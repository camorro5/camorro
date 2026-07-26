#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted dictionary from YOUR intel. 18000 passwords."""
import os
import re
import itertools

try:
    from .banner import info, ok, C
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    class C: R=G=Y=C=M=W=E=""


class WordlistAI:
    SUFFIXES = [
        "123","1234","12345","123456","12345678","1234567890",
        "1","12","01","00","007","111","000","69","420",
        "!","@","#","$","!!","!@",
        "2019","2020","2021","2022","2023","2024","2025","2026","2027",
        "1990","1995","1998","1999","2000","2001","2002","2003","2004",
    ]
    SPECIALS = ["", "!", "@", "#", "$", "*", ".", "_", "-", "!!"]
    COMMON = [
        "password","pass","admin","qwerty","iloveyou","welcome",
        "instagram","insta","love","loveyou","baby","king","queen",
        "prince","princess","football","soccer","messi","ronaldo",
        "hello","hallo","maroc","morocco","dima","maghrib",
    ]
    LEET_MAP = {
        "a": ["a","4","@"], "e": ["e","3"], "i": ["i","1"],
        "o": ["o","0"], "s": ["s","5","$"],
        "t": ["t","7"], "b": ["b","8"], "l": ["l","1"], "g": ["g","9"],
    }

    def __init__(self, answers, target_count=18000):
        self.answers = answers or {}
        self.target_count = max(100, int(target_count))
        self.passwords = set()
        self.stats = {"intel": 0, "combo": 0, "leet": 0, "common": 0, "pad": 0}

    def generate(self):
        self.passwords.clear()
        tokens = self._intel_tokens()
        years = self._years()
        numbers = self._numbers()

        self._add_known_passwords()
        self._from_tokens(tokens)
        self._dates()
        self._phones()
        self._name_patterns(tokens, years)
        self._username_patterns(years, numbers)
        self._token_year(tokens, years)
        self._token_number(tokens, numbers)
        self._token_suffix(tokens)
        self._pair_combos(tokens)
        self._leet(tokens)
        self._light_common(years)
        self._finalize(tokens, years, numbers)
        return self

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for pw in sorted(self.passwords, key=lambda x: (len(x), x.lower())):
                f.write(pw + "\n")

    @property
    def count(self):
        return len(self.passwords)

    def report(self):
        return (f"Dictionary: {self.count} | "
                f"intel={self.stats['intel']} combo={self.stats['combo']} "
                f"leet={self.stats['leet']} common={self.stats['common']} pad={self.stats['pad']}")

    # ── HELPERS ──

    def _g(self, *keys):
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

    def _split(self, s):
        if not s:
            return []
        return [p.strip() for p in re.split(r"[\s._\-,;|/]+", str(s).strip()) if len(p.strip()) >= 2]

    def _add(self, pw, src="combo"):
        if not isinstance(pw, str):
            return
        pw = pw.strip()
        if not (4 <= len(pw) <= 64) or pw in self.passwords:
            return
        self.passwords.add(pw)
        if src in self.stats:
            self.stats[src] += 1

    def _cases(self, t):
        t = str(t)
        return {t, t.lower(), t.upper(), t.capitalize()}

    # ── INTEL ──

    def _intel_tokens(self):
        raw = []
        for k in ("full_name","nickname","username","username_alt","partner","child",
                  "mother","father","pet","best_friend","city","hometown","country",
                  "school","work","sport","team","artist","movie","color","hobby","car",
                  "email","category","biography"):
            v = self._g(k)
            if isinstance(v, str) and v:
                raw.append(v)
                raw.extend(self._split(v))
        for t in self._g("bio_tokens","osint_tokens") or []:
            raw.append(str(t))
        for p in self._g("user_parts") or []:
            raw.append(str(p))
        extra = self._g("extra")
        if isinstance(extra, str) and extra:
            for kw in re.split(r"[,|]+", extra):
                kw = kw.strip()
                if kw:
                    raw.append(kw)
                    raw.extend(self._split(kw))
        junk = {"the","and","for","you","with","this","from","https","http","www",
                "com","net","org","instagram","follow","like","bio","null","none",
                "true","false","n-a"}
        out, seen = [], set()
        for t in raw:
            t = str(t).strip()
            if not t:
                continue
            digits = re.sub(r"\D", "", t)
            if digits and len(digits) >= 2:
                out.append(digits)
            t = t.lower()
            if t in junk or len(t) < 2 or len(t) > 32:
                continue
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def _years(self):
        yrs = set()
        for s in self._g("birth_year","osint_years") or []:
            try:
                yrs.add(int(str(s)[:4]))
            except Exception:
                pass
        by = self._g("birth_year")
        if isinstance(by, str) and by.isdigit():
            yrs.add(int(by))
        for y in (self._g("years") or []):
            try:
                yrs.add(int(str(y)[:4]))
            except Exception:
                pass
        return sorted([y for y in yrs if 1900 <= y <= 2030])

    def _numbers(self):
        nums = set()
        for s in self._g("stat_numbers","number") or []:
            try:
                nums.add(int(s))
            except Exception:
                pass
        phone = self._g("phone")
        if isinstance(phone, str) and phone:
            d = re.sub(r"\D", "", phone)
            if len(d) >= 4:
                nums.add(int(d[-4:]))
            if len(d) >= 2:
                nums.add(int(d[-2:]))
            if len(d) >= 6:
                nums.add(int(d[-6:]))
        return sorted([n for n in nums if 0 <= n <= 999999])

    # ── GENERATORS ──

    def _add_known_passwords(self):
        kp = self._g("known_passwords")
        if isinstance(kp, str) and kp:
            for pw in re.split(r"[,|]+", kp):
                pw = pw.strip()
                if pw:
                    self._add(pw, "intel")
                    self._add(pw.lower(), "intel")
                    self._add(pw.upper(), "intel")

    def _from_tokens(self, tokens):
        for t in tokens:
            for c in self._cases(t):
                self._add(c, "intel")
                self._add(c + "123", "intel")
                self._add(c + "1234", "intel")
                self._add("123" + c, "intel")

    def _dates(self):
        for v in (self._g("birth_day","birth_month") or ""):
            try:
                d = int(v)
                if 1 <= d <= 31:
                    d2 = f"{d:02d}"
                    self._add(d2, "intel")
                    for s in self.SUFFIXES:
                        if s.isdigit():
                            self._add(d2 + s, "combo")
            except Exception:
                pass
        for y in self._years():
            sy = str(y)
            self._add(sy, "intel")
            self._add(sy[2:], "intel")
            by = self._g("birth_year")
            if isinstance(by, str) and by.isdigit():
                self._add(by, "intel")
                self._add(by[2:], "intel")

    def _phones(self):
        phone = self._g("phone")
        for p in (self._g("osint_phones") or []) + ([phone] if phone else []):
            p = str(p)
            d = re.sub(r"\D", "", p)
            for n in range(1, len(d) + 1):
                s = d[-n:]
                if len(s) >= 4:
                    self._add(s, "intel")

    def _name_patterns(self, tokens, years):
        for t in tokens:
            t = str(t)
            if not t.isalpha() or len(t) < 3:
                continue
            first = t[0].upper() + t[1:].lower()
            self._add(first, "combo")
            for y in years:
                sy = str(y)
                self._add(first + sy, "combo")
                self._add(first + sy[2:], "combo")
                self._add(first.lower() + sy, "combo")
                self._add(first.lower() + sy[2:], "combo")
            for n in [1, 12, 123, 1234]:
                self._add(first + str(n), "combo")
                self._add(first.lower() + str(n), "combo")

    def _username_patterns(self, years, numbers):
        un = self._g("username")
        if not un:
            return
        un = str(un).strip().lstrip("@")
        for num in numbers[:10]:
            sn = str(num)
            self._add(un + sn, "combo")
            self._add(sn + un, "combo")
        for y in years:
            sy = str(y)
            self._add(un + sy, "combo")
            self._add(un + sy[2:], "combo")

    def _token_year(self, tokens, years):
        for t in tokens:
            t = str(t)
            for y in years:
                sy = str(y)
                self._add(t + sy, "combo")
                self._add(sy + t, "combo")
                self._add(t + sy[2:], "combo")
                self._add(sy[2:] + t, "combo")

    def _token_number(self, tokens, numbers):
        for t in tokens:
            t = str(t)
            for n in numbers[:15]:
                sn = str(n)
                self._add(t + sn, "combo")
                self._add(sn + t, "combo")

    def _token_suffix(self, tokens):
        for t in tokens:
            t = str(t)
            for s in self.SUFFIXES:
                self._add(t + s, "combo")
                self._add(s + t, "combo")

    def _pair_combos(self, tokens):
        limited = [str(t) for t in tokens if str(t).isalpha() and len(str(t)) >= 2][:15]
        for a, b in itertools.combinations(limited, 2):
            if a == b:
                continue
            self._add(a + b, "combo")
            self._add(b + a, "combo")
            for s in self.SPECIALS:
                self._add(a + s + b, "combo")
                self._add(b + s + a, "combo")

    def _leet(self, tokens):
        for t in tokens:
            t = str(t)
            if not t.isalpha() or len(t) < 3:
                continue
            chars = []
            for c in t.lower():
                opts = self.LEET_MAP.get(c, [c])
                chars.append(opts)
            for combo in itertools.product(*chars):
                leet = "".join(combo)
                if leet != t and leet != t.lower():
                    self._add(leet, "leet")
                    for s in self.SUFFIXES[:10]:
                        self._add(leet + s, "leet")

    def _light_common(self, years):
        for c in self.COMMON:
            self._add(c, "common")
            self._add(c.capitalize(), "common")
            for y in years:
                sy = str(y)
                self._add(c + sy, "common")
                self._add(c + sy[2:], "common")
            for s in self.SUFFIXES[:8]:
                self._add(c + s, "common")

    def _finalize(self, tokens, years, numbers):
        """Pad to reach target_count if needed."""
        while self.count < self.target_count:
            for t in (tokens + [self._g("username") or ""])[:10]:
                t = str(t)
                if not t:
                    continue
                for s in self.SUFFIXES:
                    if self.count >= self.target_count:
                        break
                    self._add(t + s, "pad")
                    self._add(s + t, "pad")
                    self._add(t.capitalize() + s, "pad")
                if self.count >= self.target_count:
                    break

            for y in years:
                sy = str(y)
                for s in self.SUFFIXES:
                    if self.count >= self.target_count:
                        break
                    self._add(sy + s, "pad")
                    self._add(sy[2:] + s, "pad")
                if self.count >= self.target_count:
                    break

            for n in numbers:
                sn = str(n)
                for s in self.SUFFIXES[:5]:
                    if self.count >= self.target_count:
                        break
                    self._add(sn + s, "pad")
                if self.count >= self.target_count:
                    break

            if self.count >= self.target_count:
                break

        info(f"Dictionary generated: {self.count} passwords")

    @staticmethod
    def load(path):
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
