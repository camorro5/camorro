#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camoro AI-like human password wordlist engine."""

import itertools
import os
import random
import re
from datetime import datetime

from core.banner import info, success


class WordlistAI:
    DEFAULT_SYMBOLS = list("!@#_$.*")
    LEET_MAP = {
        "a": ["a", "A", "@", "4"],
        "e": ["e", "E", "3"],
        "i": ["i", "I", "1", "!"],
        "o": ["o", "O", "0"],
        "s": ["s", "S", "$", "5"],
        "t": ["t", "T", "7"],
        "b": ["b", "B", "8"],
        "g": ["g", "G", "9"],
        "l": ["l", "L", "1"],
    }
    COMMON_SUFFIXES = [
        "", "1", "12", "123", "1234", "12345", "123456",
        "01", "007", "69", "77", "88", "99", "100",
        "!", "@", "#", "!!", "!!!", "@#", "@!",
        "2000", "2010", "2020", "2021", "2022", "2023", "2024", "2025", "2026",
    ]
    COMMON_PREFIXES = ["", ".", "_", "@"]
    COMMON_BASES = [
        "password", "pass", "admin", "qwerty", "iloveyou", "welcome",
        "instagram", "insta", "love", "lover", "baby", "angel", "king",
        "queen", "prince", "princess", "shadow", "dragon", "football",
        "ahlan", "habibi", "yallah", "wallah", "inshallah", "mashallah",
        "allah", "rahma", "noor", "omar", "ali", "mohammed", "ahmed",
        "fatima", "sara", "layla", "nour", "hassan", "hussain",
    ]
    ARABIC_COMMON = [
        "مرحبا", "حبيبي", "الله", "نور", "أمل", "قمر", "شمس", "ورد",
        "سعد", "فهد", "نورة", "هند", "ريم", "لينا", "ياسر", "خالد",
    ]

    def __init__(self, answers, target_count=18000):
        self.answers = answers or {}
        self.target_count = max(100, int(target_count))
        self.passwords = []

    def generate(self):
        info("AI Wordlist engine thinking like a human · target %d ..." % self.target_count)
        seeds = self._collect_seeds()
        years = self._collect_years()
        symbols = self._symbols()
        dates = self._date_tokens()
        phones = self._phone_tokens()
        candidates = set()

        for s in seeds:
            for v in self._casings(s):
                candidates.add(v)

        for s, y in itertools.product(seeds[:80], years):
            for a, b in ((s, y), (y, s)):
                candidates.add("%s%s" % (a, b))
                candidates.add("%s_%s" % (a, b))
                candidates.add("%s.%s" % (a, b))
                for sym in symbols[:4]:
                    candidates.add("%s%s%s" % (a, sym, b))
                    candidates.add("%s%s%s" % (a, b, sym))

        for s, d in itertools.product(seeds[:60], dates):
            candidates.add("%s%s" % (s, d))
            candidates.add("%s%s" % (d, s))
            candidates.add("%s@%s" % (s, d))
            candidates.add("%s#%s" % (s, d))

        for s, p in itertools.product(seeds[:40], phones):
            candidates.add("%s%s" % (s, p))
            candidates.add("%s%s" % (p, s))
            candidates.add("%s@%s" % (s, p))

        name_parts = [x for x in seeds if x.isalpha() or self._is_ar(x)][:20]
        for a, b in itertools.permutations(name_parts, 2):
            candidates.add("%s%s" % (a, b))
            candidates.add("%s_%s" % (a, b))
            candidates.add("%s.%s" % (a, b))
            candidates.add("%s%s1" % (a, b))
            candidates.add("%s%s123" % (a, b))
            for y in years[:6]:
                candidates.add("%s%s%s" % (a, b, y))
                candidates.add("%s_%s%s" % (a, b, y))
                candidates.add("%s%s@%s" % (a, b, y))

        for s in list(seeds)[:100]:
            for pre in self.COMMON_PREFIXES:
                for suf in self.COMMON_SUFFIXES:
                    candidates.add("%s%s%s" % (pre, s, suf))

        for s in list(seeds)[:25]:
            for leet in self._leet_variants(s, limit=40):
                candidates.add(leet)
                for y in years[:4]:
                    candidates.add("%s%s" % (leet, y))
                    candidates.add("%s@%s" % (leet, y))
                for suf in ["", "1", "12", "123", "!", "@"]:
                    candidates.add("%s%s" % (leet, suf))

        user = self.answers.get("username") or ""
        for base in self.COMMON_BASES:
            candidates.add(base)
            candidates.add(base + "123")
            if user:
                candidates.add(user + base)
                candidates.add(base + user)
            for y in years[:5]:
                candidates.add(base + y)

        for ar in self.ARABIC_COMMON:
            candidates.add(ar)
            for y in years[:4]:
                candidates.add("%s%s" % (ar, y))

        known = self._split_csv(self.answers.get("known_passwords", ""))
        for k in known:
            candidates.add(k)
            for v in self._casings(k):
                candidates.add(v)
            for suf in ["1", "12", "123", "!", "@", "2024", "2025", "2026"]:
                candidates.add(k + suf)
            for leet in self._leet_variants(k, limit=20):
                candidates.add(leet)

        if user:
            for v in self._casings(user):
                candidates.add(v)
                candidates.add(v + "123")
                candidates.add(v + "!")
                candidates.add(v + "@")
                for y in years:
                    candidates.add(v + y)
                    candidates.add("%s@%s" % (v, y))

        cleaned = []
        seen = set()
        for p in candidates:
            p = self._clean(p)
            if not p or p in seen:
                continue
            if len(p) < 4 or len(p) > 64:
                continue
            seen.add(p)
            cleaned.append(p)

        ranked = self._rank(cleaned)
        if len(ranked) < self.target_count:
            ranked = self._inflate(ranked, self.target_count)
        self.passwords = ranked[: self.target_count]
        success("Generated %d smart passwords" % len(self.passwords))
        return self.passwords

    def save(self, path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.passwords))
            f.write("\n")
        success("Wordlist saved → %s (%d lines)" % (path, len(self.passwords)))
        return path

    def _collect_seeds(self):
        a = self.answers
        seeds = []

        def add(x):
            if not x:
                return
            x = str(x).strip()
            if not x:
                return
            seeds.append(x)
            if " " in x:
                seeds.append(x.replace(" ", ""))
                seeds.append(x.replace(" ", "_"))
                seeds.append(x.replace(" ", "."))
                for part in x.split():
                    if len(part) >= 2:
                        seeds.append(part)

        add(a.get("username"))
        add(a.get("full_name"))
        add(a.get("first_name"))
        add(a.get("last_name"))
        add(a.get("nickname"))
        add(a.get("city"))
        add(a.get("country"))
        add(a.get("school"))
        add(a.get("job"))
        add(a.get("partner"))
        add(a.get("child"))
        add(a.get("pet"))
        add(a.get("team"))
        add(a.get("hobby"))
        add(a.get("old_username"))
        add(a.get("email_local"))
        for t in a.get("osint_tokens") or []:
            add(t)
        for w in self._split_csv(a.get("custom_words", "")):
            add(w)
        for w in self._split_csv(a.get("arabic_words", "")):
            add(w)

        fn, ln = a.get("first_name", ""), a.get("last_name", "")
        if fn and ln:
            add(fn[0] + ln)
            add(fn + ln[0])
            add(fn[0] + ln[0])

        out, seen = [], set()
        for s in seeds:
            s2 = s.strip()
            key = s2.lower()
            if s2 and key not in seen:
                seen.add(key)
                out.append(s2)
        return out

    def _collect_years(self):
        years = set()
        by = self.answers.get("birth_year") or ""
        if re.fullmatch(r"(19|20)\d{2}", by):
            years.add(by)
            years.add(by[-2:])
        for y in self.answers.get("osint_years") or []:
            ys = str(y)
            if re.fullmatch(r"(19|20)\d{2}", ys):
                years.add(ys)
                years.add(ys[-2:])
        years.update(["2000", "2010", "2020", "2021", "2022", "2023", "2024", "2025", "2026"])
        if by.isdigit() and len(by) == 4:
            yi = int(by)
            for d in range(-3, 4):
                years.add(str(yi + d))
        return sorted(years, key=lambda x: (len(x), x))

    def _date_tokens(self):
        raw_d = self.answers.get("birth_day", "")
        raw_m = self.answers.get("birth_month", "")
        d = raw_d.zfill(2) if raw_d else ""
        m = raw_m.zfill(2) if raw_m else ""
        y = self.answers.get("birth_year", "")
        out = []
        if d and d != "00":
            out += [d, d.lstrip("0") or d]
        if m and m != "00":
            out += [m, m.lstrip("0") or m]
        if d and m and d != "00" and m != "00":
            out += [d + m, m + d]
            if y:
                out += [d + m + y, d + m + y[-2:], y + m + d]
                out += ["%s/%s/%s" % (d, m, y), "%s-%s-%s" % (d, m, y)]
        if y:
            out.append(y)
            out.append(y[-2:])
        return list(dict.fromkeys([x for x in out if x]))

    def _phone_tokens(self):
        out = []
        phones = [self.answers.get("phone", "")] + list(self.answers.get("osint_phones") or [])
        for p in phones:
            digits = re.sub(r"\D", "", str(p))
            if not digits:
                continue
            out.append(digits)
            if len(digits) >= 4:
                out.append(digits[-4:])
            if len(digits) >= 6:
                out.append(digits[-6:])
            if len(digits) >= 7:
                out.append(digits[-7:])
            if digits.startswith("0"):
                out.append(digits.lstrip("0"))
        last4 = self.answers.get("phone_last4", "")
        if last4:
            out.append(re.sub(r"\D", "", last4))
        return list(dict.fromkeys([x for x in out if x]))

    def _symbols(self):
        pref = self.answers.get("symbols_pref") or ""
        if pref:
            return list(pref) + [s for s in self.DEFAULT_SYMBOLS if s not in pref]
        return list(self.DEFAULT_SYMBOLS)

    def _casings(self, s):
        if not s:
            return []
        out = [s, s.lower(), s.upper(), s.capitalize()]
        if len(s) > 1:
            out.append(s[0].upper() + s[1:].lower())
            out.append(s.title())
        return list(dict.fromkeys(out))

    def _leet_variants(self, s, limit=40):
        s = s.lower()
        pools = []
        for ch in s:
            pools.append(self.LEET_MAP.get(ch, [ch]))
        results = [s]
        for i, ch in enumerate(s):
            if ch in self.LEET_MAP:
                for rep in self.LEET_MAP[ch]:
                    if rep == ch:
                        continue
                    results.append(s[:i] + rep + s[i + 1 :])
        try:
            for combo in itertools.islice(itertools.product(*pools), limit):
                results.append("".join(combo))
        except Exception:
            pass
        return list(dict.fromkeys(results))[:limit]

    def _rank(self, items):
        user = (self.answers.get("username") or "").lower()
        fn = (self.answers.get("first_name") or "").lower()
        year = self.answers.get("birth_year") or ""

        def score(p):
            pl = p.lower()
            s = 0
            if fn and fn in pl:
                s += 50
            if user and user in pl:
                s += 40
            if year and year in p:
                s += 30
            if any(sy in p for sy in "!@#_"):
                s += 10
            if re.search(r"\d", p):
                s += 5
            if 6 <= len(p) <= 14:
                s += 15
            return (-s, len(p), p)

        return sorted(items, key=score)

    def _inflate(self, base, target):
        out = list(base)
        seen = set(out)
        extras = ["1", "12", "123", "1234", "!", "!!", "@", "#", "007", "99", "00"]
        years = [str(y) for y in range(1995, datetime.now().year + 1)]
        i = 0
        while len(out) < target and i < max(1, len(base)) * 20:
            src = base[i % max(1, len(base))] if base else "pass"
            i += 1
            for mut in (
                src + random.choice(extras),
                src + random.choice(years),
                src.capitalize() + random.choice(extras),
                src.lower() + "!",
                src + str(random.randint(0, 99)).zfill(2),
            ):
                mut = self._clean(mut)
                if mut and mut not in seen and 4 <= len(mut) <= 64:
                    seen.add(mut)
                    out.append(mut)
                if len(out) >= target:
                    break
        return out

    @staticmethod
    def _clean(p):
        if p is None:
            return ""
        return str(p).strip().replace("\x00", "")

    @staticmethod
    def _split_csv(s):
        if not s:
            return []
        return [x.strip() for x in re.split(r"[,،;|]", s) if x.strip()]

    @staticmethod
    def _is_ar(s):
        return bool(re.search(r"[\u0600-\u06FF]", s or ""))
