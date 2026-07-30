#!/usr/bin/env python3
"""
Registry Scraper Module
Extracts ALL SPID federation entities from the official registry
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

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class RegistryScraper:
    def __init__(self):
        self.registry_base = "https://registry.spid.gov.it"
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'idps'
        )
        os.makedirs(self.output_dir, exist_ok=True)

        self.endpoints = [
            f"{self.registry_base}/entities/",
            f"{self.registry_base}/entities-idp?output=xml",
            f"{self.registry_base}/entities-sp?output=xml",
            f"{self.registry_base}/entities-aa?output=xml",
        ]

        self.entities: List[Dict] = []
        self.idps: List[Dict] = []
        self.sps: List[Dict] = []
        self.aas: List[Dict] = []

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.session.verify = False

    def run(self):
        console.print(Panel.fit("[bold green]SPID Registry Scraper[/bold green]", border_style="green"))
        self._fetch_aggregated()
        self._parse_entities()
        self._fetch_details()
        self._save_all()
        self._display_summary()

    def _fetch_aggregated(self):
        console.print("\n[cyan][*] Fetching aggregated entity list...[/cyan]")
        for endpoint in self.endpoints:
            try:
                resp = self.session.get(endpoint, timeout=30)
                if resp.status_code == 200 and len(resp.content) > 500:
                    filename = endpoint.split('/')[-1].split('?')[0] or 'entities.xml'
                    filepath = os.path.join(self.output_dir, f'registry_{filename}')
                    with open(filepath, 'wb') as f:
                        f.write(resp.content)
                    console.print(f" [green]✓ Fetched: {filename} ({len(resp.content):,} bytes)[/green]")
                    self._parse_aggregated_xml(resp.text, endpoint)
            except Exception as e:
                console.print(f" [red]✗ {endpoint}: {str(e)[:50]}[/red]")

    def _parse_aggregated_xml(self, xml_str: str, source: str):
        try:
            root = etree.fromstring(xml_str.encode())
            ns = {
                'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
            }
            entities = root.findall('.//md:EntityDescriptor', ns)
            for entity in entities:
                entity_id = entity.get('entityID', '')
                xml_bytes = etree.tostring(entity, pretty_print=True)
                entry = {
                    'entity_id': entity_id,
                    'entity_id_short': entity_id[:80],
                    'xml': xml_bytes.decode(),
                    'type': self._classify_entity(entity),
                    'org_name': self._extract_org_name(entity),
                    'contacts': self._extract_contacts(entity),
                    'certificates': self._extract_certs(entity),
                    'sso_endpoints': self._extract_sso_endpoints(entity),
                    'acs_endpoints': self._extract_acs_endpoints(entity),
                    'attributes': self._extract_attributes(entity),
                    'is_idp': False,
                    'is_sp': False,
                    'is_aa': False,
                }
                etype = entry['type']
                if etype == 'IDP':
                    entry['is_idp'] = True
                    self.idps.append(entry)
                elif etype == 'SP':
                    entry['is_sp'] = True
                    self.sps.append(entry)
                elif etype == 'AA':
                    entry['is_aa'] = True
                    self.aas.append(entry)
                self.entities.append(entry)
        except Exception as e:
            console.print(f" [red]! Parse error: {str(e)[:60]}[/red]")

    def _classify_entity(self, entity) -> str:
        roles = entity.findall('.//md:RoleDescriptor', {
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata'
        })
        for role in roles:
            tag = role.tag.split('}')[-1] if '}' in role.tag else role.tag
            if 'IDPSSO' in tag:
                return 'IDP'
            elif 'SPSSO' in tag:
                return 'SP'
            elif 'AttributeAuthority' in tag:
                return 'AA'
        return 'UNKNOWN'

    def _extract_org_name(self, entity) -> str:
        ns = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}
        org = entity.find('.//md:OrganizationName', ns)
        return org.text if org is not None else 'Unknown'

    def _extract_contacts(self, entity) -> List[Dict]:
        ns = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}
        contacts = []
        for contact in entity.findall('.//md:ContactPerson', ns):
            ctype = contact.get('contactType', 'unknown')
            email = contact.find('md:EmailAddress', ns)
            phone = contact.find('md:TelephoneNumber', ns)
            company = contact.find('md:Company', ns)
            contacts.append({
                'type': ctype,
                'email': email.text if email is not None else '',
                'phone': phone.text if phone is not None else '',
                'company': company.text if company is not None else '',
            })
        return contacts

    def _extract_certs(self, entity) -> List[str]:
        ns = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
        certs = []
        for cert in entity.findall('.//ds:X509Certificate', ns):
            if cert.text:
                certs.append(cert.text[:80])
        return certs

    def _extract_sso_endpoints(self, entity) -> List[str]:
        ns = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}
        endpoints = []
        for sso in entity.findall('.//md:SingleSignOnService', ns):
            loc = sso.get('Location', '')
            if loc:
                endpoints.append(loc)
        return endpoints

    def _extract_acs_endpoints(self, entity) -> List[str]:
        ns = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}
        endpoints = []
        for acs in entity.findall('.//md:AssertionConsumerService', ns):
            loc = acs.get('Location', '')
            if loc:
                endpoints.append(loc)
        return endpoints

    def _extract_attributes(self, entity) -> List[str]:
        ns = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}
        attrs = []
        for attr in entity.findall('.//md:RequestedAttribute', ns):
            name = attr.get('Name', '')
            if name:
                attrs.append(name)
        return attrs

    def _parse_entities(self):
        console.print(f"\n[cyan][*] Parsed: {len(self.entities)} entities[/cyan]")
        console.print(f"  [green]IdPs: {len(self.idps)} | SPs: {len(self.sps)} | AAs: {len(self.aas)}[/green]")

    def _fetch_details(self):
        """Fetch individual entity details"""
        if len(self.entities) > 100:
            console.print(f"\n[cyan][*] Skipping individual detail fetch ({len(self.entities)} entities)[/cyan]")
            return
        console.print(f"\n[cyan][*] Fetching details for {len(self.entities)} entities...[/cyan]")
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching...", total=len(self.entities))
            for entity in self.entities:
                eid = entity['entity_id']
                try:
                    resp = self.session.get(
                        f"{self.registry_base}/entities/{quote(eid, safe='')}",
                        timeout=10
                    )
                    if resp.status_code == 200:
                        entity['detail_xml'] = resp.text
                except Exception:
                    pass
                progress.update(task, advance=1)
                time.sleep(0.2)

    def _save_all(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        json_file = os.path.join(self.output_dir, f'spid_entities_{timestamp}.json')
        json_data = []
        for e in self.entities:
            json_data.append({
                'entity_id': e['entity_id_short'],
                'org_name': e['org_name'],
                'type': e['type'],
                'contacts_count': len(e['contacts']),
                'has_cert': len(e['certificates']) > 0,
                'num_sso': len(e['sso_endpoints']),
                'num_acs': len(e['acs_endpoints']),
            })
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        console.print(f" [green]✓ JSON: {json_file} ({len(json_data)} entities)[/green]")

        csv_file = os.path.join(self.output_dir, f'spid_entities_{timestamp}.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Entity ID', 'Organization', 'Type', 'Is IdP', 'Is SP', 'Is AA'])
            for e in self.entities:
                writer.writerow([
                    e['entity_id_short'], e['org_name'], e['type'],
                    'Yes' if e['is_idp'] else 'No',
                    'Yes' if e['is_sp'] else 'No',
                    'Yes' if e['is_aa'] else 'No'
                ])
        console.print(f" [green]✓ CSV: {csv_file}[/green]")

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
        console.print(f" [green]✓ IdP JSON: {idp_file} ({len(idp_data)} IdPs)[/green]")

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
        console.print(f" [green]✓ SP JSON: {sp_file} ({len(sp_data)} SPs)[/green]")

    def _display_summary(self):
        console.print(Panel.fit(
            "[bold green]Extraction Complete![/bold green]\n\n"
            f"[white]Total Entities: {len(self.entities)}[/white]\n"
            f"[white]Identity Providers: {len(self.idps)}[/white]\n"
            f"[white]Service Providers: {len(self.sps)}[/white]\n"
            f"[white]Attribute Authorities: {len(self.aas)}[/white]",
            border_style="green", title="[bold]SUMMARY[/bold]"
        ))

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

        summary_file = os.path.join(self.output_dir, f'spid_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(summary_file, 'w') as f:
            f.write(f"SPID Registry Extraction Summary\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Total Entities: {len(self.entities)}\n")
            f.write(f"Identity Providers: {len(self.idps)}\n")
            f.write(f"Service Providers: {len(self.sps)}\n")
            f.write(f"Attribute Authorities: {len(self.aas)}\n")
        console.print(f"\n[green][✓] Summary saved: {summary_file}[/green]")


def run():
    scraper = RegistryScraper()
    scraper.run()


if __name__ == "__main__":
    run()
