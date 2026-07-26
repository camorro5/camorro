#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proxy manager."""

import os
import time
import requests
from .banner import ok


class ProxyManager:
    def __init__(self, proxy_file=None, proxy_url=None):
        self._all = []
        self._alive = []
        self._dead = []
        self._idx = 0
        if proxy_url:
            u = proxy_url.strip()
            if u:
                if "://" not in u:
                    u = "http://" + u
                self._all.append(u)
        if proxy_file and os.path.isfile(proxy_file):
            with open(proxy_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "://" not in line:
                        line = "http://" + line
                    self._all.append(line)
        self._all = list(dict.fromkeys(self._all))

    @property
    def count(self):
        return len(self._all)

    @property
    def alive_count(self):
        return len(self._alive)

    def get_next(self):
        pool = self._alive if self._alive else [{"url": u} for u in self._all]
        if not pool:
            return None
        item = pool[self._idx % len(pool)]
        self._idx += 1
        return item["url"] if isinstance(item, dict) else item

    def get_proxies_dict(self, url=None):
        u = url or self.get_next()
        if not u:
            return None
        return {"http": u, "https": u}

    def mark_dead(self, url):
        if not url:
            return
        self._dead.append(url)
        self._alive = [p for p in self._alive if p.get("url") != url]
        if url in self._all:
            try:
                self._all.remove(url)
            except ValueError:
                pass

    def validate_all(self, timeout=8):
        self._alive = []
        self._dead = []
        for url in list(self._all):
            t0 = time.time()
            try:
                r = requests.get(
                    "https://www.instagram.com/",
                    proxies={"http": url, "https": url},
                    timeout=timeout,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Linux; Android 13) "
                            "Chrome/122.0.0.0 Mobile Safari/537.36"
                        )
                    },
                    allow_redirects=True,
                )
                if r.status_code < 500:
                    self._alive.append(
                        {"url": url, "latency": time.time() - t0}
                    )
                else:
                    self._dead.append(url)
            except Exception:
                self._dead.append(url)
        ok(f"Proxies: {len(self._alive)} alive / {len(self._all)} total")
        return len(self._alive)
