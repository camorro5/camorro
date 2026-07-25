#!/usr/bin/env python3
"""
VENOMSCAN v2.0 - Advanced Web Application Penetration Testing Framework
═══════════════════════════════════════════════════════════════
 SQLi • XSS • LFI • RCE • CSRF • PrivEsc • Buffer Overflow
═══════════════════════════════════════════════════════════════
"""
import asyncio, json, sys, time, random
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import box
import aiohttp

from .__version__ import __version__, __codename__
from .utils.helpers import (print_banner, status, random_ua, display_table,
                             severity_tag, cvss_score, save_json, timestamp)
from .utils.network import parse_url, resolve_host, validate_target
from .core.recon import CMSDetector, PortScanner
from .core.injection import SQLiScanner, CommandInjectionScanner
from .core.xss import XSSScanner
from .core.file_attack import FileAttackScanner
from .core.csrf import CSRFScanner
from .core.auth import BruteForcer
from .core.rce import RCEExploiter
from .core.privesc import PrivEscChecker
from .core.disclosure import DisclosureScanner
from .core.evasion import EvasionContext, PayloadEncoder
from .core.fuzzer import WebFuzzer
from .core.buffer import BufferOverflowTester
from .core.llm import LocalLLM
from .core.report import ReportGenerator

console = Console()
app = typer.Typer(name="venomsan", help=f"VenomScan v{__version__} - Advanced Web Pentesting Framework")

ALL_FINDINGS = []  # Global findings tracker

# ═══════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════

@app.command()
def version():
    """عرض الإصدار."""
    print_banner()
    console.print(f"[bold red]VenomScan v{__version__}[/bold red] - {__codename__}")
    console.print("SQLi • XSS • LFI • RCE • CSRF • PrivEsc • Buffer Overflow")
    console.print("Joomla • WordPress • Drupal • Custom CMS")


@app.command()
def detect(target: str = typer.Argument(..., help="Target URL")):
    """الكشف عن CMS، التقنيات، الإضافات، WAF."""
    async def _run():
        print_banner()
        target = target.rstrip("/")
        console.print(f"[bold cyan]Target:[/bold cyan] {target}\n")

        detector = CMSDetector()
        result = await detector.detect(target)

        console.print(f"[bold]CMS:[/bold] [green]{result['cms']}[/green]")
        if result.get("version"):
            console.print(f"[bold]Version:[/bold] [green]{result['version']}[/green]")
        if result.get("admin_url"):
            console.print(f"[bold]Admin:[/bold] [cyan]{result['admin_url']}[/cyan]")
        if result.get("waf"):
            console.print(f"[bold]WAF:[/bold] [yellow]{result['waf']}[/yellow]")
        if result.get("server"):
            console.print(f"[bold]Server:[/bold] [dim]{result['server']}[/dim]")

        if result.get("components"):
            console.print(f"\n[bold]Components ({len(result['components'])}):[/bold]")
            for c in result["components"]:
                console.print(f"  [cyan]{c['name']}[/cyan] - {c['description']}")

        if result.get("technologies"):
            console.print(f"\n[bold]Technologies:[/bold] {', '.join(result['technologies'])}")

        if result.get("interesting_files"):
            console.print(f"\n[bold]Exposed Files ({len(result['interesting_files'])}):[/bold]")
            for f in result["interesting_files"]:
                console.print(f"  {f['path']} [dim]({f.get('value', f.get('status', ''))})[/dim]")

    asyncio.run(_run())


