"""Information Disclosure Scanner - Finds exposed configs, backups, sensitive files."""
import asyncio, re
from typing import Optional
import aiohttp
from ..utils.helpers import status, random_ua

SENSITIVE_FILES = [
    # Config files
    "/configuration.php", "/configuration.php.bak", "/configuration.php~",
    "/configuration.php.old", "/configuration.php.save",
    "/.env", "/.env.backup", "/.env.bak", "/.env.old",
    "/wp-config.php", "/wp-config.php.bak", "/wp-config.php~",
    "/config.php", "/config.php.bak", "/config.yml", "/config.yaml",
    # Database
    "/phpmyadmin/", "/phpMyAdmin/", "/adminer.php",
    "/.git/HEAD", "/.git/config", "/.svn/entries",
    # Logs
    "/error.log", "/error_log", "/access.log",
    "/debug.log", "/app.log",
    # Backups
    "/backup.zip", "/backup.tar.gz", "/backup.sql",
    "/site.zip", "/www.zip", "/dump.sql",
    # Info files
    "/phpinfo.php", "/info.php", "/test.php",
    "/server-status", "/server-info",
    # Version files
    "/version.txt", "/VERSION", "/CHANGELOG.txt",
    "/README.md", "/README.txt",
]

SENSITIVE_PATTERNS = {
    "DB_PASSWORD": r"(?:DB_PASSWORD|database_password|db_pass)\s*[=:]\s*['\"]([^'\"]+)['\"]",
    "DB_HOST": r"(?:DB_HOST|database_host|db_host)\s*[=:]\s*['\"]([^'\"]+)['\"]",
    "API_KEY": r"(?:API_KEY|api_key|apikey)\s*[=:]\s*['\"]([^'\"]+)['\"]",
    "SECRET": r"(?:SECRET|secret_key|secret)\s*[=:]\s*['\"]([^'\"]+)['\"]",
    "PASSWORD": r"(?:password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{3,})['\"]",
    "EMAIL": r'[\w.-]+@[\w.-]+\.\w+',
    "AWS_KEY": r'AKIA[0-9A-Z]{16}',
    "PRIVATE_KEY": r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
    "JWT_TOKEN": r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}',
}

class DisclosureScanner:
    """Scans for sensitive information disclosure."""

    def __init__(self, target: str):
        self.target = target.rstrip("/")
        self.findings = []

    async def scan_sensitive_files(self) -> list:
        """Check for exposed sensitive files."""
        status(f"Scanning {len(SENSITIVE_FILES)} sensitive files...", "info")
        findings = []
        headers = {"User-Agent": random_ua()}

        async with aiohttp.ClientSession() as s:
            for fpath in SENSITIVE_FILES:
                url = f"{self.target}{fpath}"
                try:
                    resp = await s.get(url, headers=headers, timeout=5, ssl=False)
                    if resp.status == 200:
                        content = await resp.text()
                        finding = {"type":"Sensitive File Exposed","path":fpath,"url":url,"status":resp.status,"severity":"HIGH"}

                        # Check for sensitive patterns
                        for pat_name, pat_regex in SENSITIVE_PATTERNS.items():
                            matches = re.findall(pat_regex, content, re.IGNORECASE)
                            if matches:
                                finding[pat_name] = matches[:3]  # First 3 matches
                                finding["severity"] = "CRITICAL"

                        findings.append(finding)
                        severity = finding.get("severity", "HIGH")
                        status(f"Exposed: {fpath} [{severity}]", "critical" if severity == "CRITICAL" else "high")

                except Exception as e:
                    if "401" in str(e) or "403" in str(e):
                        pass  # Protected, skip
                    # else skip silently

        self.findings.extend(findings)
        status(f"Disclosure scan: {len(findings)} exposed file(s)", "success" if not findings else "critical")
        return findings

    async def scan_headers(self) -> list:
        """Check HTTP headers for info disclosure."""
        findings = []
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            try:
                resp = await s.get(self.target, headers=headers, timeout=10, ssl=False)
                h = resp.headers

                # Check server header
                server = h.get("Server", "")
                if server:
                    findings.append({"type":"Server Header","value":server,"severity":"LOW"})

                # Check X-Powered-By
                powered = h.get("X-Powered-By", "")
                if powered:
                    findings.append({"type":"X-Powered-By","value":powered,"severity":"LOW"})

                # Missing security headers
                missing = []
                if "X-Frame-Options" not in h: missing.append("X-Frame-Options")
                if "X-Content-Type-Options" not in h: missing.append("X-Content-Type-Options")
                if "Content-Security-Policy" not in h: missing.append("CSP")
                if "Strict-Transport-Security" not in h: missing.append("HSTS")

                if missing:
                    findings.append({"type":"Missing Security Headers","value":", ".join(missing),"severity":"MEDIUM"})

            except: pass
        return findings
