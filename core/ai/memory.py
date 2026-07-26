#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Memory — learns from every operation.
Remembers what worked, what failed, adapts permanently.
"""
import json, os, time
from threading import Lock

class AIMemory:
    def __init__(self, path="output/ai_memory.json"):
        self.path = path
        self._lock = Lock()
        self.data = self._load()

    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return self._default()

    def _default(self):
        return {
            "created": time.time(),
            "total_operations": 0,
            "successes": 0,
            "failures": 0,
            "targets": {},
            "errors_seen": {},
            "working_methods": [],
            "failed_methods": [],
            "proxy_stats": {"total_used": 0, "total_dead": 0},
            "rate_limit_hits": 0,
            "checkpoints_found": 0,
            "adaptive_delays": {"osint": 1.0, "brute_min": 3.0, "brute_max": 5.0},
            "session_history": [],
            "learnings": [],
        }

    def save(self):
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    def record_operation(self, target, operation, success, details=""):
        with self._lock:
            self.data["total_operations"] += 1
            if success:
                self.data["successes"] += 1
            else:
                self.data["failures"] += 1

            if target not in self.data["targets"]:
                self.data["targets"][target] = {"ops": 0, "successes": 0, "failures": 0, "history": []}
            t = self.data["targets"][target]
            t["ops"] += 1
            if success: t["successes"] += 1
            else: t["failures"] += 1
            t["history"].append({
                "time": time.time(), "op": operation,
                "success": success, "details": details[:200]
            })
            if len(t["history"]) > 50: t["history"] = t["history"][-50:]

        self.save()

    def record_error(self, error_type, target="", details=""):
        with self._lock:
            key = f"{error_type}:{target}" if target else error_type
            if key not in self.data["errors_seen"]:
                self.data["errors_seen"][key] = {"count": 0, "first_seen": time.time(), "last_seen": 0}
            e = self.data["errors_seen"][key]
            e["count"] += 1; e["last_seen"] = time.time()
            if details: e["last_detail"] = details[:200]

            if error_type == "rate_limit": self.data["rate_limit_hits"] += 1
            elif error_type == "checkpoint": self.data["checkpoints_found"] += 1

        self.save()

    def record_method(self, method_name, worked):
        with self._lock:
            target_list = self.data["working_methods"] if worked else self.data["failed_methods"]
            if method_name not in target_list:
                target_list.append(method_name)
        self.save()

    def record_proxy(self, alive):
        with self._lock:
            self.data["proxy_stats"]["total_used"] += 1
            if not alive: self.data["proxy_stats"]["total_dead"] += 1
        self.save()

    def get_adaptive_delay(self, delay_type="brute_min"):
        with self._lock:
            return self.data.get("adaptive_delays", {}).get(delay_type, 3.0)

    def update_adaptive_delay(self, delay_type, new_value):
        with self._lock:
            if "adaptive_delays" not in self.data:
                self.data["adaptive_delays"] = {}
            old = self.data["adaptive_delays"].get(delay_type, new_value)
            # Smooth transition
            self.data["adaptive_delays"][delay_type] = round(old * 0.7 + new_value * 0.3, 2)
        self.save()

    def add_learning(self, insight):
        with self._lock:
            self.data["learnings"].append({
                "time": time.time(), "insight": insight[:500]
            })
            if len(self.data["learnings"]) > 100: self.data["learnings"] = self.data["learnings"][-100:]
        self.save()

    def get_target_stats(self, target):
        with self._lock:
            return self.data.get("targets", {}).get(target, {})

    def get_error_count(self, error_type):
        with self._lock:
            return sum(
                v.get("count", 0) for k, v in self.data.get("errors_seen", {}).items()
                if error_type in k
            )

    def summary(self):
        with self._lock:
            d = self.data
            return {
                "ops": d["total_operations"],
                "success_rate": f"{d['successes'] / max(d['total_operations'], 1) * 100:.1f}%",
                "targets": len(d["targets"]),
                "rate_limits": d["rate_limit_hits"],
                "checkpoints": d["checkpoints_found"],
                "proxies_used": d["proxy_stats"]["total_used"],
                "proxies_dead": d["proxy_stats"]["total_dead"],
                "learnings": len(d["learnings"]),
                "adaptive_delays": d["adaptive_delays"],
            }
