#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

try:
    from colorama import init, Fore, Style
    init(autoreset=True)

    class C:
        R = Fore.RED
        G = Fore.GREEN
        Y = Fore.YELLOW
        C = Fore.CYAN
        M = Fore.MAGENTA
        W = Fore.WHITE
        E = Style.RESET_ALL
except Exception:
    class C:
        R = G = Y = C = M = W = E = ""


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def show_banner():
    print(f"""{C.C}
╔══════════════════════════════════════════════════╗
║              IGTOOL  v3  —  FULL                 ║
║   Intel → Dictionary → Brute (live progress)     ║
╚══════════════════════════════════════════════════╝{C.E}
""")


def info(msg):
    print(f"{C.C}[*]{C.E} {msg}")


def ok(msg):
    print(f"{C.G}[+]{C.E} {msg}")


def warn(msg):
    print(f"{C.Y}[!]{C.E} {msg}")


def err(msg):
    print(f"{C.R}[-]{C.E} {msg}")


def step(n, total, title):
    print(f"\n{C.M}[{n}/{total}]{C.E} {C.W}{title}{C.E}")
    print(f"{C.C}{'─' * 46}{C.E}")


def ask(prompt, default=""):
    if default != "":
        s = input(f"{C.Y}[?]{C.E} {prompt} [{default}]: ").strip()
        return s if s else default
    return input(f"{C.Y}[?]{C.E} {prompt}: ").strip()


def yesno(prompt, default_yes=True):
    d = "Y/n" if default_yes else "y/N"
    a = input(f"{C.Y}[?]{C.E} {prompt} [{d}]: ").strip().lower()
    if not a:
        return default_yes
    return a in ("y", "yes", "1", "o", "oui")


def menu(items, title=""):
    print()
    if title:
        print(f"{C.C}  {title}{C.E}")
    print(f"{C.C}┌{'─' * 50}┐{C.E}")
    for i, it in enumerate(items, 1):
        print(f"{C.C}│{C.E} {C.W}{i}.{C.E} {it}")
    print(f"{C.C}└{'─' * 50}┘{C.E}")
    while True:
        c = input(f"{C.Y}[?]{C.E} Choice (1-{len(items)}): ").strip()
        if c.isdigit() and 1 <= int(c) <= len(items):
            return int(c)
        err("Invalid choice")
