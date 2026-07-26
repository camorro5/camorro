#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelligence Interview — interactive intel for wordlist."""

import json
import os
from .banner import info, ask, C


class Interviewer:
    """Collects human intel to combine with OSINT hints."""

    def __init__(self, username, hints, output_dir):
        self.username = username.strip().lstrip("@")
        self.hints = hints or {}
        self.output_dir = output_dir
        self.answers = {}

    def run(self):
        print(f"\n{C.C}┌──────────────────────────────────────────┐{C.E}")
        print(f"{C.C}│{C.E}  INTELLIGENCE INTERVIEW                  {C.C}│")
        print(f"{C.C}│{C.E}  Answer to build a TARGETED wordlist      {C.C}│")
        print(f"{C.C}│{C.E}  (ENTER = skip any question)              {C.C}│")
        print(f"{C.C}└──────────────────────────────────────────┘{C.E}\n")

        if self.hints.get("full_name"):
            info(f"OSINT name hint: {self.hints.get('full_name')}")
        if self.hints.get("followers"):
            info(
                f"OSINT stats: {self.hints.get('followers')} followers, "
                f"{self.hints.get('posts', 0)} posts"
            )
        if self.hints.get("biography"):
            info(f"OSINT bio: {str(self.hints.get('biography'))[:80]}")

        self.answers["username"] = self.username

        self.answers["full_name"] = ask(
            "Full name", self.hints.get("full_name", "")
        )
        self.answers["nickname"] = ask("Nickname / Alias")
        self.answers["birth_year"] = ask("Birth year (YYYY)")
        self.answers["birth_month"] = ask("Birth month (1-12)")
        self.answers["birth_day"] = ask("Birth day (1-31)")

        self.answers["partner"] = ask("Partner / Spouse name")
        self.answers["pet"] = ask("Pet name")
        self.answers["child"] = ask("Child name")
        self.answers["mother"] = ask("Mother's name")
        self.answers["father"] = ask("Father's name")

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
        self.answers["extra"] = ask("Extra keywords (comma-separated)")

        # Merge OSINT into answers for WordlistAI
        self.answers["biography"] = self.hints.get("biography", "")
        self.answers["bio_tokens"] = self.hints.get("bio_tokens", [])
        self.answers["osint_tokens"] = self.hints.get("bio_tokens", [])
        self.answers["osint_years"] = self.hints.get("years", [])
        self.answers["years"] = self.hints.get("years", [])
        self.answers["phones"] = self.hints.get("phones", [])
        self.answers["osint_phones"] = self.hints.get("phones", [])
        self.answers["user_parts"] = self.hints.get("user_parts", [])
        self.answers["stat_numbers"] = self.hints.get("stat_numbers", [])
        self.answers["followers"] = self.hints.get("followers", 0)
        self.answers["following"] = self.hints.get("following", 0)
        self.answers["posts"] = self.hints.get("posts", 0)
        self.answers["category"] = self.hints.get("category", "")
        self.answers["external_url"] = self.hints.get("external_url", "")

        if not self.answers.get("full_name"):
            self.answers["full_name"] = self.hints.get("full_name", "")

        self._save()
        info("Interview saved ✓")
        return self.answers

    def _save(self):
        path = os.path.join(
            self.output_dir, self.username, "interview.json"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.answers, f, indent=2, ensure_ascii=False)
