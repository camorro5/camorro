#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Healer — auto-detects problems and fixes them.
"""
import time, random
from ..banner import ai, info, ok, warn, err

class AIHealer:
    def __init__(self, memory):
        self.memory = memory
        self._heal_count = 0

    def diagnose(self, error_status, context=""):
        """Analyze error and return healing action."""
        action = {"type": "none", "reason": ""}

        if error_status in ("timeout", "connection_error"):
            action = {
                "type": "switch_proxy",
                "reason": f"Connection failed: {error_status}",
                "suggestions": ["rotate_proxy", "go_direct", "increase_timeout"]
            }
        elif error_status == "rate_limited":
            action = {
                "type": "backoff",
                "reason": "Rate limit detected",
                "suggestions": ["increase_delay", "rotate_identity", "cool_down"],
                "cooldown": 60 + (self.memory.get_error_count("rate_limit") * 10)
            }
        elif error_status == "login_wall":
            action = {
                "type": "authenticate",
                "reason": "Login wall hit",
                "suggestions": ["use_sessionid", "rotate_fingerprint", "use_mobile_ua"]
            }
        elif error_status == "checkpoint":
            action = {
                "type": "flag",
                "reason": "Checkpoint triggered — account locked or suspicious login",
                "suggestions": ["save_password", "reduce_speed", "change_proxy"]
            }
        elif error_status == "empty_data":
            action = {
                "type": "switch_method",
                "reason": "No data returned",
                "suggestions": ["try_next_endpoint", "rotate_fingerprint", "use_desktop"]
            }
        elif error_status == "invalid_user":
            action = {
                "type": "stop",
                "reason": "Username does not exist",
                "suggestions": ["verify_username", "stop_operation"]
            }
        else:
            action = {
                "type": "retry",
                "reason": f"Unknown error: {error_status}",
                "suggestions": ["retry_once", "log_error"]
            }

        self.memory.record_error(error_status, context, action["reason"])
        self._heal_count += 1
        return action

    def apply_healing(self, action, context_obj=None):
        """Execute healing action. Returns new parameters."""
        result = {"healed": False, "new_delay": None, "new_proxy": None, "new_method": None}

        if action["type"] == "switch_proxy":
            ai("Healing: switching proxy...")
            if context_obj and hasattr(context_obj, 'proxy_mgr'):
                context_obj.proxy_mgr.mark_dead(context_obj.proxy_mgr.get_next())
                new_proxy = context_obj.proxy_mgr.get_next()
                if new_proxy: result["new_proxy"] = new_proxy; result["healed"] = True
                else:
                    ai("Healing: all proxies dead, going DIRECT")
                    result["new_proxy"] = None; result["healed"] = True

        elif action["type"] == "backoff":
            cooldown = action.get("cooldown", 60)
            ai(f"Healing: backing off {cooldown}s...")
            time.sleep(min(cooldown, 120))
            new_delay = self.memory.get_adaptive_delay("brute_min") * 1.5
            self.memory.update_adaptive_delay("brute_min", new_delay)
            self.memory.update_adaptive_delay("brute_max", new_delay * 1.5)
            result["new_delay"] = new_delay; result["healed"] = True

        elif action["type"] == "switch_method":
            ai("Healing: switching OSINT method...")
            result["new_method"] = "next"; result["healed"] = True

        elif action["type"] == "authenticate":
            ai("Healing: need authentication — using sessionid if available...")
            import os
            sid = os.environ.get("IG_SESSIONID")
            if sid: result["healed"] = True; ai("sessionid found, will attach")
            else: warn("No sessionid available — may hit login wall again")

        elif action["type"] == "flag":
            ai("Healing: flagging checkpoint — saved for manual review")
            result["healed"] = True

        elif action["type"] == "retry":
            ai("Healing: retrying...")
            result["healed"] = True

        self.memory.add_learning(f"Healed: {action['type']} — {action['reason']}")
        return result

    def suggest_strategy(self, target_stats):
        """Based on target history, suggest best approach."""
        if not target_stats: return "standard"

        failures = target_stats.get("failures", 0)
        successes = target_stats.get("successes", 0)
        total = target_stats.get("ops", 1)

        if failures > successes * 2 and total > 5:
            return "cautious"  # Increase delays, use best proxies
        if successes > 0 and failures == 0:
            return "aggressive"  # Speed up
        if total > 20 and failures > 15:
            return "avoid"  # Target is well-protected, skip or manual
        return "standard"
