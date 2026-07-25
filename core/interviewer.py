#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interactive intelligence questionnaire for Camoro AI wordlist."""

import json
import os
import re

from core.banner import Colors, info, success, warn


class Interviewer:
    QUESTIONS = [
        ("full_name", "Full real name (الاسم الكامل)"),
        ("first_name", "First name (الاسم الأول)"),
        ("last_name", "Last name / family (اللقب)"),
        ("nickname", "Nickname / alias (لقب / كنية)"),
        ("birth_day", "Birth day DD (يوم الميلاد 01-31)"),
        ("birth_month", "Birth month MM (شهر الميلاد 01-12)"),
        ("birth_year", "Birth year YYYY (سنة الميلاد)"),
        ("phone", "Phone number (رقم الهاتف)"),
        ("phone_last4", "Last 4 digits of phone"),
        ("city", "City (المدينة)"),
        ("country", "Country (البلد)"),
        ("school", "School / university (مدرسة / جامعة)"),
        ("job", "Job / company (العمل)"),
        ("partner", "Partner name (اسم الشريك/ة)"),
        ("child", "Child name (اسم الابن/الابنة)"),
        ("pet", "Pet name (اسم الحيوان الأليف)"),
        ("team", "Favorite team / club (فريق مفضل)"),
        ("hobby", "Hobby keyword (هوايات)"),
        ("old_username", "Old username (يوزر قديم)"),
        ("email_local", "Email local-part before @ (مثلاً ahmed92)"),
        ("known_passwords", "Known/old passwords comma-separated"),
        ("custom_words", "Extra custom words comma-separated"),
        ("arabic_words", "Arabic words they might use comma-separated"),
        ("symbols_pref", "Preferred symbols order e.g. @#!_ (empty=default)"),
    ]

    def __init__(self, username, osint_hints=None, output_dir="output"):
        self.username = username
        self.osint_hints = osint_hints or {}
        self.output_dir = output_dir
        self.answers = {}

    def run(self):
        print(
            f"\n{Colors.BOLD}{Colors.OKCYAN}"
            f"┌──────────────────────────────────────────────────┐\n"
            f"│  CAMORO INTELLIGENCE INTERVIEWER                 │\n"
            f"│  Answer what you know — press ENTER to skip      │\n"
            f"└──────────────────────────────────────────────────┘"
            f"{Colors.ENDC}\n"
        )
        if self.osint_hints.get("full_name"):
            info("OSINT suggests full name: %s" % self.osint_hints["full_name"])
        if self.osint_hints.get("years"):
            info("OSINT years found: %s" % ", ".join(self.osint_hints["years"]))

        for key, prompt in self.QUESTIONS:
            default = self._default_for(key)
            suffix = " [%s]" % default if default else ""
            try:
                val = input("%s[?]%s %s%s: " % (Colors.YELLOW, Colors.ENDC, prompt, suffix)).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                warn("Interview interrupted")
                break
            if not val and default:
                val = default
            if val:
                self.answers[key] = val

        self.answers["username"] = self.username
        self.answers["osint_tokens"] = self.osint_hints.get("bio_tokens", [])
        self.answers["osint_years"] = self.osint_hints.get("years", [])
        self.answers["osint_phones"] = self.osint_hints.get("phones", [])
        path = self._save()
        success("Interview data saved → %s" % path)
        return self.answers

    def _default_for(self, key):
        h = self.osint_hints
        if key == "full_name":
            return h.get("full_name", "")
        if key == "first_name":
            fn = (h.get("full_name") or "").split()
            return fn[0] if fn else ""
        if key == "last_name":
            fn = (h.get("full_name") or "").split()
            return fn[-1] if len(fn) > 1 else ""
        if key == "birth_year" and h.get("years"):
            return h["years"][0]
        if key == "phone" and h.get("phones"):
            return h["phones"][0]
        if key == "phone_last4" and h.get("phones"):
            digits = re.sub(r"\D", "", h["phones"][0])
            return digits[-4:] if len(digits) >= 4 else ""
        if key == "old_username":
            return self.username
        return ""

    def _save(self):
        base = os.path.join(self.output_dir, self.username)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, "interview.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.answers, f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
