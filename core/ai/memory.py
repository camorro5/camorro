#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Memory — learns from failures, never repeats errors."""
import json
import os
import time

try:
    from ..banner import info, ok, warn, err, ai
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")


MEMORY_FILE = "output/ai_memory.json"


class Memory:
    def __init__(self):
        self.data = self._load()
        # Structure:
        # {
        #   "bad_proxies": {},       # {url: {fails: N, last: time}}
        #   "bad_patterns": {},      # {pattern: {hits: N, last: time}}
        #   "delays": [],            # [{timestamp, action, delay}]
        #   "errors": [],            # [{timestamp, error, context}]
        #   "success_rate": {},      # {action: {success, total}}
        #   "session_start": time,
        #   "total_attempts": 0,
        # }

    def _load(self):
        try:
            if os.path.isfile(MEMORY_FILE):
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "bad_proxies": {},
            "bad_patterns": {},
            "delays": [],
            "errors": [],
            "success_rate": {},
            "session_start": time.time(),
            "total_attempts": 0,
            "version": "camoro-v1",
        }

    def save(self):
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── Proxy ──

    def record_proxy(self, alive=False, url=""):
        if url:
            entry = self.data["bad_proxies"].get(url, {"fails": 0, "last": 0})
            if alive:
                entry["fails"] = 0
            else:
                entry["fails"] += 1
            entry["last"] = time.time()
            self.data["bad_proxies"][url] = entry

        # Track success rate
        sr = self.data["success_rate"].get("proxy", {"success": 0, "total": 0})
        sr["total"] += 1
        if alive:
            sr["success"] += 1
        self.data["success_rate"]["proxy"] = sr
        self.save()

    def is_bad_proxy(self, url, threshold=3):
        entry = self.data["bad_proxies"].get(url, {})
        return entry.get("fails", 0) >= threshold

    # ── Attempts ──

    def record_attempt(self, password="", result=None):
        self.data["total_attempts"] = self.data.get("total_attempts", 0) + 1

        status = (result or {}).get("status", "?")
        sr = self.data["success_rate"].get("attempt", {"success": 0, "total": 0})
        sr["total"] += 1
        if status == "ok":
            sr["success"] += 1
        self.data["success_rate"]["attempt"] = sr

        # Track bad patterns
        if status in ("rate_limited", "proxy_error", "timeout"):
            self.data["bad_patterns"].setdefault(status, {"hits": 0, "last": 0})
            self.data["bad_patterns"][status]["hits"] += 1
            self.data["bad_patterns"][status]["last"] = time.time()

        self.save()

    # ── Errors ──

    def record_error(self, error_msg, context=""):
        self.data["errors"].append({
            "timestamp": time.time(),
            "error": str(error_msg)[:200],
            "context": context,
        })
        if len(self.data["errors"]) > 200:
            self.data["errors"] = self.data["errors"][-100:]
        self.save()

    # ── Delays ──

    def record_delay(self, action, delay):
        self.data["delays"].append({
            "timestamp": time.time(),
            "action": action,
            "delay": delay,
        })
        if len(self.data["delays"]) > 100:
            self.data["delays"] = self.data["delays"][-50:]
        self.save()

    def average_delay(self, action="brute"):
        relevant = [d["delay"] for d in self.data["delays"] if d["action"] == action]
        if not relevant:
            return None
        return sum(relevant) / len(relevant)

    # ── Stats ──

    def stats(self):
        d = self.data
        sr_proxy = d["success_rate"].get("proxy", {})
        sr_attempt = d["success_rate"].get("attempt", {})

        proxy_rate = (f"{sr_proxy.get('success',0)}/{sr_proxy.get('total',1)} "
                      f"({100*sr_proxy.get('success',0)/max(sr_proxy.get('total',1),1):.0f}%)")

        attempt_rate = (f"{sr_attempt.get('success',0)}/{sr_attempt.get('total',1)} "
                        f"({100*sr_attempt.get('success',0)/max(sr_attempt.get('total',1),1):.0f}%)")

        uptime = time.time() - d.get("session_start", time.time())
        h, m = divmod(int(uptime), 3600)
        m, s = divmod(m, 60)

        return {
            "uptime": f"{h}h {m}m {s}s",
            "total_attempts": d.get("total_attempts", 0),
            "bad_proxies": len(d.get("bad_proxies", {})),
            "proxy_success_rate": proxy_rate,
            "attempt_success_rate": attempt_rate,
            "errors_logged": len(d.get("errors", [])),
            "bad_patterns": dict(d.get("bad_patterns", {})),
        }

    def show_stats(self):
        s = self.stats()
        from ..banner import C
        print(f"""
{C.C}+==================================================+
|              AI MEMORY — STATUS                |
+==================================================+
|  Uptime         : {s['uptime']}                   |
|  Total attempts : {s['total_attempts']}          |
|  Proxy rate     : {s['proxy_success_rate']}      |
|  Attempt rate   : {s['attempt_success_rate']}    |
|  Bad proxies    : {s['bad_proxies']} recorded    |
|  Errors logged  : {s['errors_logged']}           |
+==================================================+{C.E}
""")
