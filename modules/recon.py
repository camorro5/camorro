#!/usr/bin/env python3
"""
Reconnaissance Module - AI-Powered OSINT and Information Gathering (CORRECTED)
Targets the SPID ecosystem for comprehensive intelligence collection
"""

import os
import re
import sys
import json
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

import requests
from lxml import etree
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import print as rprint

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class AIRecon:
    def __init__(self, targets: Dict):
        self.targets = targets
        self.results: Dict[str, Any] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.session.verify = False
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data'
        )
        os.makedirs(os.path.join(self.data_dir, 'captured'), exist_ok=True)

        self.paths_to_check = [
            '/robots.txt', '/sitemap.xml', '/.well-known/',
            '/.well-known/security.txt', '/.well-known/openid-configuration',
            '/crossdomain.xml', '/clientaccesspolicy.xml', '/metadata.xml',
            '/wp-admin/', '/wp-content/', '/wp-json/',
            '/admin/', '/login/', '/saml/', '/saml/acs',
            '/.env', '/.git/config', '/wp-config.php.bak',
            '/phpinfo.php', '/info.php', '/test/',
            '/api/', '/v1/', '/v2/', '/swagger/',
            '/security.txt', '/health', '/status',
        ]

    def run(self):
        console.print(Panel.fit("[bold cyan]AI Reconnaissance Module[/bold cyan]", border_style="cyan"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("[cyan]Running reconnaissance...", total=None)
            self._dns_enumeration()
            self._http_header_analysis()
            self._technology_fingerprinting()
            self._ssl_analysis()
            self._endpoint_discovery()
            self._metadata_collection()
            self._osint_analysis()
            self._ai_risk_assessment()

        self._display_results()
        self._save_results()

    def _dns_enumeration(self):
        console.print("\n  [cyan]DNS Enumeration:[/cyan]")
        for name, target in self.targets.items():
            hostname = urlparse(target['url']).hostname
            try:
                ip = socket.gethostbyname(hostname)
                console.print(f"    [green]✓ {hostname} → {ip}[/green]")
                self.results.setdefault('dns', {})[hostname] = ip
            except Exception as e:
                console.print(f"    [red]✗ {hostname}: {str(e)[:40]}[/red]")

    def _http_header_analysis(self):
        console.print("\n  [cyan]HTTP Header Analysis:[/cyan]")
        for name, target in self.targets.items():
            url = target['url']
            try:
                resp = self.session.head(url, timeout=10, allow_redirects=True)
                headers = dict(resp.headers)
                self.results.setdefault('headers', {})[url] = headers
                # Check security headers
                checks = {
                    'Strict-Transport-Security': 'HSTS',
                    'Content-Security-Policy': 'CSP',
                    'X-Frame-Options': 'Clickjacking Protection',
                    'X-Content-Type-Options': 'MIME Sniffing Protection',
                    'X-XSS-Protection': 'XSS Protection',
                }
                for header, desc in checks.items():
                    if header in headers:
                        console.print(f"    [green]✓ {desc}[/green]")
                    else:
                        console.print(f"    [yellow]! Missing: {desc}[/yellow]")
                # Server header
                server = headers.get('Server', 'Unknown')
                console.print(f"    [cyan]  Server: {server}[/cyan]")
            except Exception as e:
                console.print(f"    [red]✗ {url}: {str(e)[:40]}[/red]")

    def _technology_fingerprinting(self):
        console.print("\n  [cyan]Technology Fingerprinting:[/cyan]")
        for name, target in self.targets.items():
            url = target['url']
            try:
                resp = self.session.get(url, timeout=10)
                html = resp.text
                techs = []

                # WordPress detection
                if '/wp-content/' in html or '/wp-json/' in html:
                    techs.append('WordPress')
                # nginx detection
                server = resp.headers.get('Server', '')
                if 'nginx' in server.lower():
                    techs.append('nginx')
                # PHP detection
                if 'wp-content' in html or '.php' in resp.url:
                    techs.append('PHP')
                # SAML
                if 'saml' in html.lower() or 'spid' in html.lower():
                    techs.append('SAML/SPID')

                console.print(f"    [green]✓ {url}: {', '.join(techs) if techs else 'Unknown'}[/green]")
                self.results.setdefault('tech', {})[url] = techs
            except Exception as e:
                console.print(f"    [red]✗ {url}: {str(e)[:40]}[/red]")

    def _ssl_analysis(self):
        console.print("\n  [cyan]SSL/TLS Analysis:[/cyan]")
        for name, target in self.targets.items():
            hostname = urlparse(target['url']).hostname
            port = 443
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                with socket.create_connection((hostname, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        issuer = dict(cert.get('issuer', []))
                        cn = issuer.get('commonName', 'Unknown')
                        console.print(f"    [green]✓ {hostname}: Certificate OK ({cn})[/green]")
                        self.results.setdefault('ssl', {})[hostname] = {
                            'issuer': cn,
                            'expiry': cert.get('notAfter', 'Unknown')
                        }
            except Exception as e:
                console.print(f"    [red]✗ {hostname}: {str(e)[:40]}[/red]")

    def _endpoint_discovery(self):
        console.print("\n  [cyan]Endpoint Discovery:[/cyan]")
        for name, target in self.targets.items():
            base_url = target['url']
            found = []
            for path in self.paths_to_check:
                url = base_url.rstrip('/') + path
                try:
                    resp = self.session.get(url, timeout=5, allow_redirects=False)
                    if resp.status_code in [200, 301, 302, 401, 403, 500]:
                        content_len = len(resp.content)
                        if content_len > 0 or resp.status_code in [401, 403]:
                            found.append({'path': path, 'status': resp.status_code, 'size': content_len})
                            if resp.status_code == 200 and content_len < 500:
                                console.print(f"    [red]! {path} ({resp.status_code}, {content_len}b)[/red]")
                            elif resp.status_code == 403:
                                console.print(f"    [yellow]{path} (403 Forbidden)[/yellow]")
                            elif resp.status_code in [301, 302]:
                                loc = resp.headers.get('Location', '')
                                if loc and 'login' in loc.lower():
                                    console.print(f"    [yellow]{path} → Redirect to login[/yellow]")
                except:
                    pass
            self.results.setdefault('endpoints', {})[base_url] = found

    def _metadata_collection(self):
        console.print("\n  [cyan]Metadata Collection:[/cyan]")
        metadata_urls = [
            'https://validator.spid.gov.it/metadata.xml',
            'https://validator.spid.gov.it/saml/idp/metadata.xml',
            'https://validator.spid.gov.it/oidc/rp/.well-known/openid-configuration',
            'https://demo.spid.gov.it/validator/metadata.xml',
            'https://registry.spid.gov.it/entities/',
        ]
        for url in metadata_urls:
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200 and len(resp.content) > 100:
                    filename = url.split('/')[-1] or 'metadata.xml'
                    filepath = os.path.join(self.data_dir, 'captured', filename)
                    with open(filepath, 'wb') as f:
                        f.write(resp.content)
                    console.print(f"    [green]✓ {filename} ({len(resp.content):,} bytes)[/green]")
                    self.results.setdefault('metadata', {})[url] = len(resp.content)
            except Exception as e:
                console.print(f"    [red]✗ {url}: {str(e)[:40]}[/red]")

    def _osint_analysis(self):
        console.print("\n  [cyan]OSINT Analysis:[/cyan]")
        self.results['osint'] = {
            'target_count': len(self.targets),
            'discovered_at': datetime.now().isoformat(),
            'ecosystem': 'Italian Public Digital Identity System (SPID)',
            'governing_body': "Agenzia per l'Italia Digitale (AgID)",
            'contact': 'spid.tech@agid.gov.it',
            'phone': '+3906852641',
        }
        console.print("    [green]✓ Target ecosystem: SPID (Sistema Pubblico di Identità Digitale)[/green]")
        console.print("    [green]✓ Governing body: AgID[/green]")  # FIXED: console.print (was console.Print)

    def _ai_risk_assessment(self):
        console.print("\n  [cyan]AI Risk Assessment:[/cyan]")
        risks = []
        for url, headers in self.results.get('headers', {}).items():
            if 'Strict-Transport-Security' not in headers:
                risks.append({'target': url, 'risk': 'Missing HSTS', 'severity': 'Medium'})
            if 'Content-Security-Policy' not in headers:
                risks.append({'target': url, 'risk': 'Missing CSP', 'severity': 'Medium'})
            if 'X-Frame-Options' not in headers:
                risks.append({'target': url, 'risk': 'Missing X-Frame-Options', 'severity': 'Medium'})
        for url, size in self.results.get('metadata', {}).items():
            if size > 1000:
                risks.append({'target': url, 'risk': 'Exposed SAML/OIDC metadata', 'severity': 'High'})
        for base, found in self.results.get('endpoints', {}).items():
            for ep in found:
                if ep['status'] == 200 and ep['size'] < 500:
                    risks.append({'target': base + ep['path'], 'risk': 'Exposed path', 'severity': 'Medium'})
        self.results['risks'] = risks
        for r in risks:
            color = 'red' if r['severity'] == 'High' else 'yellow'
            console.print(f"    [{color}]{r['severity']:6s}[/{color}] {r['target']}: {r['risk']}")

    def _display_results(self):
        console.print(Panel.fit("[bold green]Reconnaissance Complete![/bold green]", border_style="green"))
        risks = self.results.get('risks', [])
        if risks:
            table = Table(title="[bold red]Security Risks Found[/bold red]")
            table.add_column("Severity", style="red", width=8)
            table.add_column("Target", style="cyan", width=50)
            table.add_column("Description", style="white", width=40)
            for r in risks:
                table.add_row(r['severity'], r['target'][:48], r['risk'][:38])
            console.print(table)

    def _save_results(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = os.path.join(self.data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        filepath = os.path.join(log_dir, f'recon_{timestamp}.json')
        with open(filepath, 'w') as f:
            clean = {k: v for k, v in self.results.items() if k != 'metadata'}
            json.dump(clean, f, indent=2, default=str)
        console.print(f"\n[green][✓] Report saved: {filepath}[/green]")


def run():
    targets = {
        'spid_website': {'url': 'https://www.spid.gov.it', 'description': 'SPID Official'},
        'validator': {'url': 'https://validator.spid.gov.it', 'description': 'SAML Validator'},
        'registry': {'url': 'https://registry.spid.gov.it', 'description': 'Federation Registry'},
        'login': {'url': 'https://login.agid.gov.it', 'description': 'Admin Portal'},
        'agid': {'url': 'https://www.agid.gov.it', 'description': 'AgID Official'},
    }
    recon = AIRecon(targets)
    recon.run()


if __name__ == "__main__":
    run()
