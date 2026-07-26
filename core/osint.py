#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSINT — Instagram profile intelligence (real data only)."""

import json
import os
import re
import time
import requests
from .banner import info, ok, warn, err, C

try:
    from .session import Session
except Exception:
    Session = None


class OSINT:
    """
    Multi-method public profile gatherer.
    Only reports SUCCESS when real fields are present
    (name / bio / followers / posts), not bare username.
    """

    APP_ID = "936619743392459"
    UA = (
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Mobile Safari/537.36"
    )

    def __init__(self, username, output_dir="output", proxy=None, sessionid=None):
        self.username = username.strip().lstrip("@")
        self.output_dir = output_dir
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self.sessionid = (sessionid or os.environ.get("IG_SESSIONID") or "").strip()
        self.data = {}
        self.fail_reason = ""
        self._session = requests.Session()
        self._session.headers.update(self._base_headers())
        if self.proxy:
            self._session.proxies.update(self.proxy)

    # ─────────────────────────────────────────────
    def scrape(self):
        info(f"Scanning @{self.username}...")

        # 1) warm cookies from homepage
        self._warm()

        # optional real session cookie (best chance)
        if self.sessionid:
            self._session.cookies.set(
                "sessionid", self.sessionid, domain=".instagram.com"
            )
            info("Using sessionid cookie")

        methods = [
            ("web_profile_info", self._via_web_profile_info),
            ("html_meta", self._via_html_page),
            ("i.instagram", self._via_i_instagram),
        ]

        for name, fn in methods:
            try:
                info(f"Trying method: {name}")
                if fn() and self._is_real_data():
                    self._save()
                    ok(f"OSINT OK — @{self.data.get('username', self.username)}")
                    self.print_summary()
                    return self.data
            except Exception as e:
                self.fail_reason = f"{name}: {e}"
                continue

        # empty / blocked
        self._save_empty()
        self._report_failure()
        return {}

    # ─────────────────────────────────────────────
    def _base_headers(self):
        h = {
            "User-Agent": self.UA,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Origin": "https://www.instagram.com",
            "Referer": f"https://www.instagram.com/{self.username}/",
            "X-IG-App-ID": self.APP_ID,
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive",
        }
        if Session is not None:
            try:
                extra = Session.build_headers()
                if isinstance(extra, dict):
                    # keep our UA / app-id priority
                    for k, v in extra.items():
                        if k.lower() not in ("user-agent", "x-ig-app-id"):
                            h[k] = v
            except Exception:
                pass
        return h

    def _warm(self):
        """Visit homepage + profile shell to get csrftoken / mid / ig_did."""
        try:
            r = self._session.get(
                "https://www.instagram.com/",
                timeout=20,
                allow_redirects=True,
            )
            csrf = self._session.cookies.get("csrftoken") or ""
            if not csrf:
                m = re.search(r'"csrf_token":"([^"]+)"', r.text or "")
                if m:
                    csrf = m.group(1)
                    self._session.cookies.set(
                        "csrftoken", csrf, domain=".instagram.com"
                    )
            if csrf:
                self._session.headers["X-CSRFToken"] = csrf
            # soft hit profile page for more cookies
            self._session.get(
                f"https://www.instagram.com/{self.username}/",
                timeout=20,
                allow_redirects=True,
            )
            time.sleep(0.4)
        except Exception:
            pass

    # ── method 1: official web API ────────────────
    def _via_web_profile_info(self):
        url = (
            "https://www.instagram.com/api/v1/users/web_profile_info/"
            f"?username={self.username}"
        )
        r = self._session.get(url, timeout=25)
        if r.status_code == 404:
            self.fail_reason = "account not found (404)"
            return False
        if r.status_code in (401, 403):
            self.fail_reason = f"blocked/login wall ({r.status_code})"
            return False
        if r.status_code != 200:
            self.fail_reason = f"web_profile_info HTTP {r.status_code}"
            return False
        try:
            raw = r.json()
        except Exception:
            self.fail_reason = "web_profile_info not JSON"
            return False
        user = (raw.get("data") or {}).get("user") or {}
        if not user:
            self.fail_reason = "web_profile_info empty user"
            return False
        self._from_user_obj(user)
        return True

    # ── method 2: HTML + og meta + embedded JSON ──
    def _via_html_page(self):
        url = f"https://www.instagram.com/{self.username}/"
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        r = self._session.get(url, headers=headers, timeout=25)
        if r.status_code == 404:
            self.fail_reason = "account not found (404)"
            return False
        if r.status_code != 200:
            self.fail_reason = f"html HTTP {r.status_code}"
            return False

        html = r.text or ""

        # login wall / challenge
        low = html.lower()
        if "login" in (r.url or "").lower() and "username" not in html[:2000].lower():
            self.fail_reason = "redirected to login"
            # still try meta below

        # 2a embedded JSON blobs
        if self._parse_embedded_json(html):
            return True

        # 2b old ?__a=1 style string inside page
        m = re.search(
            r"window\._sharedData\s*=\s*(\{.+?\});</script>",
            html,
            re.DOTALL,
        )
        if m:
            try:
                shared = json.loads(m.group(1))
                user = (
                    shared.get("entry_data", {})
                    .get("ProfilePage", [{}])[0]
                    .get("graphql", {})
                    .get("user")
                )
                if user:
                    self._from_user_obj(user)
                    return True
            except Exception:
                pass

        m = re.search(
            r"WebProfileInfo|web_profile_info.*?"
            r"(\"data\"\s*:\s*\{\s*\"user\"\s*:\s*\{.+?\}\s*\}\s*\})",
            html,
            re.DOTALL,
        )
        # 2c og tags — often works even with light walls
        if self._parse_og_meta(html):
            return True

        if "login" in low and "csrftoken" in low:
            self.fail_reason = "login wall (no public meta)"
        else:
            self.fail_reason = "html had no profile fields"
        return False

    # ── method 3: mobile web host ─────────────────
    def _via_i_instagram(self):
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={self.username}"
        h = dict(self._session.headers)
        h["User-Agent"] = (
            "Instagram 192.0.0.37.107 Android "
            "(33/13; 420dpi; 1080x2400; samsung; SM-S918B; dm3q; qcom; en_US; 301484483)"
        )
        h["X-IG-App-ID"] = self.APP_ID
        r = self._session.get(url, headers=h, timeout=25)
        if r.status_code != 200:
            self.fail_reason = f"i.instagram HTTP {r.status_code}"
            return False
        try:
            user = (r.json().get("data") or {}).get("user") or {}
        except Exception:
            return False
        if not user:
            return False
        self._from_user_obj(user)
        return True

    # ─────────────────────────────────────────────
    def _from_user_obj(self, user):
        def edge_count(key_edge, key_flat):
            v = user.get(key_edge)
            if isinstance(v, dict):
                return int(v.get("count") or 0)
            v = user.get(key_flat)
            try:
                return int(v or 0)
            except Exception:
                return 0

        self.data = {
            "id": str(user.get("id") or user.get("pk") or ""),
            "username": user.get("username") or self.username,
            "full_name": user.get("full_name") or "",
            "biography": user.get("biography") or user.get("bio") or "",
            "external_url": user.get("external_url") or "",
            "is_private": bool(user.get("is_private", False)),
            "is_verified": bool(user.get("is_verified", False)),
            "is_business": bool(
                user.get("is_business_account") or user.get("is_business") or False
            ),
            "business_category": user.get("business_category_name") or "",
            "category": user.get("category_name") or "",
            "followers": edge_count("edge_followed_by", "follower_count"),
            "following": edge_count("edge_follow", "following_count"),
            "posts": edge_count("edge_owner_to_timeline_media", "media_count"),
            "profile_pic": (
                user.get("profile_pic_url_hd")
                or user.get("profile_pic_url")
                or ""
            ),
        }

    def _parse_embedded_json(self, html):
        """Find user objects inside script tags / RSS-like payloads."""
        # requireRequire or Schedule pattern used by IG web
        patterns = [
            r'"user"\s*:\s*\{"biography":.*?"username":"%s".*?\}' % re.escape(self.username),
            r'{"data":{"user":\{.+?\}\}\s*,\s*"status"',
            r'"props"\s*:\s*\{"pageProps".*?"user"\s*:\s*(\{.+?\})\s*,\s*"status"',
        ]
        # simpler: scan for "username":"<target>" block with followers nearby
        for m in re.finditer(
            r'\{[^{}]*"username"\s*:\s*"%s"[^{}]*\}' % re.escape(self.username),
            html,
        ):
            # expand window around match
            start = max(0, m.start() - 5000)
            end = min(len(html), m.end() + 15000)
            chunk = html[start:end]
            # try pull key fields via regex
            data = {
                "id": _re_str(chunk, r'"id"\s*:\s*"(\d+)"') or "",
                "username": self.username,
                "full_name": _re_json_str(chunk, r'"full_name"\s*:\s*"((?:\\.|[^"\\])*)"'),
                "biography": _re_json_str(chunk, r'"biography"\s*:\s*"((?:\\.|[^"\\])*)"'),
                "external_url": _re_json_str(chunk, r'"external_url"\s*:\s*"((?:\\.|[^"\\])*)"')
                or "",
                "is_private": '"is_private":true' in chunk or '"is_private": true' in chunk,
                "is_verified": '"is_verified":true' in chunk or '"is_verified": true' in chunk,
                "is_business": False,
                "business_category": "",
                "category": "",
                "followers": _re_count(
                    chunk,
                    r'"edge_followed_by"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"follower_count"\s*:\s*(\d+)',
                ),
                "following": _re_count(
                    chunk,
                    r'"edge_follow"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"following_count"\s*:\s*(\d+)',
                ),
                "posts": _re_count(
                    chunk,
                    r'"edge_owner_to_timeline_media"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"media_count"\s*:\s*(\d+)',
                ),
                "profile_pic": "",
            }
            self.data = data
            if self._is_real_data():
                return True

        # __additionalDataLoaded("...", {..})
        m = re.search(
            r"additionalDataLoaded\s*\(\s*[^,]+,\s*(\{.+?\})\s*\)\s*;",
            html,
            re.DOTALL,
        )
        if m:
            try:
                blob = json.loads(m.group(1))
                user = (
                    blob.get("data", {}).get("user")
                    or blob.get("graphql", {}).get("user")
                    or blob.get("user")
                    or {}
                )
                if user:
                    self._from_user_obj(user)
                    return self._is_real_data()
            except Exception:
                pass
        return False

    def _parse_og_meta(self, html):
        """
        og:description examples:
          '1,234 Followers, 56 Following, 78 Posts - See Instagram photos and videos from Jane Doe (@jane)'
          'Jane Doe (@jane) • Instagram photos and videos'
        """
        og_desc = _meta(html, "og:description") or _meta(html, "description")
        og_title = _meta(html, "og:title") or ""

        followers = following = posts = 0
        full_name = ""
        is_private = False

        if og_desc:
            # numbers (handle 1,234 and 1.2M / 1.2K)
            def parse_num(label):
                m = re.search(
                    rf"([\d.,]+)\s*([KkMm])?\s*{label}",
                    og_desc,
                    re.I,
                )
                if not m:
                    return 0
                return _to_int(m.group(1), m.group(2))

            followers = parse_num("Followers")
            following = parse_num("Following")
            posts = parse_num("Posts")

            m = re.search(r"from\s+(.+?)\s*\(@", og_desc)
            if m:
                full_name = m.group(1).strip()
            if "this account is private" in og_desc.lower():
                is_private = True

        if og_title and not full_name:
            # 'Name (@user) • Instagram photos and videos'
            m = re.search(r"^(.+?)\s*\(@", og_title)
            if m:
                full_name = m.group(1).strip()
            elif "(@%s)" % self.username in og_title:
                full_name = og_title.split("(@")[0].strip()

        # secondary: title tag
        if not full_name:
            m = re.search(r"<title>([^<]+)</title>", html, re.I)
            if m:
                t = m.group(1)
                m2 = re.search(r"^(.+?)\s*\(@", t)
                if m2:
                    full_name = m2.group(1).strip()

        # reject pure login pages
        if not followers and not following and not posts and not full_name:
            return False
        if full_name.lower() in ("login", "instagram", "see photos and videos"):
            if not followers:
                return False

        self.data = {
            "id": "",
            "username": self.username,
            "full_name": full_name if full_name.lower() != self.username.lower() else "",
            "biography": "",
            "external_url": "",
            "is_private": is_private,
            "is_verified": False,
            "is_business": False,
            "business_category": "",
            "category": "",
            "followers": followers,
            "following": following,
            "posts": posts,
            "profile_pic": _meta(html, "og:image") or "",
            "source": "og_meta",
        }
        return self._is_real_data()

    # ─────────────────────────────────────────────
    def _is_real_data(self):
        """True only if we learned something beyond the handle."""
        if not self.data:
            return False
        if self.data.get("full_name"):
            return True
        if self.data.get("biography"):
            return True
        if int(self.data.get("followers") or 0) > 0:
            return True
        if int(self.data.get("posts") or 0) > 0:
            return True
        if int(self.data.get("following") or 0) > 0:
            return True
        if self.data.get("id"):
            return True
        return False

    def _save(self):
        path = os.path.join(self.output_dir, self.username)
        os.makedirs(path, exist_ok=True)
        out = os.path.join(path, "osint.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _save_empty(self):
        self.data = {
            "id": "",
            "username": self.username,
            "full_name": "",
            "biography": "",
            "external_url": "",
            "is_private": False,
            "is_verified": False,
            "is_business": False,
            "business_category": "",
            "category": "",
            "followers": 0,
            "following": 0,
            "posts": 0,
            "profile_pic": "",
            "osint_ok": False,
            "fail_reason": self.fail_reason or "no public data",
        }
        self._save()

    def _report_failure(self):
        print()
        err(f"OSINT FAILED for @{self.username}")
        if self.fail_reason:
            warn(f"Reason: {self.fail_reason}")
        print(f"""
{C.Y}Instagram is blocking public scrape from this IP/network.{C.E}

What you can do:
  1) Use a residential/VPN proxy (free lists usually fail)
  2) Export sessionid from a logged-in browser and set it:
       export IG_SESSIONID='YOUR_SESSIONID_HERE'
  3) Continue with INTERVIEW — type name/bio/city yourself;
     wordlist will still be targeted.

Sessionid tip (Chrome / Kiwi on phone):
  Login to instagram.com → DevTools/Cookies → copy 'sessionid'
""")

    def print_summary(self):
        d = self.data or {}
        name = d.get("full_name") or "N/A"
        print(f"""
{C.C}{'─' * 40}{C.E}
  Name       : {name}
  Username   : @{d.get('username', self.username)}
  ID         : {d.get('id') or 'N/A'}
  Private    : {d.get('is_private')}
  Verified   : {d.get('is_verified')}
  Followers  : {d.get('followers', 0):,}
  Following  : {d.get('following', 0):,}
  Posts      : {d.get('posts', 0):,}
  Bio        : {(d.get('biography') or '')[:80] or 'N/A'}
  Category   : {d.get('category') or d.get('business_category') or 'N/A'}
  URL        : {d.get('external_url') or 'N/A'}
{C.C}{'─' * 40}{C.E}
""")

    def get_hints(self):
        """Tokens / numbers for WordlistAI."""
        bio = self.data.get("biography", "") or ""
        name = self.data.get("full_name", "") or ""
        uname = self.data.get("username", self.username) or self.username
        blob = f"{bio} {name}"
        tokens = re.findall(r"[a-zA-Z\u0600-\u06FF0-9_]+", blob.lower())
        tokens = [t for t in tokens if 2 <= len(t) <= 32]
        years = re.findall(r"\b(19\d{2}|20[0-2]\d)\b", blob)
        phones = re.findall(r"(?:\+?\d[\d\s\-]{6,}\d)", bio)
        phones = [re.sub(r"[\s\-]+", "", p) for p in phones]
        stat_nums = []
        for n in (
            self.data.get("followers", 0),
            self.data.get("posts", 0),
            self.data.get("following", 0),
        ):
            try:
                n = int(n)
            except Exception:
                continue
            if 0 < n < 10_000_000:
                s = str(n)
                stat_nums.append(s)
                if len(s) >= 2:
                    stat_nums.append(s[-2:])
                if len(s) >= 4:
                    stat_nums.append(s[-4:])
        user_parts = [p for p in re.split(r"[._\-\s]+", uname) if len(p) >= 2]
        return {
            "username": uname,
            "full_name": name,
            "biography": bio,
            "bio_tokens": list(dict.fromkeys(tokens)),
            "years": list(dict.fromkeys(years)),
            "phones": phones,
            "followers": int(self.data.get("followers") or 0),
            "following": int(self.data.get("following") or 0),
            "posts": int(self.data.get("posts") or 0),
            "user_parts": user_parts,
            "stat_numbers": list(dict.fromkeys(stat_nums)),
            "category": self.data.get("category")
            or self.data.get("business_category")
            or "",
            "external_url": self.data.get("external_url") or "",
            "is_private": bool(self.data.get("is_private")),
            "osint_ok": self._is_real_data(),
        }


# ── helpers ───────────────────────────────────────
def _meta(html, prop):
    m = re.search(
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if m:
        return _html_unescape(m.group(1))
    m = re.search(
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']',
        html,
        re.I,
    )
    if m:
        return _html_unescape(m.group(1))
    return ""


def _html_unescape(s):
    return (
        s.replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def _re_str(text, pattern):
    m = re.search(pattern, text)
    return m.group(1) if m else ""


def _re_json_str(text, pattern):
    m = re.search(pattern, text)
    if not m:
        return ""
    try:
        return json.loads(f'"{m.group(1)}"')
    except Exception:
        return m.group(1).encode().decode("unicode_escape", errors="ignore")


def _re_count(text, *patterns):
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return 0
    return 0


def _to_int(num_str, suffix=None):
    s = (num_str or "0").replace(",", "").strip()
    try:
        val = float(s)
    except Exception:
        return 0
    if suffix:
        su = suffix.upper()
        if su == "K":
            val *= 1_000
        elif su == "M":
            val *= 1_000_000
    return int(val)
