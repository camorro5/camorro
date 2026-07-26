#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Browser fingerprint rotation."""

import random
import uuid


class Session:
    DESKTOP_UA = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    ]

    MOBILE_UA = [
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Redmi Note 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    ]

    IG_APP_UA = [
        "Instagram 212.0.0.32.118 Android (34/14; 420dpi; 1080x2400; samsung; SM-S928B; e3q; qcom; en_US; 312484483)",
        "Instagram 310.0.0.25.109 Android (34/14; 440dpi; 1080x2400; Google; Pixel 9; shiba; shiba; en_US; 543310651)",
        "Instagram 303.1.0.11.110 Android (33/13; 480dpi; 1080x2340; Xiaomi; 2201116SG; bree; qcom; en_US; 520161702)",
    ]

    LANGS = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-US,en;q=0.9,ar;q=0.8",
        "fr-FR,fr;q=0.9,en;q=0.8",
        "ar-MA,ar;q=0.9,en;q=0.8",
    ]

    APP_ID = "936619743392459"

    @classmethod
    def random_ua(cls, mobile=True):
        pool = (cls.MOBILE_UA + cls.DESKTOP_UA) if mobile else cls.DESKTOP_UA
        return random.choice(pool)

    @classmethod
    def ig_app_ua(cls):
        return random.choice(cls.IG_APP_UA)

    @classmethod
    def new_device_ids(cls):
        return {
            "X-IG-Device-ID": str(uuid.uuid4()),
            "X-IG-Family-Device-ID": str(uuid.uuid4()),
            "X-IG-Android-ID": f"android-{uuid.uuid4().hex[:16]}",
        }

    @classmethod
    def build_headers(cls, username=None, mobile=True, for_api=True):
        ua = cls.random_ua(mobile=mobile)
        ref = (
            f"https://www.instagram.com/{username}/"
            if username
            else "https://www.instagram.com/"
        )
        if for_api:
            return {
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": random.choice(cls.LANGS),
                "Accept-Encoding": "gzip, deflate",
                "Origin": "https://www.instagram.com",
                "Referer": ref,
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-IG-App-ID": cls.APP_ID,
                "X-Requested-With": "XMLHttpRequest",
                "X-ASBD-ID": "129477",
                "X-IG-WWW-Claim": "0",
                "DNT": "1",
            }
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(cls.LANGS),
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
        }
