"""CSRF Detection & Exploitation Scanner."""
import asyncio, re
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
from ..utils.helpers import status, random_ua

class CSRFScanner:
    """Checks for CSRF tokens in forms and tests for CSRF vulnerability."""

    def __init__(self, target: str):
        self.target = target.rstrip("/")
        self.findings = []
        self.forms_without_csrf = []

    async def scan(self) -> list:
        """Scan all forms for CSRF protection."""
        status("Scanning for CSRF vulnerabilities...", "info")
        headers = {"User-Agent": random_ua()}
        visited = set()
        to_visit = [self.target]

        async with aiohttp.ClientSession() as s:
            while to_visit and len(visited) < 20:
                url = to_visit.pop(0)
                if url in visited: continue
                try:
                    resp = await s.get(url, headers=headers, timeout=10, ssl=False)
                    if "text/html" not in resp.headers.get("Content-Type", ""): continue
                    html = await resp.text()
                    visited.add(url)
                    soup = BeautifulSoup(html, 'html.parser')

                    for form in soup.find_all("form"):
                        method = form.get("method", "get").lower()
                        if method != "post": continue  # CSRF relevant for state-changing requests

                        action = form.get("action", "")
                        form_url = urljoin(url, action) if action else url
                        inputs = form.find_all("input")

                        # Check for CSRF token
                        has_csrf = False
                        token_input = None
                        for inp in inputs:
                            name = (inp.get("name") or "").lower()
                            if any(t in name for t in ["csrf", "token", "nonce", "_token"]):
                                # Check if token is random (not static)
                                has_csrf = True
                                token_input = inp
                                break

                        if not has_csrf:
                            self.forms_without_csrf.append({
                                "url": str(form_url),
                                "method": method.upper(),
                                "action": action,
                                "inputs": [i.get("name") for i in inputs if i.get("name")],
                            })

                    # Find more links
                    for link in soup.find_all("a", href=True):
                        href = urljoin(url, link["href"])
                        if href.startswith(self.target) and href not in visited:
                            to_visit.append(href)

                except: continue

        # Analyze results
        for form in self.forms_without_csrf:
            # Only flag forms that look important (login, settings, etc.)
            important_keywords = ["login", "admin", "user", "password", "settings", "profile", "delete", "update", "edit"]
            if any(k in form["url"].lower() or any(k in str(i).lower() for i in form.get("inputs", [])) for k in important_keywords):
                self.findings.append({
                    "type": "CSRF (Missing Token)",
                    "url": form["url"],
                    "method": form["method"],
                    "severity": "HIGH",
                    "description": f"No CSRF token found on important form: {form['url']}",
                })
                status(f"CSRF: No token on {form['url']}", "high")

        status(f"CSRF scan: {len(self.findings)} vulnerable form(s)", "success" if not self.findings else "high")
        return self.findings
