"""
SPID-Xploit v2.0 - Modules Package
Italian SPID Penetration Testing Framework

This package contains all attack and analysis modules:
- ai_engine: Core AI/ML engine for intelligent payload generation
- cve_2025_24894: CVE-2025-24894 SAML signature bypass exploit
- metadata_parser: SAML metadata analysis and extraction
- payload_generator: AI-powered payload generation
- recon: OSINT and reconnaissance module
- registry_scraper: SPID entity registry extraction
- saml_forger: SAML response forgery module
"""

__version__ = "2.0.0"
__author__ = "Security Research Team"
__license__ = "For authorized security testing only"

import sys
import os

# Ensure modules path is set
modules_dir = os.path.dirname(os.path.abspath(__file__))
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)
