#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelligence Interview — interactive information gathering."""

import json
import os
from .banner import info, warn, ask, C


class Interviewer:
    """Collects intel for targeted wordlist generation."""

    def __init__(self, username, hints, output_dir):
        self.username = username
        self.hints = hints
        self.output_dir = output_dir
        self.answers = {}

    def run(self):
        print(f"\n{C.C}┌──────────────────────────────────────────┐{C.E}")
        print(f"{C.C}│{C.E}  🧠  INTELLIGENCE INTERVIEW              {C.C}│")
        print(f"{C.C}│{C.E}  Answer to build a targeted wordlist     {C.C}│")
        print(f"{C.C}│{C.E}  (ENTER = skip)                          {C.C}│")
        print(f"{C.C}└──────────────────────────────────────────┘{C.E}\n")

        self.answers["username"] = self.username

        # Basic
        self.answers["full_name"] = ask("Full name", self.hints.get("full_name", ""))
        self.answers["nickname"] = ask("Nickname / Alias")
        self.answers["birth_year"] = ask("Birth year (YYYY)")
        self.answers["birth_month"] = ask("Birth month (1-12)")
        self.answers["birth_day"] = ask("Birth day (1-31)")

        # Relationships
        self.answers["partner"] = ask("Partner / Spouse name")
        self.answers["pet"] = ask("Pet name")
        self.answers["child"] = ask("Child name")
        self.answers["mother"] = ask("Mother's name")
        self.answers["father"] = ask("Father's name")

        # Personal
        self.answers["city"] = ask("City / Hometown")
        self.answers["sport"] = ask("Favorite sport")
        self.answers["team"] = ask("Favorite team")
        self.answers["artist"] = ask("Favorite artist/band")
        self.answers["movie"] = ask("Favorite movie")
        self.answers["color"] = ask("Favorite color")
        self.answers["number"] = ask("Lucky number")
        self.answers["hobby"] = ask("Hobby")
        self.answers["car"] = ask("Car brand/model")
        self.answers["phone"] = ask("Phone number (if known)")
        self.answers["email"] = ask("Email (if known)")

        # Extra
        self.answers["extra"] = ask("Extra keywords (comma-separated)")

        # OSINT hints
        self.answers["osint_tokens"] = self.hints.get("bio_tokens", [])
        self.answers["osint_years"] = self.hints.get("years", [])
        self.answers["osint_phones"] = self.hints.get("phones", [])

        self._save()
        return self.answers

    def _save(self):
        path = os.path.join(self.output_dir, self.username, "interview.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.answers, f, indent=2, ensure_ascii=False)
        info("Interview saved ✓")
