#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSINT — Instagram profile intelligence gathering."""

import json
import os
import re
import requests
from .banner import info, ok, warn, err
from .session import Session


class OSINT:
    """Gathers public Instagram profile data."""

    def __init__(self, username, output_dir="output", proxy=None):
        self.username = username
        self.output_dir = output_dir
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self.data = {}
        self._raw = {}

    def scrape(self):
        """Scrape profile data from Instagram."""
        info(f"Scanning @{self.username}...")

        # Try multiple endpoints
        urls = [
            f"https://www.instagram.com/{self.username}/?__a=1&__d=1",
            f"https://www.instagram.com/{self.username}/?__a=1",
            f"https://i.instagram.com/api/v1/users/web_profile_info/?username={self.username}",
        ]

        for url in urls:
            try:
                headers = Session.build_headers()
                r = requests.get(url, headers=headers, proxies=self.proxy, timeout=15)

                if r.status_code == 200:
                    self._raw = r.json()
                    self._parse()
                    self._save()
                    return self.data
                elif r.status_code == 404:
                    err(f"Account @{self.username} not found")
                    return {}
            except Exception as e:
                continue

        warn(f"Could not retrieve profile for @{self.username} (private or blocked)")
        return {}

    def _parse(self):
        """Parse Instagram's JSON response into structured data."""
        graphql = self._raw.get("graphql", {})
        user = graphql.get("user", self._raw.get("user", {}))

        self.data = {
            "id": user.get("id", ""),
            "username": user.get("username", self.username),
            "full_name": user.get("full_name", ""),
            "biography": user.get("biography", ""),
            "external_url": user.get("external_url", ""),
            "is_private": user.get("is_private", False),
            "is_verified": user.get("is_verified", False),
            "is_business": user.get("is_business_account", False),
            "business_category": user.get("business_category_name", ""),
            "category": user.get("category_name", ""),
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "profile_pic": user.get("profile_pic_url_hd", user.get("profile_pic_url", "")),
            "highlight_reel_count": user.get("highlight_reel_count", 0),
        }

    def _save(self):
        """Save OSINT data as JSON."""
        path = os.path.join(self.output_dir, self.username)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "osint.json"), "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_hints(self):
        """Extract wordlist hints from profile data."""
        bio = self.data.get("biography", "")
        name = self.data.get("full_name", "")

        tokens = re.findall(r"[a-zA-Z0-9_]+", bio.lower())
        tokens = [t for t in tokens if len(t) >= 3]

        years = re.findall(r"\b(19\d{2}|20\d{2})\b", bio)
        phones = re.findall(r"[\d\s\-\+\(\)]{7,}", bio)

        return {
            "username": self.username,
            "full_name": name,
            "bio_tokens": list(set(tokens)),
            "years": list(set(years)),
            "phones": phones,
        }

    def print_summary(self):
        """Display profile summary."""
        d = self.data
        if not d:
            return

        print(f"\n  {d['full_name'] or 'N/A'}  (@{d['username']})")
        if d["is_verified"]:
            print("  ✓ Verified")
        if d["is_private"]:
            print("  🔒 PRIVATE account")
        if d["is_business"]:
            print(f"  💼 Business: {d.get('business_category', 'N/A')}")

        print(f"  👥 Followers : {d['followers']:,}")
        print(f"  👤 Following : {d['following']:,}")
        print(f"  📷 Posts     : {d['posts']:,}")

        if d["biography"]:
            print(f"  📝 Bio: {d['biography'][:120]}")
        if d["external_url"]:
            print(f"  🔗 URL: {d['external_url']}")
