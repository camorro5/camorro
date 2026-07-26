#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Brain — decision engine."""
import time
import random

try:
    from ..banner import info, ok, warn, err, ai
    from .memory import Memory
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")
    from memory import Memory


class Brain:
    def __init__(self, memory=None):
        self.memory = memory or Memory()
        self.state = "idle"
        self.last_decision = None
        self.decision_count = 0

    def think(self, context):
        """
        context = {
            "consecutive_fails": int,
            "session_fails": int,
            "last_status": str,
            "proxy_alive": bool,
            "proxy_score": int,
            "current_delay": float,
            "total_tested": int,
            "total_remaining": int,
            "rate_limited": bool,
        }
        Returns dict with actions.
        """
        self.decision_count += 1

        cf = context.get("consecutive_fails", 0)
        sf = context.get("session_fails", 0)
        ls = context.get("last_status", "")
        p_alive = context.get("proxy_alive", True)
        delay = context.get("current_delay", 3.0)
        rl = context.get("rate_limited", False)

        decision = {
            "action": "continue",
            "reason": "",
            "new_delay": delay,
            "rotate_proxy": False,
            "rotate_fingerprint": False,
            "force_rest": 0,
            "confidence": 1.0,
        }

        # ═══════════════════════════
        # RATE LIMIT
        # ═══════════════════════════
        if rl or ls == "rate_limited":
            decision["action"] = "rest"
            decision["reason"] = "Rate limit detected"
            decision["new_delay"] = random.uniform(45, 90)
            decision["rotate_proxy"] = True
            decision["rotate_fingerprint"] = True
            decision["force_rest"] = random.uniform(30, 60)
            self.state = "cooling"
            ai(f"Brain: rate-limited → cooling {decision['force_rest']:.0f}s")
            return decision

        # ═══════════════════════════
        # CONSECUTIVE FAILS
        # ═══════════════════════════
        if cf >= 5:
            decision["action"] = "rest"
            decision["reason"] = f"{cf} consecutive fails"
            decision["new_delay"] = random.uniform(20, 45)
            decision["rotate_proxy"] = True
            decision["force_rest"] = random.uniform(15, 30)
            self.state = "cooling"
            ai(f"Brain: {cf} fails → rest {decision['force_rest']:.0f}s")
            return decision

        if cf >= 3:
            decision["reason"] = f"{cf} consecutive fails — rotate proxy"
            decision["rotate_proxy"] = True
            decision["new_delay"] = min(delay * 1.5, 15)
            ai(f"Brain: {cf} fails → rotate proxy, delay={decision['new_delay']:.1f}s")
            return decision

        # ═══════════════════════════
        # PROXY DEAD
        # ═══════════════════════════
        if not p_alive:
            decision["reason"] = "Proxy dead"
            decision["rotate_proxy"] = True
            decision["new_delay"] = max(delay, random.uniform(2, 4))
            self.state = "recovering"
            return decision

        # ═══════════════════════════
        # HIGH FAIL RATE
        # ═══════════════════════════
        tested = context.get("total_tested", 1)
        if tested > 10 and sf / tested > 0.3:
            decision["reason"] = "High fail rate — rotate proxy+fp"
            decision["rotate_proxy"] = True
            decision["rotate_fingerprint"] = True
            decision["new_delay"] = random.uniform(8, 15)
            ai(f"Brain: {sf}/{tested} fails → rotate proxy+fp")
            return decision

        # ═══════════════════════════
        # NORMAL
        # ═══════════════════════════
        if self.state == "cooling":
            self.state = "active"

        # Adaptive delay
        if self.memory:
            avg = self.memory.average_delay("brute")
            if avg and avg > 10:
                decision["new_delay"] = max(avg * 0.9, delay)

        decision["reason"] = "Normal — continue"
        self.state = "active"
        return decision

    def get_state(self):
        return {
            "state": self.state,
            "decisions": self.decision_count,
            "last": self.last_decision,
        }
