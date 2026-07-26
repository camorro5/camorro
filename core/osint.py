#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSINT — Instagram profile intelligence for targeted wordlists."""

import json
import os
import re
import requests
from .banner import info, ok, warn, err
from .session import Session


class OSINT:
    """Gathers public Instagram profile data and builds wordlist hints."""

    def __init__(self, username, output_dir="output", proxy=None):
        self.username = username.strip().lstrip("@")
        self.output_dir = output_dir
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self.data = {}
        self._raw = {}

    def scrape(self):
        """Scrape profile data from multiple endpoints."""
        info(f"Scanning @{self.username}...")
        headers = Session.build_headers()
        headers["X-IG-App-ID"] = "936619743392459"

        urls = [
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={self.username}",
            f"https://www.instagram.com/{self.username}/?__a=1&__d=1",
            f"https://www.instagram.com/{self.username}/",
        ]

        for url in urls:
            try:
                r = requests.get(
                    url,
                    headers=headers,
                    proxies=self.proxy,
                    timeout=20,
                )
                if r.status_code == 404:
                    err(f"Account @{self.username} not found")
                    return {}
                if r.status_code != 200:
                    continue

                ctype = r.headers.get("Content-Type", "")
                text = r.text or ""
                if "json" in ctype or text.strip().startswith("{"):
                    try:
                        self._raw = r.json()
                        self._parse_json()
                    except Exception:
                        continue
                else:
                    self._parse_html(text)

                if (
                    self.data.get("username")
                    or self.data.get("full_name")
                    or self.data.get("biography")
                    or self.data.get("followers")
                ):
                    self._save()
                    ok(f"OSINT OK — @{self.data.get('username', self.username)}")
                    self.print_summary()
                    return self.data
            except Exception:
                continue

        warn(
            f"Could not retrieve profile for @{self.username} "
            "(private, blocked, or login wall)"
        )
        # Minimal fallback so wordlist still has username
        self.data = {
            "id": "",
            "username": self.username,
            "full_name": "",
            "biography": "",
            "external_url": "",
            "is_private": False,
            "is_verified": False,
            "is_business": False,
            "business_category": "",
            "category": "",
            "followers": 0,
            "following": 0,
            "posts": 0,
            "profile_pic": "",
        }
        self._save()
        return {}

    def _parse_json(self):
        user = (
            self._raw.get("data", {}).get("user")
            or self._raw.get("graphql", {}).get("user")
            or self._raw.get("user")
            or {}
        )
        if not user:
            self.data = {}
            return

        self.data = {
            "id": str(user.get("id", "") or user.get("pk", "") or ""),
            "username": user.get("username", self.username) or self.username,
            "full_name": user.get("full_name", "") or "",
            "biography": user.get("biography", "") or user.get("bio", "") or "",
            "external_url": user.get("external_url", "") or "",
            "is_private": bool(user.get("is_private", False)),
            "is_verified": bool(user.get("is_verified", False)),
            "is_business": bool(user.get("is_business_account", False)),
            "business_category": user.get("business_category_name", "") or "",
            "category": user.get("category_name", "") or "",
            "followers": int(
                user.get("edge_followed_by", {}).get("count")
                or user.get("follower_count")
                or 0
            ),
            "following": int(
                user.get("edge_follow", {}).get("count")
                or user.get("following_count")
                or 0
            ),
            "posts": int(
                user.get("edge_owner_to_timeline_media", {}).get("count")
                or user.get("media_count")
                or 0
            ),
            "profile_pic": (
                user.get("profile_pic_url_hd")
                or user.get("profile_pic_url")
                or ""
            ),
        }

    def _parse_html(self, html):
        """Fallback extraction from public HTML."""
        m = re.search(r'"username"\s*:\s*"([^"]+)"', html)
        uname = m.group(1) if m else self.username

        m = re.search(r'"full_name"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        full = ""
        if m:
            try:
                full = json.loads(f'"{m.group(1)}"')
            except Exception:
                full = m.group(1)

        m = re.search(r'"biography"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        bio = ""
        if m:
            try:
                bio = json.loads(f'"{m.group(1)}"')
            except Exception:
                bio = m.group(1)

        m = re.search(
            r'"edge_followed_by"\s*:\s*\{\s*"count"\s*:\s*(\d+)', html
        )
        followers = int(m.group(1)) if m else 0
        m = re.search(r'"edge_follow"\s*:\s*\{\s*"count"\s*:\s*(\d+)', html)
        following = int(m.group(1)) if m else 0
        m = re.search(
            r'"edge_owner_to_timeline_media"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
            html,
        )
        posts = int(m.group(1)) if m else 0
        priv = '"is_private":true' in html or '"is_private": true' in html
        veri = '"is_verified":true' in html or '"is_verified": true' in html

        self.data = {
            "id": "",
            "username": uname,
            "full_name": full,
            "biography": bio,
            "external_url": "",
            "is_private": priv,
            "is_verified": veri,
            "is_business": False,
            "business_category": "",
            "category": "",
            "followers": followers,
            "following": following,
            "posts": posts,
            "profile_pic": "",
        }

    def _save(self):
        path = os.path.join(self.output_dir, self.username)
        os.makedirs(path, exist_ok=True)
        out = os.path.join(path, "osint.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_hints(self):
        """
        Everything useful for the wordlist engine.
        Followers/posts are shown in summary; lowercase tokens, years,
        phones, username parts feed password generation.
        """
        bio = self.data.get("biography", "") or ""
        name = self.data.get("full_name", "") or ""
        uname = self.data.get("username", self.username) or self.username

        blob = f"{bio} {name}"
        tokens = re.findall(r"[a-zA-Z\u0600-\u06FF0-9_]+", blob.lower())
        tokens = [t for t in tokens if 2 <= len(t) <= 32]

        years = re.findall(r"\b(19\d{2}|20[0-2]\d)\b", blob)
        phones = re.findall(r"(?:\+?\d[\d\s\-]{6,}\d)", bio)
        phones = [re.sub(r"\s+", "", p) for p in phones]

        stat_nums = []
        for n in (
            self.data.get("followers", 0),
            self.data.get("posts", 0),
            self.data.get("following", 0),
        ):
            try:
                n = int(n)
            except (TypeError, ValueError):
                continue
            if n and n < 10000000:
                s = str(n)
                stat_nums.append(s)
                if len(s) >= 2:
                    stat_nums.append(s[-2:])
                if len(s) >= 4:
                    stat_nums.append(s[-4:])

        user_parts = [
            p for p in re.split(r"[._\-\s]+", uname) if len(p) >= 2
        ]

        return {
            "username": uname,
            "full_name": name,
            "biography": bio,
            "bio_tokens": list(dict.fromkeys(tokens)),
            "years": list(dict.fromkeys(years)),
            "phones": phones,
            "followers": self.data.get("followers", 0),
            "following": self.data.get("following", 0),
            "posts": self.data.get("posts", 0),
            "stat_numbers": list(dict.fromkeys(stat_nums)),
            "user_parts": user_parts,
            "is_private": self.data.get("is_private", False),
            "external_url": self.data.get("external_url", ""),
            "category": (
                self.data.get("category")
                or self.data.get("business_category")
                or ""
            ),
        }

    def print_summary(self):
        d = self.data
        if not d:
            return
        print()
        print(f"  Name       : {d.get('full_name') or 'N/A'}")
        print(f"  Username   : @{d.get('username', self.username)}")
        print(f"  Private    : {d.get('is_private')}")
        print(f"  Verified   : {d.get('is_verified')}")
        print(f"  Followers  : {d.get('followers', 0):,}")
        print(f"  Following  : {d.get('following', 0):,}")
        print(f"  Posts      : {d.get('posts', 0):,}")
        if d.get("biography"):
            print(f"  Bio        : {d['biography'][:160]}")
        if d.get("external_url"):
            print(f"  URL        : {d['external_url']}")
        if d.get("category") or d.get("business_category"):
            print(
                f"  Category   : "
                f"{d.get('category') or d.get('business_category')}"
            )
        print()
