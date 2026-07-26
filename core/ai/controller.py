#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Controller — orchestrates all modules."""
import time

try:
    from ..banner import info, ok, warn, err, ai, C
    from .brain import Brain
    from .memory import Memory
    from .healer import Healer
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    def ai(m):   print(f"[AI] {m}")
    class C: R=G=Y=C=M=W=E=""
    from brain import Brain
    from memory import Memory
    from healer import Healer


class AIController:
    """Central AI — manages brain, memory, healer."""

    def __init__(self):
        self.memory = Memory()
        self.brain = Brain(memory=self.memory)
        self.healer = Healer(brain=self.brain, memory=self.memory)
        self.active = True
        self.total_heals = 0
        self.total_decisions = 0
        ai("AI Controller initialized — Brain+Memory+Healer online")

    def record_attempt(self, password, result):
        """Called after each brute-force attempt."""
        self.memory.record_attempt(password=password, result=result)

    def record_proxy(self, alive, url=""):
        """Called when proxy succeeds or fails."""
        self.memory.record_proxy(alive=alive, url=url)

    def record_error(self, error_msg, context=""):
        self.memory.record_error(error_msg, context)

    def think(self, context):
        """Make a decision based on current context."""
        decision = self.brain.think(context)
        self.total_decisions += 1
        return decision

    def heal(self, brute_instance):
        """Auto-heal when things go wrong."""
        result = self.healer.heal(brute_instance)
        self.total_heals += 1
        return result

    def status(self):
        """Show AI status."""
        s = self.memory.stats()
        bs = self.brain.get_state()
        print(f"""
{C.C}+==================================================+
|              AI CONTROLLER — STATUS             |
+==================================================+
|  Brain State     : {bs['state']}                          |
|  Decisions       : {self.total_decisions}                    |
|  Heals           : {self.total_heals}                    |
|  Uptime          : {s['uptime']}                   |
|  Total Attempts  : {s['total_attempts']}          |
|  Proxy Rate      : {s['proxy_success_rate']}      |
|  Attempt Rate    : {s['attempt_success_rate']}    |
+==================================================+{C.E}
""")

    @staticmethod
    def wrap_brute(brute_instance):
        """Wrap brute-force with AI monitoring loop."""
        # This is a hook for TUI integration
        pass
