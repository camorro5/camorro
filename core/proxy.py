#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAMORO Proxy Manager — elite 10-proxy pool.
Geonode SOCKS5 + AI scoring. Auto-heals on death.
"""
import os
import time
import json
import requests
from threading import Lock

try:
    from .banner import info, ok, warn, err, ai, C
    from .proxy_scraper import ProxyScraper
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")
    class C: R=G=Y=C=M=W=E=""
    from proxy_scraper import ProxyScraper


POOL_SIZE = 10
BLACKLIST_FILE = "output/proxy_blacklist.json"


class ProxyManager:
    def __init__(self, proxy_file=None, auto_fetch=True, pool_size=POOL_SIZE,
                 country="", ai_brain=None):
        self.pool_size = pool_size
        self._lock = Lock()
        self._scraper = ProxyScraper()
        self._idx = 0
        self._auto_fetch = auto_fetch
        self._country = country
        self._blacklist = self._load_blacklist()
        self._pool = []
        self._dead = []
        self._last_fetch = 0.0
        self._fetch_cooldown = 15
        self._consecutive_fails = 0
        self._total_requests = 0
        self._total_fails = 0
        self.ai_brain = ai_brain

        # Load from file
        loaded = 0
        if proxy_file and os.path.isfile(proxy_file):
            with open(proxy_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "://" not in line:
                        line = "http://" + line
                    if line not in self._blacklist:
                        ip = line.split("://")[1].split(":")[0]
                        port = line.split(":")[-1]
                        self._pool.append({
                            "url": line, "ip": ip, "port": port,
                            "protocols": ["http"], "country": "??",
                            "latency": 999, "speed": "?", "uptime": 0,
                            "google": False, "anonymity": "?",
                            "last_checked": 99, "score": 30, "label": "AVERAGE",
                            "fails": 0, "successes": 0, "source": "file",
                        })
                        loaded += 1
            if loaded:
                info(f"Loaded {loaded} proxies from file")

        # Auto-fill pool
        if self._auto_fetch and len(self._pool) < self.pool_size:
            self._fill_pool()

        # Validate existing
        if self._pool:
            self._validate_pool()

    # ── BLACKLIST ──

    def _load_blacklist(self):
        try:
            if os.path.isfile(BLACKLIST_FILE):
                with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def _save_blacklist(self):
        try:
            os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)
            with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self._blacklist), f, indent=2)
        except Exception:
            pass

    # ── POOL MANAGEMENT ──

    def _fill_pool(self):
        if not self._auto_fetch:
            return
        if time.time() - self._last_fetch < self._fetch_cooldown:
            return

        needed = self.pool_size - len(self._pool)
        if needed <= 0:
            return

        ai(f"Pool: {len(self._pool)}/{self.pool_size} — fetching {needed}...")
        fresh = self._scraper.fetch_best(count=needed + 3, country=self._country)

        added = 0
        for p in fresh:
            if p["url"] not in self._blacklist:
                self._pool.append(p)
                added += 1
                if len(self._pool) >= self.pool_size:
                    break

        self._last_fetch = time.time()
        if added:
            ok(f"Pool: +{added} → {len(self._pool)}/{self.pool_size} ready")
        else:
            warn(f"Pool: no new quality proxies (still {len(self._pool)}/{self.pool_size})")

    def _validate_pool(self):
        info(f"Validating pool ({len(self._pool)} proxies)...")
        alive = []
        for entry in self._pool:
            try:
                r = requests.get(
                    "https://www.instagram.com/",
                    proxies={"http": entry["url"], "https": entry["url"]},
                    timeout=8,
                    headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/126.0.0.0 Mobile Safari/537.36"},
                    allow_redirects=True,
                )
                if r.status_code < 500:
                    alive.append(entry)
                    continue
            except Exception:
                pass
            self._blacklist.add(entry["url"])
            self._dead.append(entry)

        removed = len(self._pool) - len(alive)
        self._pool = alive
        self._pool.sort(key=lambda x: x.get("score", 0), reverse=True)

        if removed:
            warn(f"  {removed} dead removed — pool: {len(self._pool)}/{self.pool_size}")
        if len(self._pool) < self.pool_size:
            self._fill_pool()

    # ── GET PROXY ──

    def get_next(self):
        """Get next proxy URL. Skips proxies with ≥2 fails."""
        with self._lock:
            if not self._pool:
                if self._auto_fetch:
                    ai("Pool empty — emergency fetch...")
                    self._fill_pool()
                if not self._pool:
                    return None

            for _ in range(len(self._pool)):
                entry = self._pool[self._idx % len(self._pool)]
                self._idx += 1
                if entry["fails"] < 2:
                    return entry["url"]

            for e in self._pool:
                e["fails"] = max(0, e["fails"] - 1)

            entry = self._pool[self._idx % len(self._pool)]
            self._idx += 1
            return entry["url"]

    def get_proxies_dict(self):
        u = self.get_next()
        return {"http": u, "https": u} if u else None

    # ── FEEDBACK ──

    def mark_dead(self, url):
        """Proxy dead → kill it, replace immediately."""
        if not url:
            return

        with self._lock:
            self._total_requests += 1
            self._total_fails += 1
            self._consecutive_fails += 1

            for entry in list(self._pool):
                if entry["url"] == url:
                    entry["fails"] += 1
                    if entry["fails"] >= 2:
                        ai(f"KILLED: {url} (score was {entry.get('score','?')})")
                        self._pool.remove(entry)
                        self._dead.append(entry)
                        self._blacklist.add(url)
                        self._save_blacklist()
                    else:
                        warn(f"Degraded: {url} ({entry['fails']}/2 fails)")
                    break

            if len(self._pool) < self.pool_size and self._auto_fetch:
                if time.time() - self._last_fetch > self._fetch_cooldown:
                    self._fill_pool()
                else:
                    ai("Emergency quick-fetch...")
                    quick = self._scraper.fetch_one_quick(
                        blacklist=self._blacklist, country=self._country
                    )
                    if quick:
                        self._pool.append(quick)
                        ok(f"Quick-replaced: +1 → {len(self._pool)}/{self.pool_size}")

            if self.ai_brain:
                self.ai_brain.memory.record_proxy(alive=False)

    def mark_alive(self, url):
        """Proxy worked → reset its fail counter."""
        if not url:
            return

        with self._lock:
            self._total_requests += 1
            self._consecutive_fails = 0

            for entry in self._pool:
                if entry["url"] == url:
                    entry["fails"] = 0
                    entry["successes"] += 1
                    break

            if self.ai_brain:
                self.ai_brain.memory.record_proxy(alive=True)

    # ── MANUAL ──

    def refresh_all(self):
        """Force-refresh entire pool."""
        ai("Force-refreshing pool...")
        for e in list(self._pool):
            self._blacklist.add(e["url"])
        self._pool.clear()
        self._dead.clear()
        self._save_blacklist()
        self._fill_pool()
        ok(f"Pool refreshed: {len(self._pool)}/{self.pool_size}")

    def kill_proxy(self, url):
        """Manually kill a proxy."""
        for entry in list(self._pool):
            if entry["url"] == url:
                self._pool.remove(entry)
                self._dead.append(entry)
                self._blacklist.add(url)
                self._save_blacklist()
                ok(f"Killed: {url}")
                self._fill_pool()
                return True
        warn(f"Not in pool: {url}")
        return False

    # ── STATS ──

    @property
    def count(self):
        return len(self._pool)

    @property
    def alive_count(self):
        return len([e for e in self._pool if e["fails"] == 0])

    def stats(self):
        with self._lock:
            pinfo = []
            for e in sorted(self._pool, key=lambda x: x.get("score", 0), reverse=True):
                st = f"{C.G}*{C.E}" if e["fails"] == 0 else f"{C.Y}o{C.E}"
                pinfo.append({
                    "url": e["url"],
                    "score": e.get("score", 0),
                    "label": e.get("label", "?"),
                    "fails": e["fails"],
                    "successes": e.get("successes", 0),
                    "country": e.get("country", "?"),
                    "status": st,
                })
            sr = f"{(1 - self._total_fails / max(self._total_requests, 1)) * 100:.1f}%"
            return {
                "pool_size": self.pool_size,
                "alive": self.alive_count,
                "total": len(self._pool),
                "dead": len(self._dead),
                "blacklisted": len(self._blacklist),
                "requests": self._total_requests,
                "fails": self._total_fails,
                "success_rate": sr,
                "streak": self._consecutive_fails,
                "pool": pinfo,
            }

    def show_stats(self):
        s = self.stats()
        print(f"""
{C.C}+==================================================+
|           PROXY POOL — AI MONITORED            |
+==================================================+
|  Pool   : {s['alive']} alive / {s['total']} total / {s['pool_size']} max         |
|  Dead   : {s['dead']} session / {s['blacklisted']} blacklisted           |
|  Reqs   : {s['requests']} ({s['success_rate']} success)                  |
|  Streak : {s['streak']} fails in a row                        |
+--------------------------------------------------+
|  Active Pool (AI-scored):                        |{C.E}""")
        for i, p in enumerate(s["pool"], 1):
            us = p["url"].replace("http://", "").replace("socks5://", "").replace("socks4://", "")
            if len(us) > 28:
                us = us[:25] + "..."
            sc = p.get("score", 0)
            stars = "***" if sc >= 80 else "**" if sc >= 60 else "*"
            print(f"  {p['status']} #{i}: {us:<28} {stars} score={sc} | {p['country']}")
        print(f"{C.C}+==================================================+{C.E}")
