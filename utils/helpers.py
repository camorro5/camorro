"""
Helper utilities for GhostMedia Framework.
"""

import os
import sys
import socket
import subprocess
from datetime import datetime


# Terminal colors
R = "\033[91m"
G = "\033[92m"
Y = "\033[93m"
B = "\033[94m"
C = "\033[96m"
W = "\033[0m"
BOLD = "\033[1m"


def banner():
    """Display GhostMedia banner."""
    print(f"""
{C}{BOLD}╔══════════════════════════════════════════════════════════╗
║  {G}GhostMedia {W}{BOLD}v2.0{C}{BOLD} — Media Exploitation Framework    ║
║  {W}Target: Huawei P30 Lite | ARM64 | Android 9/10     {C}{BOLD}║
║  {W}AI Analyzer + Proxy Harvester (spys.one)           {C}{BOLD}║
║  {W}Auto-Trigger: Thumbnail | Preview | Auto-Download  {C}{BOLD}║
╚══════════════════════════════════════════════════════════╝{W}
""")


def print_status(msg: str):
    print(f"{B}[*]{W} {msg}")


def print_success(msg: str):
    print(f"{G}[+]{W} {msg}")


def print_error(msg: str):
    print(f"{R}[!]{W} {msg}")


def print_warning(msg: str):
    print(f"{Y}[!]{W} {msg}")


def print_info(msg: str):
    print(f"{C}[i]{W} {msg}")


def validate_ip(ip: str) -> bool:
    """Validate IPv4 address."""
    try:
        parts = ip.split(".")
        return len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts)
    except (ValueError, AttributeError):
        return False


def validate_port(port: int) -> bool:
    """Validate port number."""
    return 1 <= port <= 65535


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    required = {
        "python3": "python3 --version",
        "msfvenom (optional)": "msfvenom --version",
    }

    all_ok = True
    for name, check in required.items():
        try:
            result = subprocess.run(check.split(), capture_output=True, timeout=5)
            status = f"{G}✓{W}" if result.returncode == 0 else f"{Y}✗{W}"
            print(f"  {status} {name}")
            if result.returncode != 0 and "(optional)" not in name:
                all_ok = False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"  {Y}✗{W} {name} (not found)")
            if "(optional)" not in name:
                all_ok = False

    return all_ok


def get_device_info(device: str) -> dict:
    """Get detailed device profile."""
    profiles = {
        "huawei_p30_lite": {
            "name": "Huawei P30 Lite",
            "codename": "MAR-LX1M / MAR-LX3A",
            "chipset": "HiSilicon Kirin 710 (12nm)",
            "cpu": "4x Cortex-A73 @ 2.2GHz + 4x Cortex-A53 @ 1.7GHz",
            "gpu": "Mali-G51 MP4",
            "arch": "ARM64 (aarch64)",
            "android_versions": ["9.0 (Pie) EMUI 9.1", "10.0 EMUI 10.0"],
            "kernel": "Linux 4.9.x",
            "libwebp": "1.2.4 - 1.3.1",
            "stagefright": "Android 9/10 branch",
            "skia": "Android 9/10 branch",
        }
    }
    return profiles.get(device, {})
