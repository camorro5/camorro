#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagram web login API."""

import re
import time
import random
import requests
from .session import Session


class InstagramAPI:
    def __init__(self, proxy=None):
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self.session = requests.Session()
        self._rotate_identity()
        if self.proxy:
            self.session.proxies.update(self.proxy)

    def _rotate_identity(self):
        self.session.headers.clear()
        self.session.headers.update(Session.build_headers(for_api=True))
        self.session.headers.update(Session.new_device_ids())

    def set_proxy(self, proxy_url):
        if proxy_url:
            self.proxy = {"http": proxy_url, "https": proxy_url}
            self.session.proxies.update(self.proxy)
        else:
            self.proxy = None
            self.session.proxies.clear()

    def _warm(self):
        try:
            r = self.session.get("https://www.instagram.com/", timeout=20, allow_redirects=True)
            csrf = self.session.cookies.get("csrftoken") or ""
            if not csrf:
                m = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', r.text or "")
                if m:
                    csrf = m.group(1)
                    self.session.cookies.set("csrftoken", csrf, domain=".instagram.com")
            if csrf:
                self.session.headers["X-CSRFToken"] = csrf
            time.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass

    def profile_exists(self, username):
        username = username.strip().lstrip("@")
        self._rotate_identity()
        try:
            r = self.session.get(f"https://www.instagram.com/{username}/", timeout=20, allow_redirects=True)
            if r.status_code == 404:
                return False
            if r.status_code == 200:
                t = r.text or ""
                if "Sorry, this page isn't available" in t:
                    return False
                return True
        except Exception:
            return None
        return None

    def try_login(self, username, password):
        username = username.strip().lstrip("@")
        self._rotate_identity()
        if self.proxy:
            self.session.proxies.update(self.proxy)
        try:
            self._warm()
            csrf = self.session.cookies.get("csrftoken") or ""
            self.session.headers["X-CSRFToken"] = csrf
            self.session.headers["Content-Type"] = "application/x-www-form-urlencoded"
            self.session.headers["X-Requested-With"] = "XMLHttpRequest"
            self.session.headers["Referer"] = "https://www.instagram.com/accounts/login/"
            ts = int(time.time())
            data = {
                "username": username,
                "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{ts}:{password}",
                "queryParams": "{}",
                "optIntoOneTap": "false",
                "trustedDeviceRecords": "{}",
            }
            r = self.session.post("https://www.instagram.com/api/v1/web/accounts/login/ajax/", data=data, timeout=25)
            try:
                j = r.json()
            except Exception:
                j = {}
            if j.get("authenticated") is True:
                return {"success": True, "status": "ok", "raw": j}
            if j.get("user") is False:
                return {"success": False, "status": "invalid_user", "raw": j}
            msg = (j.get("message") or "").lower()
            if "checkpoint" in msg or j.get("checkpoint_url") or j.get("two_factor_required"):
                return {"success": False, "status": "checkpoint", "raw": j}
            if r.status_code == 429 or "wait" in msg or "rate" in msg:
                return {"success": False, "status": "rate_limited", "raw": j}
            if j.get("authenticated") is False:
                return {"success": False, "status": "bad_password", "raw": j}
            if j.get("status") == "fail":
                if "password" in msg or r.status_code == 400:
                    return {"success": False, "status": "bad_password", "raw": j}
                return {"success": False, "status": "error", "raw": j}
            return {"success": False, "status": "bad_password", "raw": j}
        except requests.exceptions.Timeout:
            return {"success": False, "status": "timeout"}
        except requests.exceptions.ProxyError:
            return {"success": False, "status": "connection_error"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status": "connection_error"}
        except Exception as e:
            return {"success": False, "status": "error", "error": str(e)}
