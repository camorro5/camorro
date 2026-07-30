#!/usr/bin/env python3
"""
Metadata Analyzer Module
Parses and analyzes SPID SAML metadata for security weaknesses
"""

import os
import json
import base64
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from lxml import etree

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class MetadataAnalyzer:
    """Analyzes SAML metadata for security vulnerabilities"""

    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.ns = {
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'spid': 'https://spid.gov.it/saml-extensions',
        }
        self.findings = []

    def analyze_all(self):
        """Analyze all available metadata sources"""
        console.print(Panel.fit("[bold cyan]Metadata Security Analyzer[/bold cyan]", border_style="cyan"))

        sources = [
            ('Validator IdP', 'https://validator.spid.gov.it/metadata.xml'),
            ('Validator SP', 'https://validator.spid.gov.it/saml/idp/metadata.xml'),
            ('Registry (local)', os.path.join(self.data_dir, 'idps', 'spid_entities_raw_*.xml')),
        ]

        for name, source in sources:
            try:
                if source.startswith('http'):
                    resp = requests.get(source, timeout=15, verify=False)
                    if resp.status_code == 200:
                        self._analyze_metadata(name, resp.text, source)
                elif '*' in source:
                    import glob
                    for f in sorted(glob.glob(source), reverse=True)[:3]:
                        with open(f, 'r') as fh:
                            self._analyze_metadata(f'Registry: {os.path.basename(f)}', fh.read(), f)
            except Exception as e:
                console.print(f"  [red]✗ {name}: {str(e)[:50]}[/red]")

        self._show_results()

    def _analyze_metadata(self, name: str, xml_str: str, source: str):
        """Analyze a single metadata document"""
        console.print(f"\n[cyan]Analyzing: {name}[/cyan]")
        try:
            root = etree.fromstring(xml_str.encode())
        except:
            console.print(f"  [red]Invalid XML[/red]")
            return

        # 1. Check certificate expiry
        certs = root.findall('.//ds:X509Certificate', self.ns)
        for cert in certs:
            if cert.text:
                try:
                    der = base64.b64decode(cert.text)
                    from cryptography import x509
                    from cryptography.hazmat.backends import default_backend
                    cert_obj = x509.load_der_x509_certificate(der, default_backend())
                    expiry = cert_obj.not_valid_after_utc
                    if expiry < datetime.utcnow():
                        self.findings.append({'source': name, 'type': 'EXPIRED_CERT', 'detail': f'Certificate expired {expiry}'})
                        console.print(f"  [red]! EXPIRED CERTIFICATE: {expiry}[/red]")
                    else:
                        days_left = (expiry - datetime.utcnow()).days
                        if days_left < 30:
                            self.findings.append({'source': name, 'type': 'EXPIRING_CERT', 'detail': f'Certificate expires in {days_left} days'})
                            console.print(f"  [yellow]! Certificate expires in {days_left} days[/yellow]")
                        else:
                            console.print(f"  [green]✓ Certificate valid ({days_left} days)[/green]")
                except:
                    pass

        # 2. Check signature algorithm strength
        sig_methods = root.findall('.//ds:SignatureMethod', self.ns)
        for sig in sig_methods:
            algo = sig.get('Algorithm', '')
            if 'sha1' in algo.lower():
                self.findings.append({'source': name, 'type': 'WEAK_SIG_ALGO', 'detail': f'Weak signature: {algo}'})
                console.print(f"  [red]! Weak signature algorithm: {algo}[/red]")
            elif 'sha256' in algo.lower():
                console.print(f"  [green]✓ Strong signature: {algo.split("/")[-1]}[/green]")

        # 3. Check for weak key sizes
        key_infos = root.findall('.//ds:KeyInfo', self.ns)
        for ki in key_infos:
            rsa_key = ki.find('.//ds:RSAKeyValue', self.ns)
            if rsa_key is not None:
                modulus = rsa_key.find('ds:Modulus', self.ns)
                if modulus is not None and modulus.text:
                    key_size = len(base64.b64decode(modulus.text)) * 8
                    if key_size < 2048:
                        self.findings.append({'source': name, 'type': 'WEAK_KEY', 'detail': f'RSA key size: {key_size} bits'})
                        console.print(f"  [red]! Weak RSA key: {key_size} bits[/red]")
                    else:
                        console.print(f"  [green]✓ Key size: {key_size} bits[/green]")

        # 4. Check for exposed attributes
        attributes = root.findall('.//md:RequestedAttribute', self.ns)
        sensitive = ['fiscalNumber', 'mobilePhone', 'email', 'address', 'idCard']
        exposed_sensitive = [a.get('Name', '') for a in attributes if a.get('Name', '') in sensitive]
        if exposed_sensitive:
            self.findings.append({'source': name, 'type': 'SENSITIVE_ATTRS', 'detail': f'Exposed: {", ".join(exposed_sensitive)}'})
            console.print(f"  [yellow]! Sensitive attributes requested: {', '.join(exposed_sensitive)}[/yellow]")

        # 5. Check SSO endpoints (HTTP vs HTTPS)
        for sso in root.findall('.//md:SingleSignOnService', self.ns):
            loc = sso.get('Location', '')
            if loc.startswith('http://'):
                self.findings.append({'source': name, 'type': 'HTTP_ENDPOINT', 'detail': f'SSO over HTTP: {loc}'})
                console.print(f"  [red]! SSO endpoint over HTTP[/red]")

        console.print(f"  [green]✓ Analysis complete[/green]")

    def _show_results(self):
        """Display all findings"""
        console.print(Panel.fit(f"[bold]Metadata Analysis: {len(self.findings)} findings[/bold]", border_style="yellow"))
        if self.findings:
            table = Table()
            table.add_column("Source", style="cyan", width=25)
            table.add_column("Type", style="yellow", width=20)
            table.add_column("Detail", style="white", width=60)
            for f in self.findings:
                table.add_row(f['source'][:24], f['type'], f['detail'][:59])
            console.print(table)

        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.data_dir, 'logs', f'metadata_analysis_{timestamp}.json')
        os.makedirs(os.path.join(self.data_dir, 'logs'), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.findings, f, indent=2, default=str)
        console.print(f"\n[green][✓] Saved: {filepath}[/green]")


def run():
    analyzer = MetadataAnalyzer()
    analyzer.analyze_all()

if __name__ == "__main__":
    run()
