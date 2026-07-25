#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camoro OSINT — public Instagram profile intelligence."""

import json
import os
import random
import re
import time
from datetime import datetime

import requests

from core.banner import Colors, info, success, warn, error, ok

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class CamoroOSINT:
    def __init__(self, username, output_dir="output", proxy=None):
        self.username = username.strip().lstrip("@")
        self.output_dir = output_dir
        self.proxy = proxy
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.profile_data = {}
        self.profile_dir = ""

    def _get(self, url, **kwargs):
        try:
            return self.session.get(url, timeout=25, **kwargs)
        except requests.RequestException as exc:
            error(f"Request failed: {exc}")
            return None

    def scrape(self):
        info(f"Collecting OSINT on @{self.username} ...")
        data = self._scrape_web_profile()
        if not data:
            data = self._scrape_og_fallback()
        if not data:
            error(f"Username @{self.username} not found or blocked")
            return {}
        self.profile_data = data
        self._print_profile()
        self._save()
        return self.profile_data

    def _scrape_web_profile(self):
        endpoints = [
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={self.username}",
            f"https://i.instagram.com/api/v1/users/web_profile_info/?username={self.username}",
        ]
        headers_api = {
            "User-Agent": random.choice(USER_AGENTS),
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/{self.username}/",
            "Accept": "*/*",
        }
        self._get(f"https://www.instagram.com/{self.username}/")
        time.sleep(1)
        for url in endpoints:
            try:
                r = self.session.get(url, headers=headers_api, timeout=25)
            except requests.RequestException:
                continue
            if r.status_code == 200:
                try:
                    payload = r.json()
                    user = payload.get("data", {}).get("user") or payload.get("user")
                    if user:
                        return self._normalize_user(user)
                except (ValueError, KeyError, TypeError):
                    pass
            time.sleep(0.8)
        return {}

    def _scrape_og_fallback(self):
        r = self._get(f"https://www.instagram.com/{self.username}/")
        if r is None or r.status_code != 200:
            return {}
        html = r.text
        if "Sorry, this page isn't available" in html or "Page Not Found" in html:
            return {}

        def meta(prop=None, name=None):
            if prop:
                m = re.search(
                    rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']',
                    html,
                    re.I,
                )
                if not m:
                    m = re.search(
                        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']{re.escape(prop)}["\']',
                        html,
                        re.I,
                    )
            else:
                m = re.search(
                    rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
                    html,
                    re.I,
                )
            return m.group(1) if m else ""

        desc = meta(prop="og:description") or meta(name="description")
        title = meta(prop="og:title")
        image = meta(prop="og:image")
        url = meta(prop="og:url") or f"https://www.instagram.com/{self.username}/"

        followers = following = posts = "?"
        m = re.search(
            r"([\d.,KMkm]+)\s*Followers?,\s*([\d.,KMkm]+)\s*Following,\s*([\d.,KMkm]+)\s*Posts?",
            desc,
            re.I,
        )
        if m:
            followers, following, posts = m.group(1), m.group(2), m.group(3)

        name = title.split("(")[0].strip(" •-|") if title else self.username
        bio = ""
        if " - " in desc:
            bio = desc.split(" - ", 1)[-1].strip()

        shared = re.search(r'"biography"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        if shared:
            try:
                bio = bytes(shared.group(1), "utf-8").decode("unicode_escape")
            except Exception:
                bio = shared.group(1)

        is_private = '"is_private":true' in html or 'is_private":true' in html
        is_verified = '"is_verified":true' in html or 'is_verified":true' in html

        return {
            "username": self.username,
            "full_name": name,
            "biography": bio,
            "followers": followers,
            "following": following,
            "posts": posts,
            "profile_pic_url": image,
            "external_url": "",
            "is_private": str(is_private),
            "is_verified": str(is_verified),
            "is_business": "unknown",
            "business_category": "",
            "connected_fb": "unknown",
            "joined_recently": "unknown",
            "profile_url": url,
            "user_id": "",
            "scraped_at": datetime.utcnow().isoformat() + "Z",
        }

    def _normalize_user(self, user):
        return {
            "username": user.get("username", self.username),
            "full_name": user.get("full_name", ""),
            "biography": user.get("biography", ""),
            "followers": str(
                user.get("edge_followed_by", {}).get("count")
                or user.get("follower_count", "?")
            ),
            "following": str(
                user.get("edge_follow", {}).get("count")
                or user.get("following_count", "?")
            ),
            "posts": str(
                user.get("edge_owner_to_timeline_media", {}).get("count")
                or user.get("media_count", "?")
            ),
            "profile_pic_url": user.get("profile_pic_url_hd")
            or user.get("profile_pic_url", ""),
            "external_url": user.get("external_url") or "",
            "is_private": str(user.get("is_private", False)),
            "is_verified": str(user.get("is_verified", False)),
            "is_business": str(user.get("is_business_account", False)),
            "business_category": str(user.get("business_category_name") or ""),
            "connected_fb": str(user.get("connected_fb_page") or ""),
            "joined_recently": str(user.get("is_joined_recently", False)),
            "profile_url": f"https://www.instagram.com/{user.get('username', self.username)}/",
            "user_id": str(user.get("id") or user.get("pk") or ""),
            "scraped_at": datetime.utcnow().isoformat() + "Z",
        }

    def _print_profile(self):
        d = self.profile_data
        print(f"\n{Colors.HEADER}{'─' * 48}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}  Results · scan for @{d.get('username')}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'─' * 48}{Colors.ENDC}")
        labels = [
            ("Username", "username"),
            ("Full Name", "full_name"),
            ("URL", "profile_url"),
            ("User ID", "user_id"),
            ("Followers", "followers"),
            ("Following", "following"),
            ("Posts", "posts"),
            ("Bio", "biography"),
            ("External URL", "external_url"),
            ("Private", "is_private"),
            ("Verified", "is_verified"),
            ("Business", "is_business"),
            ("Business Category", "business_category"),
            ("Connected FB", "connected_fb"),
            ("Joined Recently", "joined_recently"),
            ("Profile Pic", "profile_pic_url"),
        ]
        for label, key in labels:
            val = d.get(key, "")
            if val in ("", "None", "null"):
                val = "-"
            print(f"  {Colors.BOLD}{label:20}{Colors.ENDC}: {val}")
        print(f"{Colors.HEADER}{'─' * 48}{Colors.ENDC}\n")

    def _save(self):
        base = os.path.join(self.output_dir, self.username)
        os.makedirs(base, exist_ok=True)
        if os.path.exists(os.path.join(base, "osint.json")):
            i = 1
            while os.path.exists(os.path.join("%s_%d" % (base, i), "osint.json")):
                i += 1
            base = "%s_%d" % (base, i)
            os.makedirs(base, exist_ok=True)

        self.profile_dir = base
        path = os.path.join(base, "osint.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.profile_data, f, ensure_ascii=False, indent=2)
        success(f"OSINT saved → {path}")

        pic = self.profile_data.get("profile_pic_url") or ""
        if pic.startswith("http"):
            try:
                r = self.session.get(pic, timeout=20)
                if r.status_code == 200:
                    pp = os.path.join(base, "profile_pic.jpg")
                    with open(pp, "wb") as f:
                        f.write(r.content)
                    ok(f"Profile picture saved → {pp}")
            except Exception:
                warn("Could not download profile picture")

    def hints_for_wordlist(self):
        d = self.profile_data or {}
        bio = d.get("biography") or ""
        name = d.get("full_name") or ""
        parts = re.findall(r"[A-Za-z\u0600-\u06FF]{2,}", "%s %s" % (name, bio))
        years = re.findall(r"(?:19|20)\d{2}", "%s %s" % (name, bio))
        phones = re.findall(r"\+?\d{8,15}", bio)
        return {
            "username": d.get("username") or self.username,
            "full_name": name,
            "bio_tokens": list(dict.fromkeys(parts))[:30],
            "years": list(dict.fromkeys(years)),
            "phones": phones,
            "external_url": d.get("external_url") or "",
        }
