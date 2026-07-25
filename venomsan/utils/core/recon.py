"""Reconnaissance - CMS detection, technology fingerprinting, WAF detection, port scanning."""
import asyncio, re, random
from typing import Optional
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
from ..utils.helpers import status, random_ua, display_table
from ..utils.network import COMMON_PORTS, resolve_host

class CMSDetector:
    """Advanced CMS & Technology Detector."""

    SIGNATURES = {
        "Joomla": [(r'<meta name="generator" content="Joomla!',None),(r'/index\.php\?option=com_',None),(r'/administrator/index\.php',None)],
        "WordPress": [(r'/wp-content/',None),(r'/wp-admin/',None),(r'wp-json',None)],
        "Drupal": [(r'/sites/default/',None),(r'Drupal\.settings',None)],
        "Magento": [(r'/skin/frontend/',None),(r'Magento',None)],
        "PrestaShop": [(r'PrestaShop',None)],
    }

    JOOMLA_COMPS = {
        "com_jumi":"Jumi - Custom file inclusion (HIGH RISK)",
        "com_k2":"K2 - Content management",
        "com_content":"Default content",
        "com_users":"User management",
        "com_media":"Media manager",
        "com_installer":"Extension installer",
        "com_config":"Configuration",
        "com_templates":"Template editor (RCE vector)",
        "com_finder":"Smart search",
        "com_contact":"Contact forms",
        "com_joomlaupdate":"Joomla updater (RCE vector)",
    }

    def __init__(self):
        self.findings = {}

    async def detect(self, url: str) -> dict:
        url = url.rstrip("/")
        result = {"url":url,"cms":"unknown","version":None,"admin_url":None,"components":[],"interesting_files":[],"technologies":[],"server":None,"php_version":None,"waf":None}

        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            try:
                resp = await s.get(url, headers=headers, timeout=10, ssl=False)
                html = await resp.text()
                result["server"] = resp.headers.get("Server","")
                result["php_version"] = resp.headers.get("X-Powered-By","")

                soup = BeautifulSoup(html, 'html.parser')
                meta = soup.find("meta", {"name":"generator"})
                if meta:
                    content = meta.get("content","")
                    result["version"] = content
                    if "joomla" in content.lower():
                        result["cms"] = "Joomla"

                for cms, patterns in self.SIGNATURES.items():
                    for pat, _ in patterns:
                        if re.search(pat, html, re.IGNORECASE):
                            result["cms"] = cms
                            break
                    if result["cms"] != "unknown":
                        break

                # Technologies
                if "X-Powered-By" in resp.headers or ".php" in html:
                    result["technologies"].append("PHP")
                if "jquery" in html.lower():
                    result["technologies"].append("jQuery")
                if "bootstrap" in html.lower():
                    result["technologies"].append("Bootstrap")
                if "font-awesome" in html.lower():
                    result["technologies"].append("FontAwesome")

                # WAF detection
                if "cf-ray" in str(resp.headers).lower():
                    result["waf"] = "Cloudflare"
                elif "x-sucuri" in str(resp.headers).lower():
                    result["waf"] = "Sucuri"
                elif "mod_security" in str(resp.headers).lower():
                    result["waf"] = "ModSecurity"

            except Exception as e:
                result["error"] = str(e)

        # Joomla specific
        if result["cms"] in ["Joomla","unknown"]:
            await self._joomla_checks(url, result)

        return result

    async def _joomla_checks(self, url, result):
        async with aiohttp.ClientSession() as s:
            headers = {"User-Agent": random_ua()}

            # Admin panel
            admin = f"{url}/administrator/"
            try:
                resp = await s.get(admin, headers=headers, timeout=8, ssl=False)
                if resp.status in [200,301,302,401,403]:
                    result["admin_url"] = admin
                    html = await resp.text()
                    if "joomla" in html.lower():
                        result["cms"] = "Joomla"
                        status(f"Joomla admin: {admin}", "success")
                    # Check CAPTCHA
                    if "captcha" in html.lower() or "g-recaptcha" in html:
                        status("CAPTCHA detected on admin login", "warning")
            except: pass

            # Version from XML
            for vu in ["/administrator/manifests/files/joomla.xml","/language/en-GB/en-GB.xml"]:
                try:
                    resp = await s.get(f"{url}{vu}", headers=headers, timeout=5, ssl=False)
                    if resp.status == 200:
                        txt = await resp.text()
                        vm = re.search(r'<version>([^<]+)</version>', txt)
                        if vm:
                            result["version"] = f"Joomla {vm.group(1)}"
                            result["interesting_files"].append({"path":vu,"value":vm.group(1)})
                            status(f"Version: {vm.group(1)}", "success")
                            break
                except: pass

            # Components
            for comp, desc in self.JOOMLA_COMPS.items():
                try:
                    resp = await s.get(f"{url}/index.php?option={comp}", headers=headers, timeout=5, ssl=False)
                    if resp.status == 200:
                        txt = await resp.text()
                        if len(txt) > 300 and "404" not in txt[:200] and "unpublished" not in txt[:300].lower():
                            result["components"].append({"name":comp,"description":desc,"accessible":True})
                except: pass

            # Interesting files
            for f in ["/README.txt","/robots.txt","/htaccess.txt","/configuration.php.bak","/configuration.php~"]:
                try:
                    resp = await s.get(f"{url}{f}", headers=headers, timeout=5, ssl=False)
                    if resp.status == 200:
                        result["interesting_files"].append({"path":f,"status":200})
                        if "configuration.php" in f:
                            status(f"CRITICAL: Backup file exposed: {f}", "critical")
                except: pass


class PortScanner:
    """Async port scanner."""

    def __init__(self, concurrency=200, timeout=3.0):
        self.concurrency = concurrency
        self.timeout = timeout
        self.sem = asyncio.Semaphore(concurrency)

    async def _scan_port(self, host: str, port: int) -> dict:
        async with self.sem:
            await asyncio.sleep(random.uniform(0.001, 0.01))
            try:
                r, w = await asyncio.wait_for(asyncio.open_connection(host, port), self.timeout)
                # Banner grab
                try:
                    banner = await asyncio.wait_for(r.read(1024), 0.5)
                    try: banner = banner.decode("utf-8", errors="replace")[:200]
                    except: banner = banner.hex()[:200]
                except: banner = None
                w.close()
                await w.wait_closed()
                return {"host":host,"port":port,"state":"open","service":COMMON_PORTS.get(port,"?"),"banner":banner}
            except asyncio.TimeoutError:
                return {"host":host,"port":port,"state":"filtered"}
            except:
                return {"host":host,"port":port,"state":"closed"}

    async def scan(self, host: str, ports: list[int]) -> list[dict]:
        resolved = resolve_host(host) or host
        status(f"Scanning {len(ports)} ports on {resolved}...", "info")
        tasks = [self._scan_port(resolved, p) for p in ports]
        results = []
        scanned = 0
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            scanned += 1
            if scanned % 50 == 0 or scanned == len(ports):
                open_count = sum(1 for x in results if x["state"]=="open")
                status(f"Progress: {scanned}/{len(ports)} | Open: {open_count}", "info")
        return results

    async def scan_common(self, host: str) -> list[dict]:
        ports = sorted(set(COMMON_PORTS.keys()) | {8000,8088,8888,9000,3000,5000})
        return await self.scan(host, ports)