@app.command()
def scan(target: str = typer.Argument(..., help="Target URL")):
    """فحص شامل لكل الثغرات."""
    async def _run():
        global ALL_FINDINGS
        print_banner()
        target = target.rstrip("/")
        console.print(f"[bold cyan]Target:[/bold cyan] {target}\n")
        ALL_FINDINGS = []

        # Recon
        console.print("[bold]═══ PHASE 1: RECONNAISSANCE ═══[/bold]\n")
        detector = CMSDetector()
        cms_info = await detector.detect(target)
        console.print(f"CMS: [green]{cms_info['cms']} {cms_info.get('version','')}[/green]")
        console.print(f"Admin: [cyan]{cms_info.get('admin_url','N/A')}[/cyan]")

        # Port scan
        console.print(f"\n[bold]═══ PHASE 2: PORT SCAN ═══[/bold]\n")
        parsed = parse_url(target)
        host = parsed["hostname"]
        port_scanner = PortScanner(concurrency=100)
        port_results = await port_scanner.scan_common(host)
        open_ports = [r for r in port_results if r["state"] == "open"]
        if open_ports:
            display_table("Open Ports", [{"Port":r["port"],"Service":r.get("service","?"),"Banner":str(r.get("banner",""))[:40]} for r in sorted(open_ports, key=lambda x:x["port"])], "green")

        # SQL Injection
        console.print(f"\n[bold]═══ PHASE 3: SQL INJECTION ═══[/bold]\n")
        sqli = SQLiScanner(target)
        sqli_findings = await sqli.full_scan()
        ALL_FINDINGS.extend(sqli_findings)

        # XSS
        console.print(f"\n[bold]═══ PHASE 4: XSS ═══[/bold]\n")
        xss = XSSScanner(target)
        xss_findings = await xss.full_scan()
        ALL_FINDINGS.extend(xss_findings)

        # LFI/RFI
        console.print(f"\n[bold]═══ PHASE 5: FILE INCLUSION ═══[/bold]\n")
        file_scanner = FileAttackScanner(target)
        file_findings = await file_scanner.full_scan()
        ALL_FINDINGS.extend(file_findings)

        # CSRF
        console.print(f"\n[bold]═══ PHASE 6: CSRF ═══[/bold]\n")
        csrf = CSRFScanner(target)
        csrf_findings = await csrf.scan()
        ALL_FINDINGS.extend(csrf_findings)

        # Disclosure
        console.print(f"\n[bold]═══ PHASE 7: INFORMATION DISCLOSURE ═══[/bold]\n")
        disc = DisclosureScanner(target)
        disc_findings = await disc.scan_sensitive_files()
        ALL_FINDINGS.extend(disc_findings)

        # Summary
        console.print(f"\n[bold]═══════════════════════════════════[/bold]")
        console.print(f"[bold]SCAN COMPLETE[/bold]")
        console.print(f"[bold]═══════════════════════════════════[/bold]")

        if ALL_FINDINGS:
            display_table("Findings Summary", [
                {"Type":f.get("type","?"),"Severity":severity_tag(f.get("severity","?")),"URL":str(f.get("url",""))[:50],"Payload":str(f.get("payload",""))[:40]}
                for f in ALL_FINDINGS
            ], "red")
        else:
            status("No vulnerabilities found in automated scan", "success")

        # Save
        save_json({"target":target,"cms":cms_info,"findings":ALL_FINDINGS,"timestamp":timestamp()},
                  f"data/scan_{urlparse(target).hostname}.json")
        console.print(f"\n[dim]Report saved to data/[/dim]")

    asyncio.run(_run())


@app.command()
def brute(target: str = typer.Argument(..., help="Target URL"),
          username: str = typer.Option("admin", "--username", "-u"),
          wordlist: str = typer.Option(None, "--wordlist", "-w"),
          password: str = typer.Option(None, "--password", "-p"),
          concurrency: int = typer.Option(5, "--concurrency", "-c"),
          delay: float = typer.Option(0.5, "--delay", "-d")):
    """هجوم القوة العمياء على لوحة التحكم."""
    async def _run():
        print_banner()
        passwords = []
        if password:
            passwords = [password]
        elif wordlist:
            if Path(wordlist).exists():
                with open(wordlist) as f:
                    passwords = [l.strip() for l in f if l.strip()][:100]
            else:
                console.print(f"[red]Wordlist not found: {wordlist}[/red]")
                return
        else:
            from .core.auth import DEFAULT_PASSWORDS
            passwords = DEFAULT_PASSWORDS

        bruteforcer = BruteForcer(target, concurrency, delay)
        results = await bruteforcer.attack([username], passwords)

        if results:
            console.print(f"\n[bold green]✓ CREDENTIALS FOUND:[/bold green]")
            for r in results:
                console.print(f"  Username: [cyan]{r['username']}[/cyan]")
                console.print(f"  Password: [cyan]{r['password']}[/cyan]")
        else:
            console.print(f"\n[red]No valid credentials found[/red]")

    asyncio.run(_run())


