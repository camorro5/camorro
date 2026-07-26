#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Brain — decision engine. Analyzes situation, picks best action.
"""
import time, random
from .memory import AIMemory
from .healer import AIHealer
from ..banner import ai, info, ok, warn, err

class AIBrain:
    def __init__(self):
        self.memory = AIMemory()
        self.healer = AIHealer(self.memory)
        self.current_target = ""
        self.current_phase = ""
        self.start_time = 0
        self._state = "idle"

    def start_session(self, target):
        self.current_target = target
        self.start_time = time.time()
        self._state = "running"
        target_stats = self.memory.get_target_stats(target)
        strategy = self.healer.suggest_strategy(target_stats)
        ai(f"Session started — target: @{target}")
        ai(f"Strategy: {strategy} | History: {target_stats.get('ops', 0)} ops, "
           f"{target_stats.get('successes', 0)} wins, {target_stats.get('failures', 0)} losses")
        return strategy

    def decide_osint_method(self, available_methods):
        """Pick which OSINT method to try first based on past success."""
        working = self.memory.data.get("working_methods", [])
        failed = self.memory.data.get("failed_methods", [])

        # Prioritize methods that worked before
        for method in working:
            if method in available_methods:
                return method

        # Avoid methods that consistently failed
        for method in available_methods:
            if method not in failed:
                return method

        return available_methods[0] if available_methods else "web_profile_info"

    def handle_osint_result(self, success, method_used, data_present):
        self.memory.record_method(method_used, success)
        self.memory.record_operation(
            self.current_target, f"osint:{method_used}",
            success, f"data={data_present}"
        )
        if not success:
            action = self.healer.diagnose("empty_data", self.current_target)
            return self.healer.apply_healing(action)
        return {"healed": False}

    def handle_brute_error(self, error_status, password_tried=""):
        """AI decides how to handle a brute force error."""
        action = self.healer.diagnose(error_status, self.current_target)
        ai(f"Detected: {error_status} | Action: {action['type']}")

        if error_status == "rate_limited":
            self.memory.update_adaptive_delay("brute_min", self.memory.get_adaptive_delay("brute_min") + 0.5)
            self.memory.update_adaptive_delay("brute_max", self.memory.get_adaptive_delay("brute_max") + 1.0)

        if password_tried and error_status == "checkpoint":
            self.memory.add_learning(f"Checkpoint password: {password_tried} for @{self.current_target}")

        return action

    def should_continue_brute(self, attempt, total, errors_recent):
        """AI decides if brute should continue or pause."""
        if errors_recent >= 10:
            ai("Too many errors — pausing 120s to avoid permanent block")
            time.sleep(120)
            return True  # Continue after pause

        if attempt > 0 and attempt % 500 == 0:
            # Periodic health check
            stats = self.memory.summary()
            ai(f"Health check: {stats['success_rate']} success | {stats['rate_limits']} rate limits")
        return True

    def end_session(self, result_summary):
        elapsed = time.time() - self.start_time
        self._state = "idle"
        self.memory.add_learning(
            f"Session @{self.current_target} ended: {result_summary} in {elapsed:.0f}s"
        )
        ai(f"Session ended — {elapsed:.0f}s | {result_summary}")

    def get_status(self):
        return {
            "target": self.current_target,
            "phase": self.current_phase,
            "state": self._state,
            "memory": self.memory.summary(),
            "elapsed": time.time() - self.start_time if self.start_time else 0
        }
