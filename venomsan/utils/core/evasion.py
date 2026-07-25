"""Evasion Engine - WAF bypass, encoding, proxy rotation, TLS spoofing."""
import asyncio, random, time, base64, codecs
from typing import Optional
from urllib.parse import quote, quote_plus
from ..utils.helpers import status

# ═══════════════════════════════════════════════
# User Agents pool
# ═══════════════════════════════════════════════
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/120.0.6099.144 Mobile Safari/537.36",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "it-IT,it;q=0.9,en;q=0.8",
    "en-GB,en;q=0.9,en-US;q=0.8",
]

class PayloadEncoder:
    """Multi-layer payload encoder to bypass WAF."""

    @staticmethod
    def encode(payload: str, layers: int = 3) -> tuple:
        """Apply multiple encoding layers."""
        methods = [PayloadEncoder._b64, PayloadEncoder._hex, PayloadEncoder._url,
                    PayloadEncoder._double_url, PayloadEncoder._unicode, PayloadEncoder._rot13]
        current = payload
        applied = []
        for _ in range(min(layers, len(methods))):
            m = random.choice(methods)
            try:
                current = m(current)
                applied.append(m.__name__.replace("_", ""))
            except: pass
        return current, applied

    @staticmethod
    def _b64(p): return base64.b64encode(p.encode()).decode()
    @staticmethod
    def _hex(p): return p.encode().hex()
    @staticmethod
    def _url(p): return quote(p)
    @staticmethod
    def _double_url(p): return quote(quote(p))
    @staticmethod
    def _unicode(p): return ''.join(f'\\u{ord(c):04x}' for c in p)
    @staticmethod
    def _rot13(p): return codecs.encode(p, 'rot_13')

    @staticmethod
    def sql_obfuscate(query: str) -> str:
        """Obfuscate SQL query."""
        obf = {"SELECT":"SeLeCt","UNION":"UnIoN","FROM":"FrOm","WHERE":"WhErE","AND":"AnD","OR":"oR","SLEEP":"SLeEp"}
        for k, v in obf.items():
            query = query.replace(k, v).replace(k.lower(), v)
        return query

class AdaptiveRateLimiter:
    """Rate limiter that mimics human behavior."""

    def __init__(self, min_delay=0.05, max_delay=0.5, adaptive=True):
        self.min = min_delay
        self.max = max_delay
        self.adaptive = adaptive
        self._times = []
        self._errors = 0

    async def wait(self):
        if self.adaptive and len(self._times) > 20:
            self._adjust()
        delay = random.uniform(self.min, self.max)
        delay += random.gauss(0, delay * 0.1)
        await asyncio.sleep(max(0.01, delay))
        self._times.append(time.monotonic())

    def _adjust(self):
        self._times = self._times[-20:]
        if len(self._times) >= 2:
            span = self._times[-1] - self._times[0]
            rate = len(self._times) / max(span, 0.001)
            if rate > 10: self.max *= 1.1
            elif rate < 2 and self.max > self.min * 2: self.max *= 0.95

    def report_error(self, code: int):
        self._errors += 1
        if code in [429, 503]: self.max *= 2.0

class EvasionContext:
    """Full evasion context for requests."""

    def __init__(self):
        self.limiter = AdaptiveRateLimiter()
        self._ua_idx = 0
        self.encoder = PayloadEncoder()

    def random_headers(self, extra=None) -> dict:
        ua = USER_AGENTS[self._ua_idx % len(USER_AGENTS)]
        self._ua_idx += 1
        h = {
            "User-Agent": ua,
            "Accept": random.choice(ACCEPT_HEADERS),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": random.choice(["no-cache","max-age=0"]),
            "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        }
        if extra: h.update(extra)
        return h

    async def pre_request(self) -> dict:
        await self.limiter.wait()
        return self.random_headers()

    def encode_payload(self, payload: str, layers: int = 2) -> tuple:
        return self.encoder.encode(payload, layers)
