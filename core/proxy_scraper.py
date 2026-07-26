#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-fetch fresh proxies from spys.one + fallback sources."""

import re
import time
import random
import requests

try:
    from .banner import info, ok, warn, err
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m): print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m): print(f"[-] {m}")


class ProxyScraper:
    SOURCES = [
        {"name": "spys.one http", "url": "https://spys.one/en/http-proxy-list/", "type": "html"},
        {"name": "spys.one https", "url": "https://spys.one/en/https-ssl-proxy-list/", "type": "html"},
        {"name": "proxyscrape http", "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=8000&country=all&ssl=all&anonymity=all", "type": "text"},
        {"name": "proxyscrape https", "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=https&timeout=8000&country=all&ssl=all&anonymity=all", "type": "text"},
        {"name": "proxy-list.download http", "url": "https://www.proxy-list.download/api/v1/get?type=http", "type": "text"},
        {"name": "proxy-list.download https", "url": "https://www.proxy-list.download/api/v1/get?type=https", "type": "text"},
        {"name": "TheSpeedX http", "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt", "type": "text"},
        {"name": "monosans http", "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", "type": "text"},
        {"name": "monosans https", "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt", "type": "text"},
        {"name": "jetkai http", "url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt", "type": "text"},
        {"name": "jetkai https", "url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt", "type": "text"},
        {"name": "roosterkid http", "url": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP_RAW.txt", "type": "text"},
    ]

    IP_PORT = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})\b")

    def __init__(self, timeout=10, user_agent=None):
        self.timeout = timeout
        self.ua = user_agent or "Mozilla/5.0 (Linux; Android 14) Chrome/125.0.0.0 Mobile Safari/537.36"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.ua})

    def fetch_all(self, max_proxies=300) -> list:
        all_proxies: list = []
        seen: set = set()
        for src in self.SOURCES:
            try:
                name = src["name"]
                info(f"Fetching: {name}")
                time.sleep(random.uniform(0.3, 0.9))
                if src["type"] == "text":
                    proxies = self._fetch_text(src["url"])
                elif src["type"] == "html":
                    proxies = self._fetch_html(src["url"])
                else:
                    continue
                new = 0
                for p in proxies:
                    if p not in seen:
                        seen.add(p)
                        all_proxies.append(p)
                        new += 1
                ok(f"  {name}: +{new} (total {len(all_proxies)})")
                if len(all_proxies) >= max_proxies:
                    break
            except requests.exceptions.Timeout:
                warn(f"  {name}: timeout")
            except requests.exceptions.ConnectionError:
                warn(f"  {name}: connection error")
            except Exception as e:
                warn(f"  {name}: {e}")
        random.shuffle(all_proxies)
        ok(f"Total fresh proxies: {len(all_proxies)}")
        return all_proxies[:max_proxies]

    def _fetch_text(self, url: str) -> list:
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

    def _fetch_html(self, url: str) -> list:
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        html = r.text
        proxies = []
        for m in self.IP_PORT.finditer(html):
            proxies.append(f"http://{m.group(1)}:{m.group(2)}")
        for m in re.finditer(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[^<]*<[^>]*>[^<]*<[^>]*>[\s]*(\d{2,5})", html):
            proxies.append(f"http://{m.group(1)}:{m.group(2)}")
        return proxies

    def fetch_and_validate(self, max_proxies=200, test_url="https://www.instagram.com/", test_timeout=8) -> list:
        raw = self.fetch_all(max_proxies=max_proxies * 2)
        alive = []
        info(f"Validating {len(raw)} proxies...")
        for url in raw:
            try:
                t0 = time.time()
                r = self.session.get(test_url, proxies={"http": url, "https": url}, timeout=test_timeout, allow_redirects=True)
                if r.status_code < 500:
                    latency = time.time() - t0
                    alive.append({"url": url, "latency": round(latency, 3)})
                    if len(alive) % 10 == 0:
                        info(f"  alive: {len(alive)}...")
                if len(alive) >= max_proxies:
                    break
            except Exception:
                pass
        alive.sort(key=lambda x: x["latency"])
        ok(f"Alive proxies: {len(alive)}")
        return alive
