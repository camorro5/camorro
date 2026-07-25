#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proxy management with validation and rotation."""

import random
import time
import requests


class ProxyManager:
    """Loads, validates, and rotates HTTP/SOCKS proxies."""

    def __init__(self, proxy_file=None, proxy_url=None):
        self._proxies = []
        self._alive = []
        self._dead = []
        self._cursor = 0

        if proxy_url:
            self._proxies.append(self._normalize(proxy_url))
        if proxy_file:
            self._load_file(proxy_file)

    def _normalize(self, url):
        url = url.strip()
        if "://" not in url:
            url = f"http://{url}"
        return url

    def _load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._proxies.append(self._normalize(line))
        except Exception:
            pass

    @property
    def count(self):
        return len(self._proxies)

    @property
    def alive_count(self):
        return len(self._alive)

    def validate_all(self, test_url="https://www.instagram.com", timeout=8):
        """Test all proxies, categorize as alive/dead."""
        self._alive.clear()
        self._dead.clear()

        for p in self._proxies:
            proxies = {"http": p, "https": p}
            try:
                start = time.time()
                r = requests.get(test_url, proxies=proxies, timeout=timeout)
                latency = time.time() - start
                if r.status_code < 500:
                    self._alive.append({"url": p, "latency": latency})
                else:
                    self._dead.append(p)
            except Exception:
                self._dead.append(p)

        return len(self._alive)

    def get_next(self):
        """Returns next proxy in rotation."""
        if not self._alive:
            if not self._proxies:
                return None
            self._alive = [{"url": p, "latency": 999} for p in self._proxies]

        self._cursor = (self._cursor + 1) % len(self._alive)
        return self._alive[self._cursor]["url"]

    def get_random(self):
        """Returns a random alive proxy."""
        if not self._alive:
            if not self._proxies:
                return None
            return random.choice(self._proxies)
        return random.choice(self._alive)["url"]

    def mark_dead(self, url):
        """Remove a dead proxy from rotation."""
        self._alive = [p for p in self._alive if p["url"] != url]
        if url in self._proxies:
            self._proxies.remove(url)

    def get_proxies_dict(self, url):
        """Returns proxy dict for requests library."""
        return {"http": url, "https": url} if url else {}
