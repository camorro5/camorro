#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camoro banners, colors and console helpers."""


class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"
    WHITE = "\033[97m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"


BANNER = r"""
{c.CYAN}{c.BOLD}
   ██████╗ █████╗ ███╗   ███╗ ██████╗ ██████╗  ██████╗
  ██╔════╝██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██╔═══██╗
  ██║     ███████║██╔████╔██║██║   ██║██████╔╝██║   ██║
  ██║     ██╔══██║██║╚██╔╝██║██║   ██║██╔══██╗██║   ██║
  ╚██████╗██║  ██║██║ ╚═╝ ██║╚██████╔╝██║  ██║╚██████╔╝
   ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝
{c.ENDC}{c.YELLOW}
        ⚡ CAMORO OSINT + AI WORDLIST + BRUTE/SWARM ⚡
{c.DIM}              Linux & Termux | v1.0.0
{c.ENDC}
{c.FAIL}  [!] Authorized security testing only — use responsibly
{c.ENDC}
"""

BANNER_BRUTE = r"""
{c.CYAN}{c.BOLD}
  ⚡ CAMORO BRUTE FORCE ENGINE
{c.ENDC}"""

BANNER_SWARM = r"""
{c.MAGENTA}{c.BOLD}
  ⚡ CAMORO SWARM ENGINE · MULTI-LINK + API ROTATION
{c.ENDC}"""


def show_banner():
    print(BANNER.format(c=Colors))


def show_brute_banner():
    print(BANNER_BRUTE.format(c=Colors))


def show_swarm_banner():
    print(BANNER_SWARM.format(c=Colors))


def info(msg):
    print(f"{Colors.OKCYAN}[*]{Colors.ENDC} {msg}")


def success(msg):
    print(f"{Colors.OKGREEN}[+]{Colors.ENDC} {msg}")


def warn(msg):
    print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")


def error(msg):
    print(f"{Colors.FAIL}[-]{Colors.ENDC} {msg}")


def ok(msg):
    print(f"{Colors.OKGREEN}[✓]{Colors.ENDC} {msg}")


def fail(msg):
    print(f"{Colors.FAIL}[✗]{Colors.ENDC} {msg}")


def step(num, total, title):
    print(
        f"\n{Colors.BOLD}{Colors.MAGENTA}"
        f"{'═' * 56}\n"
        f"  STAGE {num}/{total} · {title}\n"
        f"{'═' * 56}"
        f"{Colors.ENDC}\n"
    )
