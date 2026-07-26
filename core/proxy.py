#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proxy manager — auto-fetch + auto-failover."""
import os, time, requests
from .banner import info, ok, warn, err
from .proxy_scraper import ProxyScraper

class ProxyManager:
    def __init__(self, proxy_file=None, proxy_url=None, auto_fetch=True, max_proxies=150, validate=True):
        self._all, self._alive, self._dead = [], [], set()
        self._idx = 0; self._auto_fetch = auto_fetch; self._max_proxies = max_proxies
        self._scraper = ProxyScraper(); self._last_fetch = 0.0; self._fetch_cooldown = 30
        self._consecutive_dead = 0

        if proxy_file and os.path.isfile(proxy_file):
            loaded = 0
            with open(proxy_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "://" not in line: line = "http://" + line
                    if line not in self._all: self._all.append(line); loaded += 1
            if loaded: info(f"Loaded {loaded} proxies from {proxy_file}")

        if proxy_url:
            u = proxy_url.strip()
            if u:
                if "://" not in u: u = "http://" + u
                if u not in self._all: self._all.insert(0, u)

        self._all = list(dict.fromkeys(self._all))
        if validate and self._all: self.validate_all(timeout=8)

    @property
    def count(self) -> int: return len(self._all)
    @property
    def alive_count(self) -> int: return len(self._alive)
    @property
    def dead_count(self) -> int: return len(self._dead)

    def get_next(self) -> str | None:
        if not self._alive:
            if self._auto_fetch and self._should_fetch():
                info("Proxy pool empty — auto-fetching from spys.one + mirrors...")
                fresh = self._scraper.fetch_and_validate(max_proxies=self._max_proxies, test_timeout=8)
                self._alive = fresh; self._idx = 0; self._last_fetch = time.time(); self._consecutive_dead = 0
                if fresh: ok(f"Auto-fetched {len(fresh)} alive proxies")
        if not self._alive and self._all: info("No alive — testing remaining raw proxies..."); self.validate_all(timeout=6)
        if not self._alive: return None
        item = self._alive[self._idx % len(self._alive)]; self._idx += 1
        return item["url"]

    def get_proxies_dict(self, url=None) -> dict | None:
        u = url or self.get_next()
        return {"http": u, "https": u} if u else None

    def mark_dead(self, url: str | None):
        if not url: return
        self._dead.add(url)
        self._alive = [p for p in self._alive if p.get("url") != url]
        if url in self._all: self._all.remove(url)
        self._consecutive_dead += 1
        if self._consecutive_dead >= 8 and self._should_fetch():
            warn(f"{self._consecutive_dead} dead in a row — fetching fresh proxies...")
            try:
                fresh = self._scraper.fetch_and_validate(max_proxies=self._max_proxies, test_timeout=8)
                existing = {p["url"] for p in self._alive}; added = 0
                for p in fresh:
                    if p["url"] not in existing and p["url"] not in self._dead:
                        self._alive.append(p); existing.add(p["url"]); added += 1
                if added: self._alive.sort(key=lambda x: x["latency"])
                ok(f"Merged +{added} fresh proxies (total alive: {len(self._alive)})")
                self._consecutive_dead = 0; self._last_fetch = time.time()
            except Exception as e: warn(f"Auto-fetch failed: {e}")

    def mark_alive(self, url: str):
        if not url: return
        self._consecutive_dead = max(0, self._consecutive_dead - 1)

    def validate_all(self, timeout=8):
        self._alive = []
        for url in list(self._all):
            try:
                t0 = time.time()
                r = requests.get("https://www.instagram.com/", proxies={"http": url, "https": url},
                    timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/125.0.0.0 Mobile Safari/537.36"},
                    allow_redirects=True)
                if r.status_code < 500: self._alive.append({"url": url, "latency": round(time.time() - t0, 3)})
            except Exception: self._dead.add(url)
        self._alive.sort(key=lambda x: x["latency"])
        ok(f"Proxies: {len(self._alive)} alive / {len(self._all)} total")

    def fetch_fresh(self, count=200):
        info("Fetching fresh proxies...")
        fresh = self._scraper.fetch_and_validate(max_proxies=count, test_timeout=8)
        existing = {p["url"] for p in self._alive}; added = 0
        for p in fresh:
            if p["url"] not in existing and p["url"] not in self._dead:
                self._alive.append(p); existing.add(p["url"]); added += 1
                if p["url"] not in self._all: self._all.append(p["url"])
        self._alive.sort(key=lambda x: x["latency"]); self._last_fetch = time.time(); self._consecutive_dead = 0
        ok(f"Added {added} new proxies (total alive: {len(self._alive)})")
        return added

    def stats(self) -> dict:
        return {"alive": len(self._alive), "dead": len(self._dead), "raw": len(self._all),
                "idx": self._idx, "consecutive_dead": self._consecutive_dead}

    def show_stats(self):
        s = self.stats()
        info(f"Proxy pool: {s['alive']} alive | {s['dead']} dead | {s['raw']} raw | streak: {s['consecutive_dead']} dead")

    def _should_fetch(self) -> bool:
        if not self._auto_fetch: return False
        if time.time() - self._last_fetch < self._fetch_cooldown: return False
        return True
