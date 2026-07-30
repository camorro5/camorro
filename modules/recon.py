#!/usr/bin/env python3
"""
Reconnaissance Module - AI-Powered OSINT and Information Gathering
Targets the SPID ecosystem for comprehensive intelligence collection
"""

import os
import re
import sys
import json
import socket
import ssl
import hashlib
import subprocess
import textwrap
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

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class AIRecon:
    """
    AI-Powered Reconnaissance Module
    
    Performs comprehensive information gathering on the SPID ecosystem:
    - DNS enumeration
    - Subdomain discovery
    - HTTP header analysis
    - Technology fingerprinting
    - SSL/TLS analysis
    - Endpoint discovery
    - Metadata fetching
    - AI-driven analysis
    """
    
    def __init__(self, targets: Dict):
        """Initialize reconnaissance module"""
        self.targets = targets
        self.results: Dict[str, Any] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.session.verify = False
        
        # Data directory
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data'
        )
        os.makedirs(os.path.join(self.data_dir, 'captured'), exist_ok=True)
        
        # Interesting paths to check
        self.paths_to_check = [
            '/robots.txt',
            '/sitemap.xml',
            '/.well-known/',
            '/.well-known/security.txt',
            '/.well-known/openid-configuration',
            '/crossdomain.xml',
            '/clientaccesspolicy.xml',
            '/metadata.xml',
            '/metadata/',
            '/saml/metadata',
            '/saml/metadata.xml',
            '/saml/idp/metadata.xml',
            '/saml/sp/metadata.xml',
            '/wp-content/',
            '/wp-includes/',
            '/admin/',
            '/administrator/',
            '/login/',
            '/backup/',
            '/.git/HEAD',
            '/.git/config',
            '/.env',
            '/api/',
            '/swagger.json',
            '/openapi.json',
            '/health',
# Interesting paths to check
        self.paths_to_check = [
            '/robots.txt', '/sitemap.xml', '/.well-known/', '/.well-known/security.txt',
            '/.well-known/openid-configuration', '/crossdomain.xml', '/clientaccesspolicy.xml',
            '/metadata.xml', '/metadata/', '/saml/metadata', '/saml/metadata.xml',
            '/saml/idp/metadata.xml', '/saml/sp/metadata.xml',
            '/wp-content/', '/wp-includes/', '/admin/', '/administrator/',
            '/login/', '/backup/', '/.git/HEAD', '/.git/config', '/.env',
            '/api/', '/swagger.json', '/openapi.json', '/health', '/actuator/health',
            '/actuator/info', '/metrics', '/debug', '/test/', '/demo/',
            '/phpinfo.php', '/info.php', '/config.php', '/config.json',
            '/.htaccess', '/.DS_Store', '/server-status', '/server-info',
            '/wp-json/', '/xmlrpc.php', '/wp-config.php.bak',
        ]

    def run(self):
        """Execute all reconnaissance phases"""
        console.print(Panel.fit(
            "[bold cyan]AI-Powered Reconnaissance Module[/bold cyan]\n"
            "[white]Comprehensive intelligence gathering on SPID ecosystem[/white]",
            border_style="cyan"
        ))

        phases = [
            ("DNS & Subdomain Enumeration", self._dns_recon),
            ("HTTP Header Analysis", self._http_headers),
            ("Technology Fingerprinting", self._tech_fingerprint),
            ("SSL/TLS Analysis", self._ssl_analysis),
            ("Endpoint Discovery", self._endpoint_discovery),
            ("Metadata Collection", self._metadata_collection),
            ("OSINT Analysis", self._osint_analysis),
            ("AI Risk Assessment", self._ai_risk_assessment),
        ]

        with Progress() as progress:
            overall = progress.add_task("[red]Reconnaissance Progress", total=len(phases))
            for phase_name, phase_func in phases:
                progress.update(overall, advance=1, description=f"[cyan]{phase_name}")
                try:
                    phase_func()
                except Exception as e:
                    progress.console.print(f"  [red]✗ {phase_name}: {str(e)[:50]}[/red]")

        self._display_results()
        self._save_results()

    def _dns_recon(self):
        """DNS and subdomain reconnaissance"""
        console.print("\n  [cyan]DNS Reconnaissance:[/cyan]")
        for name, info in self.targets.items():
            url = info.get('url', '')
            hostname = urlparse(url).hostname
            if hostname:
                try:
                    ip = socket.gethostbyname(hostname)
                    self.results.setdefault('dns', {})[hostname] = {'ip': ip}
                    console.print(f"    [green]{hostname}: {ip}[/green]")
                except socket.gaierror:
                    console.print(f"    [red]{hostname}: DNS resolution failed[/red]")

                try:
                    host_info = socket.gethostbyaddr(ip)
                    self.results['dns'][hostname]['hostname'] = host_info[0]
                except: pass

    def _http_headers(self):
        """Analyze HTTP response headers"""
        console.print("\n  [cyan]HTTP Header Analysis:[/cyan]")
        for name, info in self.targets.items():
            url = info.get('url', '')
            if not url: continue
            try:
                resp = self.session.get(url, timeout=10, allow_redirects=True)
                headers = dict(resp.headers)
                self.results.setdefault('headers', {})[url] = headers
                console.print(f"    [green]{url}: HTTP {resp.status_code}[/green]")

                if 'Server' in headers:
                    console.print(f"      Server: {headers['Server']}")
                if 'X-Powered-By' in headers:
                    console.print(f"      Powered-By: {headers['X-Powered-By']}")
                if 'X-Frame-Options' not in headers:
                    console.print(f"      [yellow]Missing X-Frame-Options (Clickjacking risk)[/yellow]")
                if 'Content-Security-Policy' not in headers:
                    console.print(f"      [yellow]Missing Content-Security-Policy[/yellow]")
                if 'Strict-Transport-Security' not in headers:
                    console.print(f"      [yellow]Missing HSTS[/yellow]")
            except Exception as e:
                console.print(f"    [red]{url}: {str(e)[:40]}[/red]")

    def _tech_fingerprint(self):
        """Identify web technologies"""
        console.print("\n  [cyan]Technology Fingerprinting:[/cyan]")
        for name, info in self.targets.items():
            url = info.get('url', '')
            if not url: continue
            try:
                resp = self.session.get(url, timeout=10)
                html = resp.text.lower()
                techs = []

                if 'wp-content' in html or 'wp-includes' in html:
                    techs.append('WordPress')
                if 'nginx' in resp.headers.get('Server', '').lower():
                    techs.append('Nginx')
                    version = re.search(r'nginx/([\d.]+)', resp.headers.get('Server', ''))
                    if version: techs.append(f'Nginx {version.group(1)}')
                if 'csrf-token' in html: techs.append('CSRF Protection')
                if 'saml' in html: techs.append('SAML 2.0')
                if 'openid' in html: techs.append('OpenID Connect')

                self.results.setdefault('tech', {})[url] = techs
                if techs:
                    console.print(f"    [green]{url}: {', '.join(techs)}[/green]")
                else:
                    console.print(f"    [yellow]{url}: No clear fingerprint[/yellow]")
            except Exception as e:
                console.print(f"    [red]{url}: {str(e)[:40]}[/red]")

    def _ssl_analysis(self):
        """Analyze SSL/TLS configuration"""
        console.print("\n  [cyan]SSL/TLS Analysis:[/cyan]")
        for name, info in self.targets.items():
            url = info.get('url', '')
            hostname = urlparse(url).hostname
            if not hostname: continue
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with socket.create_connection((hostname, 443), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        if cert:
                            subject = dict(x[0] for x in cert.get('subject', []))
                            issuer = dict(x[0] for x in cert.get('issuer', []))
                            expiry = cert.get('notAfter', 'Unknown')
                            self.results.setdefault('ssl', {})[hostname] = {
                                'subject': subject.get('commonName', 'Unknown'),
                                'issuer': issuer.get('commonName', 'Unknown'),
                                'expiry': expiry,
                                'version': ssock.version()
                            }
                            console.print(f"    [green]{hostname}: {ssock.version()}[/green]")
                            console.print(f"      Subject: {subject.get('commonName', 'N/A')}")
                            console.print(f"      Expires: {expiry}")
            except Exception as e:
                console.print(f"    [red]{hostname}: {str(e)[:40]}[/red]")

    def _endpoint_discovery(self):
        """Discover exposed endpoints and paths"""
        console.print("\n  [cyan]Endpoint Discovery:[/cyan]")
        for name, info in self.targets.items():
            base_url = info.get('url', '')
            if not base_url: continue
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
                except: pass
            self.results.setdefault('endpoints', {})[base_url] = found

    def _metadata_collection(self):
        """Collect SAML metadata from endpoints"""
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
        """Perform OSINT analysis"""
        console.print("\n  [cyan]OSINT Analysis:[/cyan]")
        self.results['osint'] = {
            'target_count': len(self.targets),
            'discovered_at': datetime.now().isoformat(),
            'ecosystem': 'Italian Public Digital Identity System (SPID)',
            'governing_body': 'Agenzia per l\'Italia Digitale (AgID)',
            'contact': 'spid.tech@agid.gov.it',
            'phone': '+3906852641',
        }
        console.print(f"    [green]Target ecosystem: SPID (Sistema Pubblico di Identità Digitale)[/green]")
        console.Print(f"    [green]Governing body: AgID[/green]")

    def _ai_risk_assessment(self):
        """AI-powered risk assessment"""
        console.print("\n  [cyan]AI Risk Assessment:[/cyan]")
        risks = []

        # Check for missing security headers
        for url, headers in self.results.get('headers', {}).items():
            if 'Strict-Transport-Security' not in headers:
                risks.append({'target': url, 'risk': 'Missing HSTS', 'severity': 'Medium'})
            if 'Content-Security-Policy' not in headers:
                risks.append({'target': url, 'risk': 'Missing CSP', 'severity': 'Medium'})
            if 'X-Frame-Options' not in headers:
                risks.append({'target': url, 'risk': 'Missing X-Frame-Options', 'severity': 'Medium'})

        # Check for exposed metadata
        for url, size in self.results.get('metadata', {}).items():
            if size > 1000:
                risks.append({'target': url, 'risk': 'Exposed SAML/OIDC metadata', 'severity': 'High'})

        # Check endpoints
        for base, found in self.results.get('endpoints', {}).items():
            for ep in found:
                if ep['status'] == 200 and ep['size'] < 500:
                    risks.append({'target': base + ep['path'], 'risk': 'Exposed path', 'severity': 'Medium'})

        self.results['risks'] = risks
        for r in risks:
            color = 'red' if r['severity'] == 'High' else 'yellow'
            console.print(f"    [{color}]{r['severity']:6s}[/{color}] {r['target']}: {r['risk']}")

    def _display_results(self):
        """Display comprehensive results"""
        console.print(Panel.fit(
            "[bold green]Reconnaissance Complete![/bold green]",
            border_style="green"
        ))

        # Risk table
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
        """Save reconnaissance results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = os.path.join(self.data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        filepath = os.path.join(log_dir, f'recon_{timestamp}.json')
        with open(filepath, 'w') as f:
            # Remove binary/large data for JSON
            clean = {k: v for k, v in self.results.items() if k != 'metadata'}
            json.dump(clean, f, indent=2, default=str)
        console.print(f"\n[green][✓] Report saved: {filepath}[/green]")


def run():
    """Standalone entry point"""
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
