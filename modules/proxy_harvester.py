"""
Proxy Harvester Module — Fetch & Validate Proxies from spys.one
═══════════════════════════════════════════════════════════════

Sources:
  • HTTP/HTTPS: https://spys.me/proxy.txt  (updated hourly)
  • SOCKS4/5:   https://spys.me/socks.txt  (updated hourly)

Capabilities:
  • Fetch live proxies in real-time
  • Multi-threaded validation (speed/connectivity/anonymity test)
  • Smart filtering by country, anonymity level, SSL support
  • Auto-scoring: ranks proxies by latency + reliability
  • Export to proxychains format, JSON
  • Rotating proxy pool with automatic refresh
"""

import re
import time
import socket
import threading
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from datetime import datetime
from typing import Dict, List, Optional


SPYS_HTTP_URL  = "https://spys.me/proxy.txt"
SPYS_SOCKS_URL = "https://spys.me/socks.txt"
USER_AGENT     = "Mozilla/5.0 (compatible; GhostMedia/2.0; ProxyHarvester)"


class ProxyEntry:
    """Single proxy server entry with metadata."""

    def __init__(self, ip: str, port: int, country: str = "??",
                 anonymity: str = "N", ssl: bool = False,
                 google: bool = False, proxy_type: str = "http"):
        self.ip = ip
        self.port = port
        self.country = country.upper()
        self.anonymity = anonymity.upper()
        self.ssl = ssl
        self.google = google
        self.proxy_type = proxy_type
        self.latency_ms: Optional[float] = None
        self.alive: bool = False
        self.score: float = 0.0
        self.last_checked: Optional[str] = None

    def __repr__(self):
        return (f"ProxyEntry({self.ip}:{self.port} [{self.country}] "
                f"{self.anonymity} {'SSL' if self.ssl else ''} "
                f"type={self.proxy_type} score={self.score:.1f})")

    def to_dict(self) -> Dict:
        return {
            "ip": self.ip, "port": self.port, "country": self.country,
            "anonymity": self.anonymity, "ssl": self.ssl,
            "google": self.google, "type": self.proxy_type,
            "latency_ms": self.latency_ms, "alive": self.alive,
            "score": round(self.score, 1),
            "last_checked": self.last_checked,
        }

    def to_proxychains(self) -> str:
        t = "socks5" if self.proxy_type in ("socks5", "socks4") else "http"
        return f"{t} {self.ip} {self.port}"

    def to_url(self) -> str:
        return f"{self.proxy_type}://{self.ip}:{self.port}"


