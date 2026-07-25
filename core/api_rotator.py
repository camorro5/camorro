#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camoro API rotator + device fingerprint forge."""

import hashlib
import random
import string
import time
import uuid
from dataclasses import dataclass, field


LOGIN_ENDPOINTS = [
    {
        "name": "web_ajax_www",
        "login_url": "https://www.instagram.com/accounts/login/ajax/",
        "home_url": "https://www.instagram.com/accounts/login/",
        "origin": "https://www.instagram.com",
        "referer": "https://www.instagram.com/accounts/login/",
        "style": "web",
    },
    {
        "name": "web_ajax_www_alt",
        "login_url": "https://www.instagram.com/api/v1/web/accounts/login/ajax/",
        "home_url": "https://www.instagram.com/accounts/login/",
        "origin": "https://www.instagram.com",
        "referer": "https://www.instagram.com/accounts/login/",
        "style": "web",
    },
    {
        "name": "i_web_login",
        "login_url": "https://i.instagram.com/api/v1/web/accounts/login/ajax/",
        "home_url": "https://www.instagram.com/accounts/login/",
        "origin": "https://www.instagram.com",
        "referer": "https://www.instagram.com/accounts/login/",
        "style": "web",
    },
    {
        "name": "b_www_ajax",
        "login_url": "https://www.instagram.com/accounts/login/ajax/",
        "home_url": "https://www.instagram.com/",
        "origin": "https://www.instagram.com",
        "referer": "https://www.instagram.com/",
        "style": "web",
    },
    {
        "name": "mobile_i_login",
        "login_url": "https://i.instagram.com/api/v1/accounts/login/",
        "home_url": "https://i.instagram.com/",
        "origin": "https://www.instagram.com",
        "referer": "https://www.instagram.com/",
        "style": "mobile",
    },
]

APP_IDS = [
    "936619743392459",
    "1217981644879628",
    "124024574287414",
    "567067343352427",
]

ASBD_IDS = ["129477", "198387", "359341"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 Instagram 312.0.0.0.0",
    "Instagram 310.0.0.0.0 Android (34/14; 440dpi; 1080x2400; Google/google; Pixel 8; shiba; shiba; en_US; 512345678)",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "ar-SA,ar;q=0.9,en;q=0.8",
    "ar-EG,ar;q=0.9,en-US;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
]


@dataclass
class DeviceProfile:
    device_id: str
    family_device_id: str
    phone_id: str
    uuid: str
    android_id: str
    mid: str
    user_agent: str
    app_id: str
    asbd_id: str
    accept_language: str
    endpoint: dict
    created_at: float = field(default_factory=time.time)

    def headers_base(self):
        h = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate",
            "Origin": self.endpoint["origin"],
            "Referer": self.endpoint["referer"],
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "X-IG-App-ID": self.app_id,
            "X-ASBD-ID": self.asbd_id,
            "X-IG-WWW-Claim": "0",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if self.endpoint.get("style") == "mobile":
            h.update(
                {
                    "X-IG-Device-ID": self.device_id,
                    "X-IG-Family-Device-ID": self.family_device_id,
                    "X-IG-Android-ID": self.android_id,
                    "X-IG-Connection-Type": random.choice(["WIFI", "MOBILE.LTE"]),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
            )
        return h


class DeviceForge:
    @staticmethod
    def _hex(n=16):
        return hashlib.md5(uuid.uuid4().bytes).hexdigest()[:n]

    @staticmethod
    def _ig_uuid():
        return str(uuid.uuid4())

    @classmethod
    def mid(cls):
        alphabet = string.ascii_letters + string.digits + "_-"
        return "".join(random.choice(alphabet) for _ in range(28))

    @classmethod
    def forge(cls, endpoint=None):
        ep = endpoint or random.choice(LOGIN_ENDPOINTS)
        return DeviceProfile(
            device_id=cls._ig_uuid(),
            family_device_id=cls._ig_uuid(),
            phone_id=cls._ig_uuid(),
            uuid=cls._ig_uuid(),
            android_id="android-" + cls._hex(16),
            mid=cls.mid(),
            user_agent=random.choice(USER_AGENTS),
            app_id=random.choice(APP_IDS),
            asbd_id=random.choice(ASBD_IDS),
            accept_language=random.choice(ACCEPT_LANGUAGES),
            endpoint=ep,
        )


class APIRotator:
    def __init__(self, strategy="round_robin"):
        self.strategy = strategy
        self._idx = 0
        self._sticky_left = 0
        self._sticky_ep = None
        self.sticky_every = 5
        self.endpoints = list(LOGIN_ENDPOINTS)

    def next_identity(self):
        ep = self._next_endpoint()
        return DeviceForge.forge(ep)

    def _next_endpoint(self):
        if self.strategy == "random":
            return random.choice(self.endpoints)
        if self.strategy == "sticky_burst":
            if self._sticky_left <= 0 or self._sticky_ep is None:
                self._sticky_ep = random.choice(self.endpoints)
                self._sticky_left = self.sticky_every
            self._sticky_left -= 1
            return self._sticky_ep
        ep = self.endpoints[self._idx % len(self.endpoints)]
        self._idx += 1
        return ep

    def rotate_on_block(self):
        self._idx += random.randint(1, max(1, len(self.endpoints)))
        self._sticky_left = 0
        self._sticky_ep = None
        return self.next_identity()
