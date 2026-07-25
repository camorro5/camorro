#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Wordlist Generator — creates targeted password lists."""

import itertools
import os
import random


class WordlistAI:
    """Generates targeted wordlists from intelligence data."""

    SPECIAL = ["", "!", "@", "#", "$", "%", "*", ".", "_", "-"]
    SUFFIXES = ["123", "1234", "12345", "123456", "12345678", "1", "12", "123",
                "!", "@", "#", "2024", "2025", "2026", "2027", "007", "666", "777"]

    LEET = {
        "a": ["a", "4", "@"], "e": ["e", "3"], "i": ["i", "1", "!"],
        "o": ["o", "0"], "s": ["s", "5", "$"], "t": ["t", "7"],
        "b": ["b", "8"], "l": ["l", "1"],
    }

    def __init__(self, answers, target_count=18000):
        self.answers = answers
        self.target_count = target_count
        self._passwords = set()

    def generate(self):
        self._passwords.clear()
        tokens = self._collect_tokens()

        self._basic(tokens)
        self._with_years(tokens)
        self._with_suffixes(tokens)
        self._with_special(tokens)
        self._leet(tokens)
        self._combos(tokens)

        pw_list = list(self._passwords)
        random.shuffle(pw_list)

        if len(pw_list) > self.target_count:
            pw_list = pw_list[:self.target_count]

        pw_list = [p for p in pw_list if 4 <= len(p) <= 128]
        self._passwords = set(pw_list)

    def _collect_tokens(self):
        raw = []
        fields = ["full_name", "nickname", "partner", "pet", "child",
                  "mother", "father", "city", "sport", "team", "artist",
                  "movie", "color", "number", "hobby", "car", "phone", "email"]

        for f in fields:
            v = self.answers.get(f, "")
            if v:
                v_clean = v.lower().replace(" ", "")
                raw.extend([v, v.lower(), v_clean])
                for part in v.split():
                    if len(part) >= 2:
                        raw.extend([part, part.lower()])

        uname = self.answers.get("username", "")
        if uname:
            raw.extend([uname, uname.lower()])

        # Birth date
        y = self.answers.get("birth_year", "")
        m = self.answers.get("birth_month", "")
        d = self.answers.get("birth_day", "")
        if y:
            raw.extend([y, y[-2:]])
        if m:
            raw.append(m.zfill(2))
        if d:
            raw.append(d.zfill(2))

        # Extra keywords
        extra = self.answers.get("extra", "")
        for kw in extra.split(","):
            kw = kw.strip()
            if kw:
                raw.append(kw)

        # OSINT tokens
        for t in self.answers.get("osint_tokens", []):
            raw.append(t)
        for yr in self.answers.get("osint_years", []):
            raw.extend([yr, yr[-2:]])

        # Deduplicate
        seen = set()
        result = []
        for t in raw:
            t = t.strip()
            if t and t not in seen and len(t) >= 2:
                seen.add(t)
                result.append(t)
        return result

    def _add(self, pw):
        pw = pw.strip()
        if 4 <= len(pw) <= 128:
            self._passwords.add(pw)

    def _basic(self, tokens):
        for t in tokens:
            self._add(t)
            self._add(t.capitalize())
            self._add(t.upper())

    def _with_years(self, tokens):
        years = list(set(self.answers.get("osint_years", []) +
                    [self.answers.get("birth_year", "")]))
        years = [y for y in years if y]
        for t in tokens[:50]:
            for yr in years[:5]:
                self._add(f"{t}{yr}")
                self._add(f"{yr}{t}")
                self._add(f"{t.capitalize()}{yr}")

    def _with_suffixes(self, tokens):
        for t in tokens[:50]:
            for sfx in self.SUFFIXES[:10]:
                self._add(f"{t}{sfx}")
                self._add(f"{t.capitalize()}{sfx}")

    def _with_special(self, tokens):
        sample = tokens[:25]
        for a, b in itertools.product(sample, sample):
            if a == b:
                continue
            for sep in ["", ".", "_", "-"]:
                self._add(f"{a}{sep}{b}")
                self._add(f"{a.capitalize()}{sep}{b.capitalize()}")
            if len(self._passwords) >= self.target_count * 2:
                return

    def _leet(self, tokens):
        for t in tokens[:15]:
            t_lower = t.lower()
            chars = []
            for c in t_lower:
                chars.append(self.LEET.get(c, [c, c.upper()]))
            count = 0
            for combo in itertools.product(*chars):
                pw = "".join(combo)
                if pw != t and pw != t_lower:
                    self._add(pw)
                    count += 1
                    if count >= 50:
                        break

    def _combos(self, tokens):
        nums = ["123", "1234", "12345", "123456", "12345678", "1", "12", "0",
                "01", "007", "666", "777", "999", "2024", "2025", "2026"]
        for t in tokens[:50]:
            for n in random.sample(nums, min(5, len(nums))):
                self._add(f"{t}{n}")
                self._add(f"{n}{t}")

    @property
    def count(self):
        return len(self._passwords)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for pw in sorted(self._passwords):
                f.write(pw + "\n")

    def get_list(self):
        return sorted(self._passwords)