@app.command()
def rce(target: str = typer.Argument(..., help="Joomla target"),
        username: str = typer.Option(..., "--username", "-u"),
        password: str = typer.Option(..., "--password", "-p")):
    """استغلال RCE عبر Joomla بعد الحصول على بيانات الدخول."""
    async def _run():
        print_banner()
        exploiter = RCEExploiter(target)
        logged_in = await exploiter.login(username, password)
        if not logged_in:
            console.print("[red]Login failed![/red]")
            return

        result = await exploiter.exploit_template()
        if result.get("success"):
            console.print(f"\n[bold green]✓ RCE ACHIEVED![/bold green]")
            console.print(f"\n[bold]Shell URL:[/bold] [cyan]{result['shell_url']}[/cyan]")
            if result.get("test_output"):
                console.print(f"[bold]Test:[/bold] {result['test_output']}")
        else:
            console.print(f"[red]Failed: {result.get('error')}[/red]")

    asyncio.run(_run())


@app.command()
def full(target: str = typer.Argument(..., help="Target URL"),
         brute_enabled: bool = typer.Option(False, "--brute", "-b", help="Enable brute force"),
         username: str = typer.Option("admin", "--username", "-u"),
         wordlist: str = typer.Option(None, "--wordlist", "-w")):
    """هجوم كامل: كشف + فحص + قوة عمياء + استغلال RCE."""
    async def _run():
        global ALL_FINDINGS
        print_banner()
        target = target.rstrip("/")
        ALL_FINDINGS = []
        console.print(f"[bold red]FULL ATTACK MODE[/bold red]")
        console.print(f"[bold cyan]Target:[/bold cyan] {target}\n")

        # Phase 1: Recon
        console.print("[bold]═══ 1: RECON ═══[/bold]")
        detector = CMSDetector()
        cms_info = await detector.detect(target)
        console.print(f"CMS: [green]{cms_info['cms']} {cms_info.get('version','')}[/green]")

        # Phase 2: Full vulnerability scan
        console.print(f"\n[bold]═══ 2: VULNERABILITY SCAN ═══[/bold]")

        sqli_findings = await SQLiScanner(target).full_scan()
        ALL_FINDINGS.extend(sqli_findings)

        xss_findings = await XSSScanner(target).full_scan()
        ALL_FINDINGS.extend(xss_findings)

        file_findings = await FileAttackScanner(target).full_scan()
        ALL_FINDINGS.extend(file_findings)

        csrf_findings = await CSRFScanner(target).scan()
        ALL_FINDINGS.extend(csrf_findings)

        disc_findings = await DisclosureScanner(target).scan_sensitive_files()
        ALL_FINDINGS.extend(disc_findings)

        # Phase 3: Brute force
        if brute_enabled and cms_info.get("admin_url"):
            console.print(f"\n[bold]═══ 3: BRUTE FORCE ═══[/bold]")
            from .core.auth import DEFAULT_PASSWORDS
            passwords = DEFAULT_PASSWORDS
            if wordlist and Path(wordlist).exists():
                with open(wordlist) as f:
                    passwords = [l.strip() for l in f if l.strip()][:50]

            bf = BruteForcer(target, concurrency=3, delay=1.0)
            creds = await bf.attack([username], passwords)

            # Phase 4: RCE
            if creds:
                console.print(f"\n[bold]═══ 4: RCE ═══[/bold]")
                for cred in creds[:1]:
                    exploiter = RCEExploiter(target)
                    if await exploiter.login(cred["username"], cred["password"]):
                        rce_result = await exploiter.exploit_template()
                        if rce_result.get("success"):
                            console.print(f"\n[bold green]✓ SERVER COMPROMISED![/bold green]")
                            console.print(f"Shell: [cyan]{rce_result['shell_url']}[/cyan]")

        # Generate report
        console.print(f"\n[bold]═══ REPORT ═══[/bold]")
        report = ReportGenerator(target, ALL_FINDINGS, cms_info)
        report.to_html()
        report.to_json()
        report.to_text()

        console.print(f"\n[bold green]✓ ATTACK COMPLETE[/bold green]")

    asyncio.run(_run())


