#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted dictionary from YOUR intel (+ optional OSINT)."""

import itertools
import os
import re


class WordlistAI:
    SUFFIXES = [
        "123", "1234", "12345", "123456", "12345678", "1234567890",
        "1", "12", "01", "00", "007", "111", "000", "69", "420",
        "!", "@", "#", "$", "!!", "!@",
        "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027",
        "1990", "1995", "1998", "1999", "2000", "2001", "2002", "2003", "2004",
    ]
    SPECIALS = ["", "!", "@", "#", "$", "*", ".", "_", "-", "!!"]
    COMMON = [
        "password", "pass", "admin", "qwerty", "iloveyou", "welcome",
        "instagram", "insta", "love", "loveyou", "baby", "king", "queen",
        "prince", "princess", "football", "soccer",
    ]
    LEET_MAP = {
        "a": ["a", "4", "@"],
        "e": ["e", "3"],
        "i": ["i", "1"],
        "o": ["o", "0"],
        "s": ["s", "5", "$"],
        "t": ["t", "7"],
        "b": ["b", "8"],
        "l": ["l", "1"],
        "g": ["g", "9"],
    }

    def __init__(self, answers, target_count=18000):
        self.answers = answers or {}
        self.target_count = max(100, int(target_count))
        self.passwords = set()
        self.stats = {
            "intel": 0, "combo": 0, "leet": 0, "common": 0, "pad": 0
        }

    def generate(self):
        self.passwords.clear()
        for k in self.stats:
            self.stats[k] = 0
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

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for pw in sorted(self.passwords, key=lambda x: (len(x), x.lower())):
                f.write(pw + "\n")

    @property
    def count(self):
        return len(self.passwords)

    def report(self):
        return (
            f"Dictionary: {self.count} | "
            f"intel={self.stats['intel']} "
            f"combo={self.stats['combo']} "
            f"leet={self.stats['leet']} "
            f"common={self.stats['common']} "
            f"pad={self.stats['pad']}"
        )

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
        return [
            p.strip()
            for p in re.split(r"[\s._\-,;|/]+", str(s).strip())
            if len(p.strip()) >= 2
        ]

    def _add(self, pw, src="combo"):
        if not isinstance(pw, str):
            return
        pw = pw.strip()
        if not (4 <= len(pw) <= 64):
            return
        if pw in self.passwords:
            return
        self.passwords.add(pw)
        if src in self.stats:
            self.stats[src] += 1

    def _cases(self, t):
        t = str(t)
        return {t, t.lower(), t.upper(), t.capitalize()}

    def _intel_tokens(self):
        raw = []
        for k in (
            "full_name", "nickname", "username", "username_alt",
            "partner", "child", "mother", "father", "pet", "best_friend",
            "city", "hometown", "country", "school", "work",
            "sport", "team", "artist", "movie", "color", "hobby", "car",
            "email", "category", "biography",
        ):
            v = self._g(k)
            if isinstance(v, str) and v:
                raw.append(v)
                raw.extend(self._split(v))
        for t in self._g("bio_tokens", "osint_tokens") or []:
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
        junk = {
            "the", "and", "for", "you", "with", "this", "from", "https",
            "http", "www", "com", "net", "org", "instagram", "follow",
            "like", "bio", "null", "none", "true", "false",
        }
        out, seen = [], set()
        for t in raw:
            t = str(t).strip()
            if not t:
                continue
            digits = re.sub(r"\D", "", t)
            if len(digits) >= 9 and digits == re.sub(r"\D", "", t):
                continue
            b = t.lower()
            if b in junk or not (2 <= len(b) <= 28):
                continue
            if b not in seen:
                seen.add(b)
                out.append(t)
        return out[:120]

    def _years(self):
        years = []
        for y in self._g("osint_years", "years") or []:
            years.append(str(y))
        by = self._g("birth_year")
        if by and re.fullmatch(r"19\d{2}|20\d{2}", str(by)):
            years.append(str(by))
            years.append(str(by)[-2:])
            try:
                yi = int(by)
                for d in (-1, 1, -2, 2):
                    years.append(str(yi + d))
            except ValueError:
                pass
        years += [str(y) for y in range(2016, 2028)]
        years += [
            "1990", "1991", "1992", "1993", "1994", "1995",
            "1996", "1997", "1998", "1999", "2000", "2001",
            "2002", "2003", "2004", "2005",
        ]
        bio = str(self._g("biography") or "")
        years += re.findall(r"\b(19\d{2}|20[0-2]\d)\b", bio)
        return list(dict.fromkeys([str(y) for y in years if y]))[:40]

    def _numbers(self):
        nums = [str(x) for x in (self._g("stat_numbers") or [])]
        lucky = self._g("number")
        if lucky:
            d = re.sub(r"\D", "", str(lucky))
            nums.append(d or str(lucky))
        for s in self.SUFFIXES:
            if s.isdigit():
                nums.append(s)
        for k in ("birth_day", "birth_month"):
            v = self._g(k)
            if not v:
                continue
            try:
                iv = int(v)
                nums += [str(iv), f"{iv:02d}"]
            except ValueError:
                pass
        return list(dict.fromkeys([n for n in nums if n]))[:60]

    def _add_known_passwords(self):
        raw = self._g("known_passwords")
        if not raw:
            return
        for p in re.split(r"[,|]+", str(raw)):
            p = p.strip()
            if p:
                self._add(p, "intel")
                for s in ("", "1", "12", "123", "!", "@"):
                    self._add(p + s, "intel")

    def _from_tokens(self, tokens):
        for t in tokens:
            for c in self._cases(t):
                self._add(c, "intel")

    def _dates(self):
        y = self._g("birth_year")
        m = self._g("birth_month")
        d = self._g("birth_day")
        try:
            if y and m and d:
                yi, mi, di = int(y), int(m), int(d)
                for p in (
                    f"{di:02d}{mi:02d}{yi}",
                    f"{yi}{mi:02d}{di:02d}",
                    f"{di:02d}{mi:02d}{str(yi)[-2:]}",
                    f"{mi:02d}{di:02d}{yi}",
                    f"{di:02d}{mi:02d}",
                    f"{mi:02d}{di:02d}",
                    f"{di}{mi}{yi}",
                    f"{yi}",
                    f"{str(yi)[-2:]}",
                ):
                    self._add(p, "intel")
            elif y:
                self._add(str(y), "intel")
                self._add(str(y)[-2:], "intel")
            if y and m:
                self._add(f"{int(m):02d}{y}", "intel")
                self._add(f"{y}{int(m):02d}", "intel")
        except ValueError:
            pass

    def _phones(self):
        phones = list(self._g("phones", "osint_phones") or [])
        if self._g("phone"):
            phones.append(self._g("phone"))
        for ph in phones:
            digits = re.sub(r"\D", "", str(ph))
            if len(digits) < 8:
                continue
            for piece in (
                digits, digits[-10:], digits[-9:], digits[-8:],
                digits[-6:], digits[-4:],
            ):
                self._add(piece, "intel")
            if digits.startswith("212") and len(digits) >= 12:
                self._add("0" + digits[3:], "intel")
            if digits.startswith("0") and len(digits) >= 9:
                self._add(digits[1:], "intel")

    def _name_patterns(self, tokens, years):
        name = self._g("full_name") or ""
        parts = self._split(name)
        if len(parts) >= 2:
            a, b = parts[0], parts[1]
            for sep in ("", ".", "_", "-", "@"):
                self._add(f"{a}{sep}{b}", "intel")
                self._add(f"{a.lower()}{sep}{b.lower()}", "intel")
                self._add(f"{a.capitalize()}{sep}{b.capitalize()}", "intel")
                self._add(f"{b}{sep}{a}", "combo")
            for y in years[:12]:
                self._add(f"{a.lower()}{b.lower()}{y}", "combo")
                self._add(f"{a.capitalize()}{b.capitalize()}{y}", "combo")
                self._add(f"{a.lower()}{y}", "combo")
                self._add(f"{b.lower()}{y}", "combo")
                self._add(f"{a.capitalize()}{y}", "combo")

        key_people = []
        for k in ("nickname", "partner", "pet", "child", "city", "team"):
            v = self._g(k)
            if v:
                key_people.extend(self._split(v)[:2] or [v])
        base = parts[:1] if parts else []
        nick = self._g("nickname")
        if nick:
            base.append(nick)
        for p1 in base[:3]:
            for p2 in key_people[:8]:
                if str(p1).lower() == str(p2).lower():
                    continue
                for sep in ("", "_", ".", "@"):
                    self._add(
                        f"{str(p1).lower()}{sep}{str(p2).lower()}", "combo"
                    )
                for y in years[:6]:
                    self._add(
                        f"{str(p1).lower()}{str(p2).lower()}{y}", "combo"
                    )

    def _username_patterns(self, years, numbers):
        u = self._g("username") or self.answers.get("username", "")
        alts = self._split(self._g("username_alt") or "")
        for u in [u] + alts:
            if not u:
                continue
            u = str(u)
            self._add(u, "intel")
            for s in ("123", "1234", "12345", "!", "@", "01", "007"):
                self._add(u + s, "intel")
            for y in years[:10]:
                self._add(u + str(y), "intel")
            for p in re.split(r"[._\-]+", u):
                if len(p) < 3:
                    continue
                self._add(p, "intel")
                for y in years[:10]:
                    self._add(f"{p}{y}", "combo")
                for n in numbers[:12]:
                    self._add(f"{p}{n}", "combo")
                for s in ("123", "1234", "!", "@"):
                    self._add(f"{p}{s}", "combo")

    def _token_year(self, tokens, years):
        for t in tokens[:60]:
            for y in years[:14]:
                for b in (t, t.lower(), t.capitalize()):
                    self._add(f"{b}{y}", "combo")
                    self._add(f"{y}{b}", "combo")
                    self._add(f"{b}@{y}", "combo")
                    self._add(f"{b}_{y}", "combo")
                    self._add(f"{b}.{y}", "combo")

    def _token_number(self, tokens, numbers):
        for t in tokens[:60]:
            for n in numbers[:25]:
                for b in (t.lower(), t.capitalize()):
                    self._add(f"{b}{n}", "combo")
                    self._add(f"{n}{b}", "combo")

    def _token_suffix(self, tokens):
        for t in tokens[:60]:
            for sfx in self.SUFFIXES:
                self._add(f"{t.lower()}{sfx}", "combo")
                self._add(f"{t.capitalize()}{sfx}", "combo")

    def _pair_combos(self, tokens):
        sample = tokens[:22]
        for a, b in itertools.permutations(sample, 2):
            if a.lower() == b.lower():
                continue
            for sep in ("", ".", "_", "@"):
                self._add(f"{a.lower()}{sep}{b.lower()}", "combo")
            if len(self.passwords) > self.target_count * 2:
                return

    def _leet(self, tokens):
        prefer = []
        for k in ("nickname", "full_name", "partner", "city", "pet"):
            v = self._g(k)
            if v:
                prefer.extend(self._split(v)[:2] or [v])
        pool = list(dict.fromkeys(prefer + tokens[:12]))[:18]
        for t in pool:
            tl = str(t).lower()
            if len(tl) < 3:
                continue
            chars = [self.LEET_MAP.get(c, [c]) for c in tl]
            n = 0
            for combo in itertools.product(*chars):
                pw = "".join(combo)
                if pw != tl:
                    self._add(pw, "leet")
                    self._add(pw + "123", "leet")
                    n += 1
                    if n >= 50:
                        break

    def _light_common(self, years):
        u = (self._g("username") or "user").lower()
        for base in self.COMMON:
            self._add(base, "common")
            for y in years[:5]:
                self._add(base + y, "common")
            self._add(base + "123", "common")
        for frag in (
            "love", "baby", "king", "queen", "pro", "real", "officiel", "maroc"
        ):
            self._add(u + frag, "common")
            self._add(frag + u, "common")

    def _finalize(self, tokens, years, numbers):
        final = [p for p in self.passwords if 4 <= len(p) <= 64]
        u = (self._g("username") or "").lower()
        name_parts = [
            p.lower() for p in self._split(self._g("full_name") or "")
        ]
        nick = (self._g("nickname") or "").lower()
        city = (self._g("city") or "").lower()

        def score(pw):
            pl = pw.lower()
            s = 0
            if u and u in pl:
                s += 6
            if nick and nick in pl:
                s += 5
            for np in name_parts:
                if np and np in pl:
                    s += 4
            if city and city in pl:
                s += 3
            if any(ch.isdigit() for ch in pw):
                s += 1
            if any(ch in "!@#$_." for ch in pw):
                s += 1
            return (-s, len(pw))

        final = sorted(set(final), key=score)
        if len(final) > self.target_count:
            self.passwords = set(final[: self.target_count])
            return

        need = self.target_count - len(final)
        if need <= 0:
            self.passwords = set(final)
            return

        tlist = tokens[:30] or [u or "pass"]
        ylist = years[:20] or [str(y) for y in range(1995, 2028)]
        nlist = numbers[:20] or ["123", "1234", "1", "01"]
        seen = set(final)
        extra = []
        for t, y, n, sp in itertools.product(
            tlist, ylist, nlist[:10], self.SPECIALS
        ):
            cands = [
                f"{str(t).lower()}{y}{sp}",
                f"{str(t).capitalize()}{y}{sp}",
                f"{str(t).lower()}{n}{sp}",
                f"{str(t).capitalize()}{n}{sp}",
                f"{y}{str(t).lower()}{sp}",
                f"{str(t).lower()}_{y}",
                f"{str(t).lower()}@{n}",
                f"{str(t).lower()}{y}{n}",
            ]
            for v in cands:
                if 4 <= len(v) <= 64 and v not in seen:
                    seen.add(v)
                    extra.append(v)
                    self.stats["pad"] += 1
                    if len(extra) >= need:
                        break
            if len(extra) >= need:
                break
        final.extend(extra)
        self.passwords = set(final[: self.target_count])
