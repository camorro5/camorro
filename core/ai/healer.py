#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Healer — auto-fixes errors, replaces dead proxies, adjusts delays."""
import time
import random

try:
    from ..banner import info, ok, warn, err, ai
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")


class Healer:
    def __init__(self, brain=None, memory=None):
        self.brain = brain
        self.memory = memory
        self.heals_performed = 0
        self.last_heal_time = 0
        self.heal_cooldown = 5

    def heal(self, brute_instance):
        """
        Auto-fix based on current state.
        - Proxy dead → replace
        - Rate limited → wait + rotate
        - Too fast → increase delay
        """
        now = time.time()
        if now - self.last_heal_time < self.heal_cooldown:
            return {"action": "skip", "reason": "cooldown"}

        self.last_heal_time = now
        self.heals_performed += 1

        cf = brute_instance.consecutive_fails
        sf = brute_instance.session_fails
        tested = max(brute_instance.tested, 1)

        result = {"action": "none", "reason": "", "rest": 0, "delay_changed": False}

        # ═══════════════════════
        # PROXY DEAD
        # ═══════════════════════
        if cf >= 2 and brute_instance.proxy_manager:
            ai("Healer: Proxy seems dead — forcing rotation...")
            brute_instance.proxy_manager.refresh_all()
            result["action"] = "proxy_refreshed"
            result["reason"] = f"{cf} consecutive fails"
            time.sleep(random.uniform(2, 4))
            return result

        # ═══════════════════════
        # RATE LIMITED
        # ═══════════════════════
        if cf >= 5 and tested > 0:
            wait = random.uniform(30, 90)
            ai(f"Healer: {cf} fails — force-rest {wait:.0f}s + rotate fingerprint...")
            brute_instance.consecutive_fails = 0
            result["action"] = "force_rest"
            result["reason"] = "Too many fails"
            result["rest"] = wait
            result["delay_changed"] = False
            time.sleep(wait)
            return result

        # ═══════════════════════
        # INCREASE DELAY
        # ═══════════════════════
        if sf > 5 and tested > 10:
            old_delay = brute_instance.delays[1]
            new_delay = min(old_delay * 1.5, 20)
            brute_instance.delays = (brute_instance.delays[0], new_delay)
            ai(f"Healer: Increased delay {old_delay:.1f}s → {new_delay:.1f}s")
            result["action"] = "delay_increased"
            result["reason"] = f"{sf} session fails"
            result["delay_changed"] = True
            brute_instance.session_fails = 0

        # ═══════════════════════
        # MEMORY RECORD
        # ═══════════════════════
        if self.memory:
            self.memory.record_delay("heal", (brute_instance.delays[1] + brute_instance.delays[0]) / 2)

        return result
