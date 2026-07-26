#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interview — YOU give intel → dictionary."""

import json
import os
from .banner import info, ok, ask, C


class Interviewer:
    def __init__(self, username, hints=None, output_dir="output"):
        self.username = username.strip().lstrip("@")
        self.hints = hints or {}
        self.output_dir = output_dir
        self.answers = {}

    def run(self):
        print(f"""
{C.C}╔══════════════════════════════════════════════════╗
║   أنت تعطي المعلومات → الأداة تولّد القاموس      ║
║   ENTER = تخطّي أي سؤال                          ║
╚══════════════════════════════════════════════════╝{C.E}
""")
        if self.hints.get("full_name"):
            info(f"OSINT name: {self.hints.get('full_name')}")
        if self.hints.get("biography"):
            info(f"OSINT bio : {str(self.hints.get('biography'))[:90]}")
        if self.hints.get("followers"):
            info(
                f"OSINT     : {self.hints.get('followers')} followers | "
                f"{self.hints.get('posts', 0)} posts"
            )

        a = self.answers
        a["username"] = self.username

        print(f"\n{C.W}── الهوية ──{C.E}")
        a["full_name"] = ask(
            "Full name / الاسم الكامل", self.hints.get("full_name", "")
        )
        a["nickname"] = ask("Nickname / الكنية")
        a["username_alt"] = ask("Other usernames comma / يوزرات أخرى")

        print(f"\n{C.W}── التاريخ ──{C.E}")
        a["birth_year"] = ask("Birth year YYYY / عام الازدياد")
        a["birth_month"] = ask("Birth month 1-12")
        a["birth_day"] = ask("Birth day 1-31")

        print(f"\n{C.W}── العائلة ──{C.E}")
        a["partner"] = ask("Partner / الشريك-ة")
        a["child"] = ask("Child / الولد")
        a["mother"] = ask("Mother / الأم")
        a["father"] = ask("Father / الأب")
        a["pet"] = ask("Pet / حيوان")
        a["best_friend"] = ask("Best friend / الصاحب")

        print(f"\n{C.W}── المكان ──{C.E}")
        a["city"] = ask("City / المدينة")
        a["hometown"] = ask("Hometown / المدينة الأصلية")
        a["country"] = ask("Country / البلد")
        a["school"] = ask("School / المدرسة")
        a["work"] = ask("Work / العمل")

        print(f"\n{C.W}── اهتمامات ──{C.E}")
        a["sport"] = ask("Sport")
        a["team"] = ask("Team")
        a["artist"] = ask("Artist")
        a["movie"] = ask("Movie")
        a["color"] = ask("Color")
        a["hobby"] = ask("Hobby")
        a["car"] = ask("Car")
        a["number"] = ask("Lucky number")

        print(f"\n{C.W}── تواصل ──{C.E}")
        a["phone"] = ask("Phone / التيليفون")
        a["email"] = ask("Email")
        a["extra"] = ask("Extra keywords comma / كلمات زيادة")
        a["known_passwords"] = ask(
            "Old known passwords comma / كلمات سر قديمة معروفة"
        )

        a["biography"] = self.hints.get("biography", "")
        a["bio_tokens"] = list(self.hints.get("bio_tokens", []) or [])
        a["osint_tokens"] = list(self.hints.get("bio_tokens", []) or [])
        a["osint_years"] = list(self.hints.get("years", []) or [])
        a["years"] = list(self.hints.get("years", []) or [])
        a["phones"] = list(self.hints.get("phones", []) or [])
        a["osint_phones"] = list(self.hints.get("phones", []) or [])
        a["user_parts"] = list(self.hints.get("user_parts", []) or [])
        a["stat_numbers"] = list(self.hints.get("stat_numbers", []) or [])
        a["followers"] = self.hints.get("followers", 0)
        a["following"] = self.hints.get("following", 0)
        a["posts"] = self.hints.get("posts", 0)
        a["category"] = self.hints.get("category", "")
        a["external_url"] = self.hints.get("external_url", "")

        if not a.get("full_name"):
            a["full_name"] = self.hints.get("full_name", "")
        if a.get("phone"):
            a["phones"] = list(a.get("phones") or []) + [a["phone"]]

        path = os.path.join(
            self.output_dir, self.username, "interview.json"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(a, f, indent=2, ensure_ascii=False)

        filled = sum(
            1
            for k, v in a.items()
            if k != "username" and v not in (None, "", 0, [], {})
        )
        ok(f"Interview saved → {path}")
        info(f"Fields filled: {filled}")
        return a