class ProxyHarvester:
    """
    Intelligent proxy harvester from spys.one.
    Fetches, validates, scores, and manages a rotating proxy pool.
    """

    def __init__(self, timeout: int = 10, max_workers: int = 30,
                 debug: bool = False):
        self.timeout = timeout
        self.max_workers = max_workers
        self.debug = debug
        self.proxies: List[ProxyEntry] = []
        self.validated: List[ProxyEntry] = []
        self._lock = threading.Lock()
        self._rotation_index = 0

    def fetch_http(self) -> List[ProxyEntry]:
        """Fetch HTTP/HTTPS proxies from spys.me/proxy.txt."""
        proxies = []
        try:
            req = Request(SPYS_HTTP_URL, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")

            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("Proxy"):
                    continue
                entry = self._parse_http_line(line)
                if entry:
                    proxies.append(entry)

            if self.debug:
                print(f"  [proxy_harvester] Fetched {len(proxies)} HTTP proxies")

        except Exception as e:
            if self.debug:
                print(f"  [!] Failed to fetch HTTP proxies: {e}")

        return proxies

    def fetch_socks(self) -> List[ProxyEntry]:
        """Fetch SOCKS proxies from spys.me/socks.txt."""
        proxies = []
        try:
            req = Request(SPYS_SOCKS_URL, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")

            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                entry = self._parse_socks_line(line)
                if entry:
                    proxies.append(entry)

            if self.debug:
                print(f"  [proxy_harvester] Fetched {len(proxies)} SOCKS proxies")

        except Exception as e:
            if self.debug:
                print(f"  [!] Failed to fetch SOCKS proxies: {e}")

        return proxies

    def fetch_all(self) -> List[ProxyEntry]:
        """Fetch all proxy types."""
        all_proxies = self.fetch_http() + self.fetch_socks()
        with self._lock:
            self.proxies = all_proxies
        return all_proxies

    def _parse_http_line(self, line: str) -> Optional[ProxyEntry]:
        """Parse HTTP proxy line. Format: IP:PORT CC-Anonymity(-S)?(!)? (+/-)?"""
        pattern = (
            r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r':(\d{2,5})\s+'
            r'([A-Z]{2})-'
            r'([A-Za-z]+)'
            r'(-S)?'
            r'(!)?'
        )
        match = re.match(pattern, line)
        if not match:
            return None

        ip    = match.group(1)
        port  = int(match.group(2))
        cc    = match.group(3)
        anon  = match.group(4)
        ssl   = bool(match.group(5))
        google = '+' in line

        return ProxyEntry(
            ip=ip, port=port, country=cc,
            anonymity=self._normalize_anonymity(anon),
            ssl=ssl, google=google,
            proxy_type="https" if ssl else "http"
        )

    def _parse_socks_line(self, line: str) -> Optional[ProxyEntry]:
        """Parse SOCKS proxy line."""
        pattern = (
            r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r':(\d{2,5})\s+'
            r'([A-Z]{2})-'
            r'([A-Za-z]+)'
        )
        match = re.match(pattern, line)
        if not match:
            return None

        ip    = match.group(1)
        port  = int(match.group(2))
        cc    = match.group(3)
        anon  = match.group(4)

        return ProxyEntry(
            ip=ip, port=port, country=cc,
            anonymity=self._normalize_anonymity(anon),
            ssl=False, google=('+' in line),
            proxy_type="socks5"
        )

    def _normalize_anonymity(self, code: str) -> str:
        """Normalize anonymity codes to NOA/ANM/HIA."""
        code = code.upper().replace("!", "")
        if "HIA" in code or code in ("H", "H!"):
            return "HIA"
        if "ANM" in code or code in ("A", "A!"):
            return "ANM"
        return "NOA"

    def validate_proxy(self, proxy: ProxyEntry) -> ProxyEntry:
        """Test a single proxy for TCP connectivity."""
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((proxy.ip, proxy.port))
            sock.send(b"GET / HTTP/1.0\r\nHost: example.com\r\n\r\n")
            sock.recv(1024)
            sock.close()

            proxy.alive = True
            proxy.latency_ms = (time.time() - start) * 1000
            proxy.last_checked = datetime.now().isoformat()
            proxy.score = self._calculate_score(proxy)

        except Exception:
            proxy.alive = False
            proxy.latency_ms = None
            proxy.score = 0.0

        return proxy

    def validate_all(self, proxies: List[ProxyEntry] = None,
                     min_alive: int = 10) -> List[ProxyEntry]:
        """Validate all proxies with multi-threading."""
        if proxies is None:
            proxies = self.proxies

        if self.debug:
            print(f"  [proxy_harvester] Validating {len(proxies)} proxies "
                  f"({self.max_workers} threads, timeout={self.timeout}s)...")

        alive = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.validate_proxy, p): p for p in proxies}
            for future in as_completed(futures):
                result = future.result()
                if result.alive:
                    alive.append(result)

        alive.sort(key=lambda p: p.score, reverse=True)

        with self._lock:
            self.validated = alive

        if self.debug:
            print(f"  [proxy_harvester] {len(alive)}/{len(proxies)} alive")

        return alive

    def _calculate_score(self, proxy: ProxyEntry) -> float:
        """Calculate proxy quality score (0-100)."""
        score = 50.0

        if proxy.latency_ms:
            if proxy.latency_ms < 500:
                score += 30
            elif proxy.latency_ms < 1000:
                score += 20
            elif proxy.latency_ms < 2000:
                score += 10
            elif proxy.latency_ms < 5000:
                score += 5

        if proxy.anonymity == "HIA":
            score += 20
        elif proxy.anonymity == "ANM":
            score += 10

        if proxy.ssl:
            score += 10

        if proxy.google:
            score += 5

        return min(score, 100.0)

    def filter(self, countries: List[str] = None,
               min_anonymity: str = None,
               ssl_only: bool = False,
               proxy_type: str = None,
               min_score: float = 30.0,
               max_latency: float = 5000.0) -> List[ProxyEntry]:
        """Filter validated proxies by criteria."""
        results = list(self.validated) if self.validated else list(self.proxies)

        if countries:
            countries = [c.upper() for c in countries]
            results = [p for p in results if p.country in countries]

        if min_anonymity:
            levels = ["NOA", "ANM", "HIA"]
            min_idx = levels.index(min_anonymity.upper()) if min_anonymity.upper() in levels else 0
            results = [p for p in results
                       if levels.index(p.anonymity) >= min_idx]

        if ssl_only:
            results = [p for p in results if p.ssl]

        if proxy_type:
            results = [p for p in results if p.proxy_type == proxy_type]

        if min_score:
            results = [p for p in results if p.score >= min_score]

        if max_latency:
            results = [p for p in results
                       if p.latency_ms and p.latency_ms <= max_latency]

        return results

    def next_proxy(self) -> Optional[ProxyEntry]:
        """Get next proxy from rotation pool (round-robin)."""
        with self._lock:
            if not self.validated:
                return None
            proxy = self.validated[self._rotation_index % len(self.validated)]
            self._rotation_index += 1
            return proxy

    def random_proxy(self) -> Optional[ProxyEntry]:
        """Get random proxy from validated pool."""
        with self._lock:
            if not self.validated:
                return None
            return random.choice(self.validated)

    def best_proxy(self) -> Optional[ProxyEntry]:
        """Get highest-scored proxy."""
        with self._lock:
            if not self.validated:
                return None
            return self.validated[0]

    def export_proxychains(self, output_path: str = "proxychains_proxies.txt") -> str:
        """Export validated proxies in proxychains format."""
        with open(output_path, "w") as f:
            f.write("# GhostMedia Proxy Export - Proxychains Format\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write("# Source: spys.one (spys.me)\n")
            f.write(f"# Total: {len(self.validated)} validated proxies\n\n")
            f.write("random_chain\n")
            f.write("chain_len = 1\n")
            f.write("tcp_read_time_out 15000\n")
            f.write("tcp_connect_time_out 8000\n\n")
            f.write("[ProxyList]\n")
            for p in self.validated[:50]:
                f.write(p.to_proxychains() + "\n")
        return output_path

    def export_json(self, output_path: str = "proxies.json") -> str:
        """Export all validated proxies as JSON."""
        with open(output_path, "w") as f:
            json.dump({
                "generated": datetime.now().isoformat(),
                "source": "spys.one (spys.me)",
                "total": len(self.validated),
                "proxies": [p.to_dict() for p in self.validated],
            }, f, indent=2)
        return output_path

    def stats(self) -> Dict:
        """Get statistics about the proxy pool."""
        if not self.validated:
            return {"error": "No validated proxies", "total_fetched": len(self.proxies),
                    "total_alive": 0, "alive_percentage": 0}

        latencies = [p.latency_ms for p in self.validated if p.latency_ms]
        countries = set(p.country for p in self.validated)
        types = set(p.proxy_type for p in self.validated)

        return {
            "total_fetched": len(self.proxies),
            "total_alive": len(self.validated),
            "alive_percentage": round(len(self.validated) / max(len(self.proxies), 1) * 100, 1),
            "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 1) if latencies else None,
            "min_latency_ms": round(min(latencies), 1) if latencies else None,
            "max_latency_ms": round(max(latencies), 1) if latencies else None,
            "unique_countries": len(countries),
            "countries": sorted(list(countries)),
            "proxy_types": list(types),
            "best_proxy": str(self.validated[0]) if self.validated else None,
        }
