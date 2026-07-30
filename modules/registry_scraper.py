#!/usr/bin/env python3
"""
Registry Scraper Module
Extracts ALL SPID federation entities from the official registry

Endpoints:
  - https://registry.spid.gov.it/entities/          (aggregated XML)
  - https://registry.spid.gov.it/entities-idp?output=xml  (IdPs only)
  - https://registry.spid.gov.it/entities-sp?output=xml   (SPs only)
  - https://registry.spid.gov.it/entities/<entityID>      (single entity)
"""

import os
import json
import csv
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests
from lxml import etree
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TaskProgressColumn, TimeRemainingColumn
)
from rich.panel import Panel
from rich import print as rprint

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class RegistryScraper:
    """
    SPID Registry Scraper - Extracts all entities from the SPID federation
    
    This module connects to the official SPID registry at registry.spid.gov.it
    and extracts all Identity Providers (IdPs), Service Providers (SPs),
    and Attribute Authorities (AAs) registered in the federation.
    """
    
    def __init__(self):
        """Initialize the registry scraper"""
        self.registry_base = "https://registry.spid.gov.it"
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'idps'
        )
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Endpoints to try
        self.endpoints = [
            f"{self.registry_base}/entities/",
            f"{self.registry_base}/entities-idp?output=xml",
            f"{self.registry_base}/entities-sp?output=xml",
            f"{self.registry_base}/entities-aa?output=xml",
        ]
        
        # Collected data
        self.entities: List[Dict] = []
        self.idps: List[Dict] = []
        self.sps: List[Dict] = []
        self.aas: List[Dict] = []
        
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/xml, text/xml, application/json, */*',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        
        # Namespace map
        self.ns = {
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'spid': 'https://spid.gov.it/saml-extensions'
        }
    
    def run(self):
        """Main execution - orchestrates the entire scraping process"""
        console.print(Panel.fit(
            "[bold cyan]SPID Registry Scraper v2.0[/bold cyan]\n"
            "[white]Extracts all entities from the SPID federation registry[/white]",
            border_style="cyan"
        ))
        
        # Phase 1: Fetch aggregated registry
        console.print("\n[bold cyan]Phase 1: Fetching aggregated registry XML...[/bold cyan]")
        registry_xml = self._fetch_registry()
        if not registry_xml:
            console.print("[red][!] Failed to fetch registry from all endpoints[/red]")
            return
        
        # Phase 2: Parse entities
        console.print("\n[bold cyan]Phase 2: Parsing SPID entities...[/bold cyan]")
        self._parse_registry(registry_xml)
        
        # Phase 3: Classify entities
        self._classify_entities()
        
        # Phase 4: Fetch detailed metadata (if needed)
        if len(self.entities) > 0:
            console.print("\n[bold cyan]Phase 3: Fetching detailed metadata...[/bold cyan]")
            self._fetch_detailed_metadata()
        
        # Phase 5: Save results
        console.print("\n[bold cyan]Phase 4: Saving results...[/bold cyan]")
        self._save_results()
        
        # Phase 6: Display summary
        self._display_summary()
    
    def _fetch_registry(self) -> Optional[str]:
        """Fetch the registry XML from multiple endpoints"""
        for endpoint in self.endpoints:
            try:
                console.print(f"  [cyan]Trying: {endpoint}[/cyan]")
                
                resp = self.session.get(
                    endpoint,
                    timeout=60,
                    verify=False
                )
                
                if resp.status_code == 200:
                    content = resp.text
                    
                    # Check if it's valid XML with entity descriptors
                    if 'EntityDescriptor' in content or 'EntitiesDescriptor' in content:
                        console.print(f"  [green]✓ Valid registry XML ({len(content):,} bytes)[/green]")
                        return content
                    elif len(content) > 100 and '<?xml' in content:
                        console.print(f"  [green]✓ Potential XML ({len(content):,} bytes)[/green]")
                        return content
                    else:
                        console.print(f"  [yellow]✗ Not SAML metadata[/yellow]")
                else:
                    console.print(f"  [red]✗ HTTP {resp.status_code}[/red]")
                    
            except requests.exceptions.Timeout:
                console.print(f"  [red]✗ Timeout (60s)[/red]")
            except requests.exceptions.SSLError:
                console.print(f"  [red]✗ SSL Error[/red]")
                # Try without SSL
                try:
                    http_endpoint = endpoint.replace('https://', 'http://')
                    resp = requests.get(http_endpoint, timeout=30)
                    if resp.status_code == 200 and 'EntityDescriptor' in resp.text:
                        console.print(f"  [green]✓ HTTP version worked![/green]")
                        return resp.text
                except:
                    pass
            except Exception as e:
                console.print(f"  [red]✗ Error: {str(e)}[/red]")
        
        return None
    
    def _parse_registry(self, xml_data: str):
        """Parse the registry XML and extract all entities"""
        try:
            root = etree.fromstring(xml_data.encode() if isinstance(xml_data, str) else xml_data)
        except etree.XMLSyntaxError as e:
            console.print(f"[red]  XML parse error: {str(e)}[/red]")
            # Try to fix by wrapping in EntitiesDescriptor
            try:
                wrapped = f'<?xml version="1.0" encoding="UTF-8"?>\n<md:EntitiesDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata">\n{xml_data}\n</md:EntitiesDescriptor>'
                root = etree.fromstring(wrapped.encode())
                console.print("[yellow]  → Wrapped in EntitiesDescriptor for parsing[/yellow]")
            except:
                console.print("[red]  Cannot parse XML[/red]")
                return
        
        # Find all EntityDescriptor elements
        entities = root.findall('.//md:EntityDescriptor', self.ns)
        
        if not entities:
            # Try without namespace
            entities = root.findall('.//{urn:oasis:names:tc:SAML:2.0:metadata}EntityDescriptor')
        
        if not entities:
            # Try finding any EntityDescriptor
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'EntityDescriptor':
                    entities.append(elem)
        
        console.print(f"  [cyan]Found {len(entities)} EntityDescriptor elements[/cyan]")
        
        for entity in entities:
            try:
                entity_info = self._parse_single_entity(entity)
                if entity_info:
                    self.entities.append(entity_info)
            except Exception as e:
                console.print(f"  [red]Parse error for entity: {str(e)[:50]}[/red]")
        
        console.print(f"  [green]✓ Successfully parsed {len(self.entities)} entities[/green]")
    
    def _parse_single_entity(self, entity_elem) -> Optional[Dict]:
        """Parse a single EntityDescriptor element"""
        try:
            # Get entityID
            entity_id = entity_elem.get('entityID', 'unknown')
            entity_id_short = entity_elem.get('entityID', '')
            
            # Determine type
            has_idp = entity_elem.find('.//md:IDPSSODescriptor', self.ns) is not None
            has_sp = entity_elem.find('.//md:SPSSODescriptor', self.ns) is not None
            has_aa = entity_elem.find('.//md:AttributeAuthorityDescriptor', self.ns) is not None
            
            # Try without namespace
            if not has_idp:
                for el in entity_elem.iter():
                    tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
                    if tag == 'IDPSSODescriptor':
                        has_idp = True
                    elif tag == 'SPSSODescriptor':
                        has_sp = True
                    elif tag == 'AttributeAuthorityDescriptor':
                        has_aa = True
            
            entity_type = []
            if has_idp: entity_type.append('IdP')
            if has_sp: entity_type.append('SP')
            if has_aa: entity_type.append('AA')
            if not entity_type: entity_type.append('UNKNOWN')
            
            # Get organization info
            org_name = self._get_text(entity_elem, './/md:OrganizationName', self.ns)
            org_display = self._get_text(entity_elem, './/md:OrganizationDisplayName', self.ns)
            org_url = self._get_text(entity_elem, './/md:OrganizationURL', self.ns)
            
            # Get contact info
            contacts = []
            for contact in entity_elem.findall('.//md:ContactPerson', self.ns):
                ctype = contact.get('contactType', 'other')
                email = self._get_text(contact, './/md:EmailAddress', self.ns)
                phone = self._get_text(contact, './/md:TelephoneNumber', self.ns)
                company = self._get_text(contact, './/md:Company', self.ns)
                contacts.append({
                    'type': ctype,
                    'email': email,
                    'phone': phone,
                    'company': company
                })
            
            # Get IPACode (SPID-specific)
            ipa_code = self._get_text(entity_elem, './/spid:IPACode', self.ns)
            
            # Get supported attributes (for SPs)
            attributes = []
            for attr in entity_elem.findall('.//md:RequestedAttribute', self.ns):
                attr_name = attr.get('Name', '')
                if attr_name:
                    attributes.append(attr_name)
            
            # Get SingleSignOn endpoints (for IdPs)
            sso_endpoints = []
            for sso in entity_elem.findall('.//md:SingleSignOnService', self.ns):
                binding = sso.get('Binding', '')
                location = sso.get('Location', '')
                if location:
                    sso_endpoints.append({'binding': binding, 'location': location})
            
            # Get AssertionConsumerService endpoints (for SPs)
            acs_endpoints = []
            for acs in entity_elem.findall('.//md:AssertionConsumerService', self.ns):
                binding = acs.get('Binding', '')
                location = acs.get('Location', '')
                index = acs.get('index', '')
                if location:
                    acs_endpoints.append({
                        'binding': binding, 
                        'location': location,
                        'index': index
                    })
            
            # Get certificates
            certs = []
            for key_desc in entity_elem.findall('.//md:KeyDescriptor', self.ns):
                cert_elem = key_desc.find('.//ds:X509Certificate', self.ns)
                if cert_elem is not None and cert_elem.text:
                    certs.append({
                        'use': key_desc.get('use', 'unspecified'),
                        'certificate': cert_elem.text[:100] + '...' if len(cert_elem.text) > 100 else cert_elem.text
                    })
            
            # Raw XML
            raw_xml = etree.tostring(entity_elem, pretty_print=True).decode()
            
            return {
                'entity_id': entity_id,
                'entity_id_short': entity_id_short[:100] if entity_id_short else 'unknown',
                'type': '+'.join(entity_type),
                'is_idp': has_idp,
                'is_sp': has_sp,
                'is_aa': has_aa,
                'org_name': org_name or org_display or 'Unknown',
                'org_display': org_display,
                'org_url': org_url,
                'ipa_code': ipa_code,
                'contacts': contacts,
                'attributes': list(set(attributes)),
                'sso_endpoints': sso_endpoints,
                'acs_endpoints': acs_endpoints,
                'certificates': certs,
                'xml_size': len(raw_xml),
                'xml': raw_xml
            }
            
        except Exception as e:
            return None
    
    def _get_text(self, element, xpath: str, ns: Dict) -> str:
        """Safely get text from an XML element"""
        try:
            el = element.find(xpath, ns)
            if el is not None and el.text:
                return el.text.strip()
        except:
            pass
        
        # Try without namespace
        try:
            # Extract local tag name
            local_tag = xpath.split('}')[-1] if '}' in xpath else xpath.split('/')[-1]
            for elem in element.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == local_tag and elem.text:
                    return elem.text.strip()
        except:
            pass
        
        return ''
    
    def _classify_entities(self):
        """Classify entities by type"""
        self.idps = [e for e in self.entities if e['is_idp']]
        self.sps = [e for e in self.entities if e['is_sp']]
        self.aas = [e for e in self.entities if e['is_aa']]
        
        console.print(f"\n  [cyan]Classified:[/cyan]")
        console.print(f"  [green]  IdPs: {len(self.idps)}[/green]")
        console.print(f"  [green]  SPs: {len(self.sps)}[/green]")
        console.print(f"  [green]  AAs: {len(self.aas)}[/green]")
        console.print(f"  [green]  Other: {len(self.entities) - len(self.idps) - len(self.sps) - len(self.aas)}[/green]")
    
    def _fetch_detailed_metadata(self):
        """Fetch detailed metadata for each entity"""
        # Only fetch for entities we don't have full metadata for
        to_fetch = [e for e in self.entities if e.get('xml_size', 0) < 2000]
        
        if not to_fetch:
            console.print("  [green]✓ All entities have full metadata[/green]")
            return
        
        console.print(f"  [cyan]Fetching detailed metadata for {len(to_fetch)} entities...[/cyan]")
        
        with Progress() as progress:
            task = progress.add_task(
                "[cyan]Fetching...", 
                total=len(to_fetch)
            )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for entity in to_fetch:
                    entity_id_encoded = quote(entity['entity_id'], safe='')
                    url = f"{self.registry_base}/entities/{entity_id_encoded}"
                    future = executor.submit(self._fetch_single_metadata, url, entity)
                    futures[future] = entity
                
                for future in as_completed(futures):
                    entity = futures[future]
                    try:
                        result = future.result()
                        if result:
                            idx = self.entities.index(entity)
                            self.entities[idx]['xml'] = result
                            self.entities[idx]['xml_size'] = len(result)
                    except:
                        pass
                    progress.update(task, advance=1)
        
        console.print("  [green]✓ Detailed metadata fetched[/green]")
    
    def _fetch_single_metadata(self, url: str, entity: Dict) -> Optional[str]:
        """Fetch metadata for a single entity"""
        try:
            time.sleep(random.uniform(0.1, 0.3))  # Rate limiting
            resp = self.session.get(url, timeout=15, verify=False)
            if resp.status_code == 200:
                return resp.text
        except:
            pass
        return None
    
    def _save_results(self):
        """Save results in multiple formats"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. JSON (summary, no full XML to save space)
        json_file = os.path.join(self.output_dir, f'spid_entities_{timestamp}.json')
        json_data = []
        for e in self.entities:
            json_data.append({
                'entity_id': e['entity_id_short'],
                'type': e['type'],
                'org_name': e['org_name'],
                'org_url': e['org_url'],
                'ipa_code': e['ipa_code'],
                'contacts': e['contacts'],
                'attributes': e['attributes'],
                'sso_endpoints': e['sso_endpoints'],
                'acs_endpoints': e['acs_endpoints'],
                'xml_size': e['xml_size']
            })
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        console.print(f"  [green]✓ JSON: {json_file} ({len(json_data)} entities)[/green]")
        
        # 2. CSV
        csv_file = os.path.join(self.output_dir, f'spid_entities_{timestamp}.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Entity ID', 'Type', 'Organization', 'URL', 'IPA Code',
                'Contact Type', 'Contact Email', 'Contact Phone',
                'Has IdP', 'Has SP', 'Has AA'
            ])
            for e in self.entities:
                for contact in (e['contacts'] or [{'type': '', 'email': '', 'phone': ''}]):
                    writer.writerow([
                        e['entity_id_short'],
                        e['type'],
                        e['org_name'],
                        e['org_url'],
                        e['ipa_code'],
                        contact['type'],
                        contact['email'],
                        contact['phone'],
                        'Yes' if e['is_idp'] else 'No',
                        'Yes' if e['is_sp'] else 'No',
                        'Yes' if e['is_aa'] else 'No'
                    ])
        console.print(f"  [green]✓ CSV: {csv_file}[/green]")
        
        # 3. RAW XML archive
        xml_file = os.path.join(self.output_dir, f'spid_entities_raw_{timestamp}.xml')
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<md:EntitiesDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata">\n')
            for e in self.entities:
                f.write(e['xml'])
                f.write('\n')
            f.write('</md:EntitiesDescriptor>\n')
        console.print(f"  [green]✓ XML: {xml_file}[/green]")
        
        # 4. IdP-only JSON (for targeting)
        idp_file = os.path.join(self.output_dir, f'spid_idps_{timestamp}.json')
        idp_data = []
        for e in self.idps:
            idp_data.append({
                'entity_id': e['entity_id_short'],
                'org_name': e['org_name'],
                'contacts': e['contacts'],
                'sso_endpoints': e['sso_endpoints']
            })
        with open(idp_file, 'w', encoding='utf-8') as f:
            json.dump(idp_data, f, indent=2, ensure_ascii=False)
        console.print(f"  [green]✓ IdP JSON: {idp_file} ({len(idp_data)} IdPs)[/green]")
        
        # 5. SP-only JSON (attack targets)
        sp_file = os.path.join(self.output_dir, f'spid_sps_{timestamp}.json')
        sp_data = []
        for e in self.sps:
            sp_data.append({
                'entity_id': e['entity_id_short'],
                'org_name': e['org_name'],
                'acs_endpoints': e['acs_endpoints'],
                'attributes': e['attributes']
            })
        with open(sp_file, 'w', encoding='utf-8') as f:
            json.dump(sp_data, f, indent=2, ensure_ascii=False)
        console.print(f"  [green]✓ SP JSON: {sp_file} ({len(sp_data)} SPs)[/green]")
        
        # 6. Contacts CSV (for OSINT)
        contacts_file = os.path.join(self.output_dir, f'spid_contacts_{timestamp}.csv')
        with open(contacts_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Entity ID', 'Organization', 'Type', 'Contact Type', 'Email', 'Phone', 'Company'])
            for e in self.entities:
                for contact in (e['contacts'] or []):
                    writer.writerow([
                        e['entity_id_short'],
                        e['org_name'],
                        e['type'],
                        contact['type'],
                        contact['email'],
                        contact['phone'],
                        contact['company']
                    ])
        console.print(f"  [green]✓ Contacts CSV: {contacts_file}[/green]")
    
    def _display_summary(self):
        """Display extraction summary"""
        console.print(Panel.fit(
            "[bold green]Extraction Complete![/bold green]\n\n"
            f"[white]Total Entities: {len(self.entities)}[/white]\n"
            f"[white]Identity Providers: {len(self.idps)}[/white]\n"
            f"[white]Service Providers: {len(self.sps)}[/white]\n"
            f"[white]Attribute Authorities: {len(self.aas)}[/white]\n"
            f"[white]Entities with contacts: {sum(1 for e in self.entities if e.get('contacts'))}[/white]\n"
            f"[white]Entities with certificates: {sum(1 for e in self.entities if e.get('certificates'))}[/white]",
            border_style="green",
            title="[bold]SUMMARY[/bold]"
        ))
        
        # Top 10 IdPs
        if self.idps:
            console.print("\n[bold cyan]Top Identity Providers:[/bold cyan]")
            idp_table = Table(show_header=True)
            idp_table.add_column("#", style="cyan", width=3)
            idp_table.add_column("Organization", style="yellow", width=30)
            idp_table.add_column("Entity ID", style="white", width=50)
            idp_table.add_column("SSO Endpoints", style="green", width=10)
            
            for i, idp in enumerate(self.idps[:15], 1):
                num_sso = len(idp.get('sso_endpoints', []))
                eid = idp['entity_id_short'][:47] + '...' if len(idp['entity_id_short']) > 50 else idp['entity_id_short']
                idp_table.add_row(str(i), idp['org_name'][:29], eid, str(num_sso))
            
            console.print(idp_table)
        
        # Top 10 SPs (prime targets)
        if self.sps:
            console.print("\n[bold yellow]Top Service Providers (Potential Targets):[/bold yellow]")
            sp_table = Table(show_header=True)
            sp_table.add_column("#", style="cyan", width=3)
            sp_table.add_column("Organization", style="yellow", width=30)
            sp_table.add_column("Entity ID", style="white", width=50)
            sp_table.add_column("ACS", style="green", width=10)
            
            for i, sp in enumerate(self.sps[:15], 1):
                num_acs = len(sp.get('acs_endpoints', []))
                eid = sp['entity_id_short'][:47] + '...' if len(sp['entity_id_short']) > 50 else sp['entity_id_short']
                sp_table.add_row(str(i), sp['org_name'][:29], eid, str(num_acs))
            
            console.print(sp_table)
        
        # Noteworthy targets with contact emails
        with_contacts = [e for e in self.entities if e.get('contacts') and any(c.get('email') for c in e['contacts'])]
        if with_contacts:
            console.print("\n[bold red]Entities with Contact Information (OSINT):[/bold red]")
            for e in with_contacts[:10]:
                emails = [c['email'] for c in e['contacts'] if c.get('email')]
                console.print(f"  [white]• {e['org_name'][:40]:40s} | {emails[0] if emails else 'N/A'}[/white]")
        
        # Save final summary
        summary_file = os.path.join(self.output_dir, f'spid_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(summary_file, 'w') as f:
            f.write(f"SPID Registry Extraction Summary\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Total Entities: {len(self.entities)}\n")
            f.write(f"Identity Providers: {len(self.idps)}\n")
            f.write(f"Service Providers: {len(self.sps)}\n")
            f.write(f"Attribute Authorities: {len(self.aas)}\n")
            f.write("=" * 40 + "\n")
            for e in self.entities:
                f.write(f"{e['type']:10s} | {e['org_name'][:50]:50s} | {e['entity_id_short'][:60]}\n")
        
        console.print(f"\n[green][✓] Summary saved: {summary_file}[/green]")


def run():
    """Standalone entry point"""
    scraper = RegistryScraper()
    scraper.run()


if __name__ == "__main__":
    run()