@app.command()
def privesc(os_type: str = typer.Option("linux", "--os"), kernel: str = typer.Option(None, "--kernel", "-k")):
    """عرض نواقل رفع الصلاحيات."""
    print_banner()
    PrivEscChecker.display_vectors(os_type, kernel)


@app.command()
def fuzz(target: str = typer.Argument(..., help="Target URL"), type_: str = typer.Option("dirs", "--type", "-t", help="dirs or params")):
    """Fuzzing المجلدات والبارامترات."""
    async def _run():
        print_banner()
        fuzzer = WebFuzzer(target)
        if type_ == "dirs":
            results = await fuzzer.fuzz_dirs()
            if results:
                display_table("Found Directories", results, "green")
        elif type_ == "params":
            results = await fuzzer.fuzz_params()
            if results:
                display_table("Found Parameters", [{"Parameter":r["parameter"],"Type":r.get("type","?")} for r in results], "green")
    asyncio.run(_run())


@app.command()
def buffer(target: str = typer.Argument(..., help="Target IP/hostname")):
    """فحص Buffer Overflow."""
    async def _run():
        print_banner()
        tester = BufferOverflowTester(target)
        results = await tester.scan()
        if results:
            display_table("Potential BO Targets", results, "red")
    asyncio.run(_run())


@app.command()
def analyze(error: str = typer.Option(..., "--error", "-e", help="WAF error message"),
            attack: str = typer.Option("SQLi", "--attack", "-a")):
    """تحليل خطأ WAF بالذكاء الاصطناعي."""
    async def _run():
        print_banner()
        llm = LocalLLM()
        await llm.initialize()
        result = llm.analyze_waf_error(error, {}, attack)
        console.print(f"[bold]WAF:[/bold] {result['waf_type']}")
        console.print(f"[bold]Bypass Suggestions:[/bold]")
        for s in result.get("bypass_suggestions", []):
            console.print(f"  • [yellow]{s}[/yellow]")
        if result.get("llm_analysis"):
            console.print(f"\n[bold]AI Analysis:[/bold] {result['llm_analysis']}")
    asyncio.run(_run())


@app.command()
def encode(payload: str = typer.Argument(..., help="Payload to encode"), layers: int = typer.Option(3, "--layers", "-l")):
    """تشفير حمولة لتجاوز WAF."""
    print_banner()
    encoder = PayloadEncoder()
    encoded, applied = encoder.encode(payload, layers)
    console.print(f"[bold]Original:[/bold] {payload}")
    console.print(f"[bold]Encoded:[/bold] [green]{encoded}[/green]")
    console.print(f"[bold]Layers:[/bold] {' → '.join(applied)}")


@app.command()
def report(target: str = typer.Argument(..., help="Target URL"), findings_file: str = typer.Option(None, "--file", "-f", help="JSON findings file")):
    """توليد تقرير احترافي."""
    async def _run():
        print_banner()
        findings = []
        cms_info = {"cms":"unknown","version":"unknown"}

        if findings_file and Path(findings_file).exists():
            with open(findings_file) as f:
                data = json.load(f)
                findings = data.get("findings", [])
                cms_info = data.get("cms", cms_info)
        else:
            # Quick scan
            detector = CMSDetector()
            cms_info = await detector.detect(target)

        report = ReportGenerator(target, findings, cms_info)
        report.to_html()
        report.to_json()
        report.to_text()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
