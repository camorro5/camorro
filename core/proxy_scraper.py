#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAMORO Proxy Scraper — Geonode Free API + AI scoring.
Primary: Geonode API (SOCKS5, elite, Google-pass, fast).
Each proxy gets AI quality score 0-100.
"""
import json
import os
import re
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from .banner import info, ok, warn, err, ai
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")


class ProxyScraper:
    """Geonode free API — best SOCKS5 proxies. AI scoring built-in."""

    GEONODE_API = "https://proxylist.geonode.com/api/proxy-list"

    GEONODE_HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "origin": "https://geonode.com",
        "pragma": "no-cache",
        "referer": "https://geonode.com/free-proxy-list",
        "sec-ch-ua": '"Chromium";v="128", "Google Chrome";v="128"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }

    BACKUP = [
        {"name": "proxyscrape", "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=elite"},
        {"name": "monosans", "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt"},
        {"name": "TheSpeedX", "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"},
    ]

    IP_PORT = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})\b")

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/126.0.0.0 Mobile Safari/537.36"
        })

    # ═══════════════════════════════════════════════
    # AI SCORING
    # ═══════════════════════════════════════════════

    def ai_score(self, proxy):
        """Score 0-100: protocols + latency + speed + google + uptime + anonymity"""
        score = 0

        protocols = proxy.get("protocols") or proxy.get("protocol", [])
        if isinstance(protocols, str):
            protocols = [protocols]
        protocols = [str(p).lower() for p in protocols]

        if "socks5" in protocols:
            score += 30
        elif "socks4" in protocols:
            score += 25
        if any(p in protocols for p in ("http", "https")):
            score += 15

        latency = proxy.get("responseTime") or proxy.get("latency") or 999
        try:
            latency = float(latency)
        except (ValueError, TypeError):
            latency = 999

        if latency < 200:
            score += 25
        elif latency < 500:
            score += 15
        elif latency < 1000:
            score += 5
        elif latency < 2000:
            score += 2

        speed = str(proxy.get("speed", "")).lower()
        if speed == "fast":
            score += 20
        elif speed == "medium":
            score += 10

        google = str(proxy.get("google", "")).lower()
        if google in ("true", "yes", "1"):
            score += 15

        anonymity = str(proxy.get("anonymityLevel") or proxy.get("anonymity", "")).lower()
        if anonymity == "elite":
            score += 10
        elif anonymity == "anonymous":
            score += 5

        last = proxy.get("lastChecked") or 99
        try:
            last = int(last)
        except (ValueError, TypeError):
            last = 99
        if last <= 5:
            score += 10
        elif last <= 10:
            score += 5

        uptime = proxy.get("upTime") or 0
        try:
            uptime = float(uptime)
        except (ValueError, TypeError):
            uptime = 0
        if uptime >= 90:
            score += 20
        elif uptime >= 70:
            score += 10
        elif uptime >= 50:
            score += 3

        return min(score, 100)

    def ai_label(self, score):
        if score >= 80:
            return "ELITE"
        elif score >= 60:
            return "GOOD"
        elif score >= 40:
            return "AVERAGE"
        elif score >= 20:
            return "WEAK"
        else:
            return "DEAD"

    # ═══════════════════════════════════════════════
    # GEONODE API
    # ═══════════════════════════════════════════════

    def fetch_geonode(self, max_pages=3, country=""):
        """Fetch high-quality SOCKS5 proxies from Geonode API."""
        ai("Fetching from Geonode API (SOCKS5 elite + AI scoring)...")

        all_proxies = []
        seen = set()

        for page in range(1, max_pages + 1):
            params = {
                "limit": "100",
                "page": str(page),
                "sort_by": "lastChecked",
                "sort_type": "desc",
                "filterByGoogle": "true",
                "filterBySpeed": "fast",
                "filterByUpTime": "80",
                "filterByLastChecked": "10",
                "anonymityLevel": "elite",
                "protocols": "socks5,socks4,http,https",
            }
            if country:
                params["filterByCountry"] = country.upper()

            try:
                r = self.session.get(
                    self.GEONODE_API,
                    headers=self.GEONODE_HEADERS,
                    params=params,
                    timeout=15
                )
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("data", [])
                    added = 0
                    for p in items:
                        ip = p.get("ip", "")
                        port = p.get("port", "")
                        key = f"{ip}:{port}"
                        if key in seen:
                            continue
                        seen.add(key)

                        protocols = p.get("protocols", [])
                        if isinstance(protocols, str):
                            protocols = [protocols]
                        protocols = [str(x).lower() for x in protocols]

                        if "socks5" in protocols:
                            url = f"socks5://{ip}:{port}"
                        elif "socks4" in protocols:
                            url = f"socks4://{ip}:{port}"
                        elif "https" in protocols:
                            url = f"https://{ip}:{port}"
                        else:
                            url = f"http://{ip}:{port}"

                        entry = {
                            "url": url,
                            "ip": ip,
                            "port": port,
                            "protocols": protocols,
                            "country": p.get("country", "??"),
                            "latency": p.get("responseTime") or p.get("latency", 999),
                            "speed": p.get("speed", "?"),
                            "uptime": p.get("upTime", 0),
                            "google": str(p.get("google", "")).lower() == "true",
                            "anonymity": p.get("anonymityLevel", "?"),
                            "last_checked": p.get("lastChecked", 99),
                            "score": 0,
                            "label": "",
                            "fails": 0,
                            "successes": 0,
                            "source": "geonode",
                        }
                        entry["score"] = self.ai_score(entry)
                        entry["label"] = self.ai_label(entry["score"])

                        if entry["score"] >= 30:
                            all_proxies.append(entry)
                            added += 1

                    info(f"  Page {page}: +{added} (total {len(all_proxies)})")

                    if len(all_proxies) >= 120:
                        break

                elif r.status_code == 429:
                    warn(f"  Geonode rate-limit page {page} — waiting...")
                    time.sleep(5)
                else:
                    warn(f"  Geonode HTTP {r.status_code} page {page}")

            except requests.exceptions.Timeout:
                warn(f"  Geonode timeout page {page}")
            except Exception as e:
                warn(f"  Geonode error page {page}: {e}")

            if page < max_pages:
                time.sleep(random.uniform(1, 2))

        all_proxies.sort(key=lambda x: x["score"], reverse=True)
        ok(f"Geonode: {len(all_proxies)} proxies AI-scored")

        if all_proxies:
            best = all_proxies[0]
            ai(f"  Best: {best['url']} | score={best['score']} | {best['label']} | "
               f"{best.get('country','?')} | {best.get('latency','?')}ms")

        return all_proxies

    # ═══════════════════════════════════════════════
    # BACKUP SOURCES
    # ═══════════════════════════════════════════════

    def _fetch_text(self, url):
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        proxies = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            m = self.IP_PORT.search(line)
            if m:
                proxies.append(f"http://{m.group(1)}:{m.group(2)}")
            elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$", line):
                proxies.append(f"http://{line}")
        return proxies

    def fetch_backup(self, max_count=30):
        """Fallback: backup sources if Geonode fails."""
        ai("Geonode unavailable — using backup sources...")
        all_proxies, seen = [], set()

        for src in self.BACKUP:
            try:
                raw = self._fetch_text(src["url"])
                new = 0
                for url in raw:
                    if url not in seen and len(all_proxies) < max_count:
                        seen.add(url)
                        ip = url.split("://")[1].split(":")[0]
                        port = url.split(":")[-1]
                        all_proxies.append({
                            "url": url, "ip": ip, "port": port,
                            "protocols": ["http"], "country": "??",
                            "latency": 999, "speed": "?", "uptime": 0,
                            "google": False, "anonymity": "elite",
                            "last_checked": 99, "score": 30, "label": "AVERAGE",
                            "fails": 0, "successes": 0, "source": src["name"],
                        })
                        new += 1
                if new:
                    info(f"  {src['name']}: +{new}")
            except Exception as e:
                warn(f"  {src['name']}: {e}")

        all_proxies.sort(key=lambda x: x["score"], reverse=True)
        ok(f"Backup: {len(all_proxies)} proxies")
        return all_proxies

    # ═══════════════════════════════════════════════
    # MAIN FETCH
    # ═══════════════════════════════════════════════

    def fetch_best(self, count=10, country=""):
        """Fetch top 'count' proxies. Geonode first, backup if needed."""
        proxies = self.fetch_geonode(max_pages=3, country=country)

        if not proxies:
            warn("Geonode returned 0 — trying backup...")
            proxies = self.fetch_backup(max_count=count * 2)

        if not proxies:
            err("No proxies available!")
            return []

        best = proxies[:count]

        elite = sum(1 for p in best if p["score"] >= 80)
        good = sum(1 for p in best if 60 <= p["score"] < 80)
        avg  = sum(1 for p in best if 40 <= p["score"] < 60)
        ai(f"AI Pool: {elite} elite | {good} good | {avg} average")

        for i, p in enumerate(best, 1):
            proto = ",".join(p.get("protocols", ["?"])[:2]).upper()
            stars = "⭐⭐⭐" if p["score"] >= 80 else "⭐⭐" if p["score"] >= 60 else "⭐"
            info(f"  #{i}: {stars} {p['url']} | score={p['score']} | "
                 f"{proto} | {p.get('country','?')} | {p.get('latency','?')}ms")

        return best

    def fetch_one_quick(self, blacklist=None, country=""):
        """Emergency: fetch ONE good proxy immediately."""
        blacklist = blacklist or set()

        try:
            params = {
                "limit": "50", "page": "1",
                "sort_by": "lastChecked", "sort_type": "desc",
                "filterByGoogle": "true", "filterBySpeed": "fast",
                "filterByUpTime": "80", "filterByLastChecked": "10",
                "anonymityLevel": "elite",
                "protocols": "socks5,socks4,http,https",
            }
            if country:
                params["filterByCountry"] = country.upper()

            r = self.session.get(
                self.GEONODE_API,
                headers=self.GEONODE_HEADERS,
                params=params,
                timeout=10
            )

            if r.status_code == 200:
                items = r.json().get("data", [])
                for p in items:
                    ip = p.get("ip", "")
                    port = p.get("port", "")
                    key = f"{ip}:{port}"
                    if key in blacklist:
                        continue

                    protocols = p.get("protocols", [])
                    if isinstance(protocols, str):
                        protocols = [protocols]

                    if "socks5" in protocols:
                        url = f"socks5://{ip}:{port}"
                    elif "socks4" in protocols:
                        url = f"socks4://{ip}:{port}"
                    else:
                        url = f"http://{ip}:{port}"

                    entry = {
                        "url": url, "ip": ip, "port": port,
                        "protocols": protocols,
                        "country": p.get("country", "??"),
                        "latency": p.get("responseTime", 999),
                        "speed": p.get("speed", "?"),
                        "uptime": p.get("upTime", 0),
                        "google": str(p.get("google", "")).lower() == "true",
                        "anonymity": p.get("anonymityLevel", "?"),
                        "last_checked": p.get("lastChecked", 99),
                        "fails": 0, "successes": 0, "source": "geonode-quick",
                    }
                    entry["score"] = self.ai_score(entry)
                    entry["label"] = self.ai_label(entry["score"])

                    if entry["score"] >= 40:
                        ai(f"Quick-fetch: {entry['url']} | score={entry['score']}")
                        return entry
        except Exception:
            pass

        return None
