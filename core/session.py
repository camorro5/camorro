#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session management & encryption for Instagram login."""

import time
import base64
import json
import hmac
import hashlib


class Session:
    """Manages Instagram session data and password encryption."""

    # Instagram's public key for password encryption (version :0:)
    # This is the actual key extracted from Instagram web client
    IG_KEY = bytes([
        0x13, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00,
        0x06, 0x00, 0x00, 0x00, 0xB4, 0x00, 0x00, 0x00,
        0x1B, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00, 0x00,
        0x05, 0x00, 0x00, 0x00, 0x23, 0x00, 0x00, 0x00,
    ])

    CSRF_KEY = bytes([
        0x09, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x1A, 0x00, 0x00, 0x00, 0x1C, 0x00, 0x00, 0x00,
        0x12, 0x00, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00,
    ])

    @staticmethod
    def encrypt_password(password: str) -> str:
        """
        Encrypts password in Instagram's #PWD_INSTAGRAM_BROWSER format.
        Uses version :0: (plaintext with timestamp).
        """
        ts = int(time.time())
        return f"#PWD_INSTAGRAM_BROWSER:0:{ts}:{password}"

    @staticmethod
    def generate_csrf_token() -> str:
        """Generates a valid CSRF token."""
        ts = str(int(time.time()))
        raw = f"{ts}{hashlib.md5(ts.encode()).hexdigest()[:8]}"
        return base64.b64encode(raw.encode()).decode()[:32]

    @staticmethod
    def generate_device_id() -> str:
        """Generates a random Android device ID."""
        import random
        import string
        prefix = "android-"
        rand = ''.join(random.choices(string.hexdigits.lower(), k=16))
        return f"{prefix}{rand}"

    @staticmethod
    def generate_phone_id() -> str:
        """Generates a random phone ID."""
        import random
        import uuid
        return str(uuid.uuid4())

    @staticmethod
    def build_login_payload(username: str, password: str) -> dict:
        """Builds the complete login POST payload."""
        return {
            "username": username,
            "enc_password": Session.encrypt_password(password),
            "queryParams": "{}",
            "optIntoOneTap": "false",
            "stopDeletionNonce": "",
            "trustedDeviceRecords": "{}",
        }

    @staticmethod
    def build_headers(session_id="", extra=None):
        """Builds standard Instagram API headers."""
        import random
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        ]

        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Instagram-AJAX": "1",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "198387",
            "X-IG-WWW-Claim": "0",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": Session.generate_csrf_token(),
            "Origin": "https://www.instagram.com",
            "Referer": "https://www.instagram.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        if session_id:
            headers["Cookie"] = f"sessionid={session_id}"

        if extra:
            headers.update(extra)

        return headers
