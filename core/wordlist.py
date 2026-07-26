#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Targeted AI Wordlist generator.

Builds passwords ONLY from:
  - OSINT (name, bio tokens, years, phones, username parts, stats digits)
  - Interview answers (nickname, city, partner, dates, ...)
Not random junk — intel-first, then controlled expansion to target_count.
"""

import itertools
import os
import re
import random


class WordlistAI:
    SPECIAL = ["", "!", "@", "#", "$", "*", ".", "_", "-"]
    SUFFIXES = [
        "123", "1234", "12345", "123456", "12345678", "123456789",
        "1", "12", "01", "00", "007", "111", "000",
        "!", "@", "#", "!!",
        "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027",
        "2000", "2001", "1990", "1995", "1998", "1999",
    ]
    COMMON_BASES = [
        "password", "pass", "admin", "qwerty", "iloveyou", "welcome",
        "instagram", "insta", "love", "loveyou", "baby",
    ]
    LEET = {
        "a": ["a", "4", "@"],
        "e": ["e", "3"],
        "i": ["i", "1"],
        "o": ["o", "0"],
        "s": ["s", "5", "$"],
        "t": ["t", "7"],
        "b": ["b", "8"],
        "l": ["l", "1"],
    }

    def __init__(self, answers, target_count=18000):
        self.answers = answers or {}
        self.target_count = max(100, int(target_count))
        self._passwords = set()
        self.sources = {
            "osint": 0,
            "interview": 0,
            "combo": 0,
            "common": 0,
        }

    def generate(self):
        self._passwords.clear()
        for k in self.sources:
            self.sources[k] = 0

        tokens = self._collect_tokens()
        years = self._collect_years()
        numbers = self._collect_numbers()

        self._from_tokens(tokens)
        self._token_plus_year(tokens, years)
        self._token_plus_number(tokens, numbers)
        self._token_suffixes(tokens)
        self._name_patterns(tokens, years)
        self._username_patterns(years, numbers)
        self._phone_patterns()
        self._date_patterns()
        self._pair_combos(tokens)
        self._leet_variants(tokens)
        self._light_common(years)
        self._finalize(tokens, years)

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        lines = sorted(self._passwords, key=lambda x: (len(x), x.lower()))
        with open(path, "w", encoding="utf-8") as f:
            for pw in lines:
                f.write(pw + "\n")

    @property
    def count(self):
        return len(self._passwords)

    def report(self):
        return (
            f"Wordlist: {self.count} passwords | "
            f"osint≈{self.sources['osint']} "
            f"interview≈{self.sources['interview']} "
            f"combos≈{self.sources['combo']} "
            f"common≈{self.sources['common']}"
        )

    # ── collectors ──────────────────────────────────────

    def _field(self, *keys):
        for k in keys:
            v = self.answers.get(k)
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                return v
            s = str(v).strip()
            if s:
                return s
        return ""

    def _split_name(self, s):
        if not s:
            return []
        parts = re.split(r"[\s._\-]+", str(s).strip())
        return [p.strip() for p in parts if len(p.strip()) >= 2]

    def _collect_tokens(self):
        raw = []

        for key in ("full_name", "username", "biography", "category"):
            v = self._field(key)
            if isinstance(v, str) and v:
                raw.append(v)
                raw.extend(self._split_name(v))

        for t in self._field("bio_tokens", "osint_tokens") or []:
            raw.append(str(t))

        for p in self._field("user_parts") or []:
            raw.append(str(p))

        interview_keys = [
            "nickname", "partner", "partner_name", "pet", "pet_name",
            "child", "child_name", "mother", "father", "city", "hometown",
            "sport", "favorite_sport", "team", "favorite_team",
            "artist", "favorite_artist", "movie", "favorite_movie",
            "color", "favorite_color", "hobby", "car", "email",
        ]
        for k in interview_keys:
            v = self._field(k)
            if isinstance(v, str) and v:
                raw.append(v)
                raw.extend(self._split_name(v))

        extra = self._field("extra", "extra_keywords")
        if isinstance(extra, str) and extra:
            for kw in re.split(r"[,|]+", extra):
                kw = kw.strip()
                if kw:
                    raw.append(kw)
                    raw.extend(self._split_name(kw))

        junk = {
            "the", "and", "for", "you", "with", "this", "from", "https",
            "http", "www", "com", "instagram", "follow", "like", "bio",
            "null", "none", "true", "false",
        }
        seen = set()
        tokens = []
        for t in raw:
            t = str(t).strip()
            if not t:
                continue
            digits_only = re.sub(r"\D", "", t)
            if len(digits_only) >= 8 and digits_only == re.sub(r"\D", "", t):
                continue
            base = t.lower()
            if base in junk or len(base) < 2 or len(base) > 24:
                continue
            if base not in seen:
                seen.add(base)
                tokens.append(t)
        return tokens[:80]

    def _collect_years(self):
        years = []
        for y in self._field("osint_years", "years") or []:
            years.append(str(y))
        by = self._field("birth_year")
        if by and re.fullmatch(r"19\d{2}|20\d{2}", str(by)):
            years.append(str(by))
            years.append(str(by)[-2:])
        for y in (
            "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027"
        ):
            years.append(y)
        bio = str(self._field("biography") or "")
        years.extend(re.findall(r"\b(19\d{2}|20[0-2]\d)\b", bio))
        out = []
        seen = set()
        for y in years:
            y = str(y)
            if y and y not in seen:
                seen.add(y)
                out.append(y)
        return out[:20]

    def _collect_numbers(self):
        nums = []
        for n in self._field("stat_numbers") or []:
            nums.append(str(n))
        lucky = self._field("number", "favorite_number")
        if lucky:
            d = re.sub(r"\D", "", str(lucky))
            nums.append(d or str(lucky))
        for sfx in self.SUFFIXES:
            if sfx.isdigit():
                nums.append(sfx)
        for k in ("birth_day", "birth_month"):
            v = self._field(k)
            if not v:
                continue
            try:
                iv = int(v)
                nums.append(str(iv).zfill(2))
                nums.append(str(iv))
            except ValueError:
                pass
        return list(dict.fromkeys([n for n in nums if n]))[:40]

    # ── add helper ──────────────────────────────────────

    def _add(self, pw, src="combo"):
        if not isinstance(pw, str):
            return
        pw = pw.strip()
        if 4 <= len(pw) <= 64 and pw not in self._passwords:
            self._passwords.add(pw)
            if src in self.sources:
                self.sources[src] += 1

    def _cases(self, t):
        return {t, t.lower(), t.upper(), t.capitalize()}

    # ── generators ──────────────────────────────────────

    def _from_tokens(self, tokens):
        has_osint = bool(
            self._field("bio_tokens")
            or self._field("full_name")
            or self._field("biography")
        )
        src = "osint" if has_osint else "interview"
        for t in tokens:
            for c in self._cases(t):
                self._add(c, src)

    def _token_plus_year(self, tokens, years):
        for t in tokens[:40]:
            for y in years[:12]:
                for base in (t, t.lower(), t.capitalize()):
                    self._add(f"{base}{y}", "combo")
                    self._add(f"{y}{base}", "combo")
                    self._add(f"{base}@{y}", "combo")
                    self._add(f"{base}_{y}", "combo")

    def _token_plus_number(self, tokens, numbers):
        for t in tokens[:40]:
            for n in numbers[:20]:
                for base in (t.lower(), t.capitalize()):
                    self._add(f"{base}{n}", "combo")
                    self._add(f"{n}{base}", "combo")

    def _token_suffixes(self, tokens):
        for t in tokens[:40]:
            for sfx in self.SUFFIXES[:16]:
                self._add(f"{t.lower()}{sfx}", "combo")
                self._add(f"{t.capitalize()}{sfx}", "combo")

    def _name_patterns(self, tokens, years):
        name = self._field("full_name") or ""
        parts = self._split_name(name)
        if len(parts) >= 2:
            a, b = parts[0], parts[1]
            for sep in ("", ".", "_", "-"):
                self._add(f"{a}{sep}{b}", "osint")
                self._add(f"{a.lower()}{sep}{b.lower()}", "osint")
                self._add(f"{a.capitalize()}{sep}{b.capitalize()}", "osint")
            for y in years[:8]:
                self._add(f"{a.lower()}{b.lower()}{y}", "combo")
                self._add(f"{a.capitalize()}{y}", "combo")
                self._add(f"{b.capitalize()}{y}", "combo")

    def _username_patterns(self, years, numbers):
        u = self._field("username") or self.answers.get("username", "")
        if not u:
            return
        self._add(u, "osint")
        self._add(u + "123", "osint")
        self._add(u + "1234", "osint")
        self._add(u + "!", "osint")
        parts = re.split(r"[._\-]+", str(u))
        for p in parts:
            if len(p) < 3:
                continue
            for y in years[:8]:
                self._add(f"{p}{y}", "osint")
            for n in numbers[:10]:
                self._add(f"{p}{n}", "osint")
            for sfx in ("123", "1234", "!", "@", "01"):
                self._add(f"{p}{sfx}", "osint")
        for y in years[:6]:
            self._add(str(u) + str(y), "osint")

    def _phone_patterns(self):
        phones = list(self._field("phones", "osint_phones") or [])
        p = self._field("phone")
        if p:
            phones.append(p)
        for ph in phones:
            digits = re.sub(r"\D", "", str(ph))
            if len(digits) < 8:
                continue
            self._add(digits, "osint")
            self._add(digits[-8:], "osint")
            self._add(digits[-6:], "osint")
            self._add(digits[-4:], "osint")
            if digits.startswith("212") and len(digits) >= 12:
                self._add("0" + digits[3:], "osint")

    def _date_patterns(self):
        y = self._field("birth_year")
        m = self._field("birth_month")
        d = self._field("birth_day")
        try:
            if y and m and d:
                yi, mi, di = int(y), int(m), int(d)
                self._add(f"{di:02d}{mi:02d}{yi}", "interview")
                self._add(f"{yi}{mi:02d}{di:02d}", "interview")
                self._add(f"{di:02d}{mi:02d}{str(yi)[-2:]}", "interview")
                self._add(f"{mi:02d}{di:02d}{yi}", "interview")
            if y and m:
                self._add(f"{int(m):02d}{y}", "interview")
            if y:
                self._add(str(y), "interview")
                self._add(str(y)[-2:], "interview")
        except ValueError:
            pass

    def _pair_combos(self, tokens):
        sample = tokens[:18]
        for a, b in itertools.permutations(sample, 2):
            if a.lower() == b.lower():
                continue
            for sep in ("", ".", "_"):
                self._add(f"{a.lower()}{sep}{b.lower()}", "combo")
            if len(self._passwords) >= self.target_count * 3:
                return

    def _leet_variants(self, tokens):
        for t in tokens[:12]:
            tl = t.lower()
            chars = [self.LEET.get(c, [c]) for c in tl]
            n = 0
            for combo in itertools.product(*chars):
                pw = "".join(combo)
                if pw != tl:
                    self._add(pw, "combo")
                    n += 1
                    if n >= 40:
                        break

    def _light_common(self, years):
        u = (self._field("username") or "user").lower()
        for base in self.COMMON_BASES:
            base = base.strip()
            if len(base) < 4:
                continue
            self._add(base, "common")
            for y in years[:4]:
                self._add(base + y, "common")
            self._add(base + "123", "common")
        for frag in ("love", "baby", "king", "queen", "pro", "real"):
            self._add(u + frag, "common")
            self._add(frag + u, "common")

    def _finalize(self, tokens, years):
        final = [p for p in self._passwords if 4 <= len(p) <= 64]
        u = (self._field("username") or "").lower()
        name_parts = [
            p.lower() for p in self._split_name(self._field("full_name") or "")
        ]

        def score(pw):
            pl = pw.lower()
            s = 0
            if u and u in pl:
                s += 5
            for np in name_parts:
                if np and np in pl:
                    s += 4
            if any(ch.isdigit() for ch in pw):
                s += 1
            return (-s, len(pw))

        final = sorted(set(final), key=score)

        if len(final) > self.target_count:
            final = final[: self.target_count]
        elif len(final) < self.target_count:
            need = self.target_count - len(final)
            extra = []
            tlist = tokens[:20] or [u or "pass"]
            ylist = years[:10] or ["123"]
            sfxs = ["", "!", "@", "1", "12", "123", "1234", "01"]
            for t, y, sfx in itertools.product(tlist, ylist, sfxs):
                extra.append(f"{str(t).lower()}{y}{sfx}")
                extra.append(f"{str(t).capitalize()}{y}{sfx}")
                if len(extra) >= need * 2:
                    break
            for e in extra:
                if 4 <= len(e) <= 64:
                    final.append(e)
                if len(final) >= self.target_count:
                    break
            final = list(dict.fromkeys(final))[: self.target_count]

        self._passwords = set(final)

    def get_list(self):
        return sorted(self._passwords)
