"""Directory & Parameter Fuzzer."""
import asyncio
from pathlib import Path
from typing import Optional
import aiohttp
from ..utils.helpers import status, random_ua

# Common directory wordlist (built-in)
DIRS = [
    "admin","administrator","wp-admin","wp-login","login","cpanel",
    "phpmyadmin","phpMyAdmin","mysql","adminer",
    "backup","backups","old","new","test","dev","staging",
    "api","v1","v2","api/v1","api/v2","graphql",
    "upload","uploads","files","images","img","css","js","static","assets",
    "config","conf","includes","inc","logs","tmp","temp",
    ".git",".svn",".env",".htaccess","robots.txt",
    "readme","README","CHANGELOG","license",
    "shell","cmd","shell.php","admin.php","info.php","phpinfo.php",
    "install","installation","setup",
]

# Parameter names to fuzz
PARAMS = [
    "id","page","file","path","url","redirect","return","next",
    "cmd","command","exec","action","do","task","view","layout",
    "user","username","pass","password","passwd","email","token",
    "lang","language","locale","type","format","template","theme",
    "q","query","search","keyword","s",
    "sort","order","dir","limit","offset","page_id",
]

class WebFuzzer:
    """Directory and parameter fuzzing engine."""

    def __init__(self, target: str, concurrency: int = 50):
        self.target = target.rstrip("/")
        self.concurrency = concurrency
        self.sem = asyncio.Semaphore(concurrency)
        self.results = []

    async def _check_path(self, session, path: str) -> Optional[dict]:
        async with self.sem:
            url = f"{self.target}/{path}"
            headers = {"User-Agent": random_ua()}
            try:
                resp = await session.get(url, headers=headers, timeout=5, ssl=False, allow_redirects=False)
                if resp.status in [200, 301, 302, 401, 403]:
                    return {"path":f"/{path}","status":resp.status,"size":len(await resp.text())}
            except: pass
        return None

    async def fuzz_dirs(self, wordlist: Optional[list] = None) -> list:
        """Fuzz directories."""
        words = wordlist or DIRS
        status(f"Fuzzing {len(words)} directories...", "info")

        async with aiohttp.ClientSession() as s:
            tasks = [self._check_path(s, w) for w in words]
            results = []
            for coro in asyncio.as_completed(tasks):
                r = await coro
                if r:
                    results.append(r)
                    status(f"Found: /{r['path']} [{r['status']}]", "success" if r['status']==200 else "info")

        self.results = sorted(results, key=lambda x: x['status'])
        status(f"Dir fuzz: {len(self.results)} found", "success")
        return self.results

    async def fuzz_params(self) -> list:
        """Fuzz for hidden parameters."""
        findings = []
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            for param in PARAMS[:20]:
                try:
                    url = f"{self.target}/?{param}=FUZZ"
                    resp = await s.get(url, headers=headers, timeout=5, ssl=False)
                    status_code = resp.status
                    html = await resp.text()

                    # Check if param is reflected or causes different response
                    if "FUZZ" in html:
                        findings.append({"parameter":param,"type":"reflected","url":url})
                        status(f"Reflected param: {param}", "info")
                except: pass

        return findings
