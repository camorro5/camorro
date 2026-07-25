#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Colors, banner, and output helpers."""

import os
import sys
from colorama import init, Fore, Style
init(autoreset=True)


class C:
    R = Fore.RED + Style.BRIGHT
    G = Fore.GREEN + Style.BRIGHT
    Y = Fore.YELLOW + Style.BRIGHT
    B = Fore.BLUE + Style.BRIGHT
    C = Fore.CYAN + Style.BRIGHT
    M = Fore.MAGENTA + Style.BRIGHT
    W = Fore.WHITE + Style.BRIGHT
    E = Style.RESET_ALL


BANNER = fr"""
{C.C}
   ██╗ ██████╗     ████████╗ ██████╗  ██████╗ ██╗     
   ██║██╔════╝     ╚══██╔══╝██╔═══██╗██╔═══██╗██║     
   ██║██║  ███╗       ██║   ██║   ██║██║   ██║██║     
   ██║██║   ██║       ██║   ██║   ██║██║   ██║██║     
   ██║╚██████╔╝       ██║   ╚██████╔╝╚██████╔╝███████╗
   ╚═╝ ╚═════╝        ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
{C.E}
   {C.W}Instagram Security Testing Tool — v1.0{C.E}
   {C.C}OSINT  ·  AI Wordlist  ·  Brute Force  ·  Proxy{C.E}
"""


def show_banner():
    print(BANNER)


def clear():
    os.system("clear 2>/dev/null || cls 2>/dev/null || true")


def info(msg):
    print(f"{C.C}[*]{C.E} {msg}")


def ok(msg):
    print(f"{C.G}[+]{C.E} {msg}")


def warn(msg):
    print(f"{C.Y}[!]{C.E} {msg}")


def err(msg):
    print(f"{C.R}[-]{C.E} {msg}")


def step(n, total, msg):
    print(f"{C.B}[{n}/{total}]{C.E} {C.W}{msg}{C.E}")


def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    try:
        return input(f"{C.Y}[?]{C.E} {prompt}{suffix}: ").strip() or default
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def yesno(q, default_yes=True):
    h = "Y/n" if default_yes else "y/N"
    a = ask(f"{q} ({h})")
    if not a:
        return default_yes
    return a[0].lower() == "y"


def menu(options, title="MENU"):
    print(f"\n{C.C}┌──────────────────────────────────────────┐{C.E}")
    print(f"{C.C}│{C.E}  {C.W}{title.center(40)}{C.E}{C.C}│")
    print(f"{C.C}│{' ' * 40}│")
    for i, opt in enumerate(options, 1):
        label = opt if isinstance(opt, str) else opt[0]
        print(f"{C.C}│{C.E}  {C.W}{i:2}{C.E}. {label[:36]:36} {C.C}│")
    print(f"{C.C}└──────────────────────────────────────────┘{C.E}\n")
    while True:
        a = ask(f"Choice (1-{len(options)})")
        try:
            n = int(a)
            if 1 <= n <= len(options):
                return n
        except ValueError:
            pass
        warn(f"Enter 1-{len(options)}")
