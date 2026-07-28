# CVE-2026-48908 | iec-global.com

## Target
- Domain: https://iec-global.com
- Org: Israel Electric Corporation (IEC)
- CMS: Joomla 4.4.0
- Component: SP Page Builder 4.0.11
- CVE: CVE-2026-48908
- CVSS: 10.0 Critical
- Type: Unauthenticated File Upload to RCE

Authorized security testing only.

## Run

### Termux
```bash
pkg update -y
pkg install python curl zip -y
pip install -r requirements.txt
python exploit.py
