#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSINT — 6 methods: web_profile_info, i.instagram, GraphQL, HTML, RSC, OG meta."""
import json
import os
import re
import time
import random
import uuid
import requests

try:
    from .banner import info, ok, warn, err, C
    from .session import Session
except ImportError:
    def info(m): print(f"[*] {m}")
    def ok(m):   print(f"[+] {m}")
    def warn(m): print(f"[!] {m}")
    def err(m):  print(f"[-] {m}")
    class C: R=G=Y=C=M=W=E=""
    from session import Session


def _meta(html, prop):
    m = re.search(rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']', html, re.I)
    if m:
        return m.group(1).replace("&amp;","&").replace("&quot;",'"').replace("&#39;","'").replace("&lt;","<").replace("&gt;",">")
    m = re.search(rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']', html, re.I)
    return m.group(1).replace("&amp;","&").replace("&quot;",'"') if m else ""

def _rx(t, p):
    m = re.search(p, t)
    return m.group(1) if m else ""

def _jstr(t, p):
    m = re.search(p, t)
    if not m:
        return ""
    try:
        return json.loads(f'"{m.group(1)}"')
    except Exception:
        return m.group(1)

def _cnt(t, *ps):
    for p in ps:
        m = re.search(p, t)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return 0


class OSINT:
    APP_ID = "936619743392459"

    def __init__(self, username, output_dir="output", proxy=None, sessionid=None):
        self.username = username.strip().lstrip("@")
        self.output_dir = output_dir
        self.proxy_url = proxy
        self.sessionid = (sessionid or os.environ.get("IG_SESSIONID") or "").strip()
        self.data = {}
        self.fail_reason = ""
        self.session = requests.Session()
        self._apply_proxy(proxy)
        self._apply_fp(mobile=True)

    def _apply_proxy(self, proxy):
        self.proxy_url = proxy
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})
        else:
            self.session.proxies.clear()

    def _apply_fp(self, mobile=True):
        self.session.headers.clear()
        h = Session.build_headers(username=self.username, mobile=mobile, for_api=True)
        h.update(Session.new_device_ids())
        self.session.headers.update(h)

    def scrape(self):
        info(f"Scanning @{self.username}...")
        result = self._run_pass()
        if result:
            return result

        if self.proxy_url:
            warn("Proxy failed — retry DIRECT...")
            self._apply_proxy(None)
            self.fail_reason = ""
            result = self._run_pass()
            if result:
                return result

        warn("Retry desktop...")
        self._apply_fp(mobile=False)
        result = self._run_pass()
        if result:
            return result

        self._save_empty()
        self._report_failure()
        return {}

    def _run_pass(self):
        self._warm()
        if self.sessionid:
            self.session.cookies.set("sessionid", self.sessionid, domain=".instagram.com")

        methods = [
            ("web_profile_info", self._via_web_profile_info),
            ("html_sharedData",  self._via_html),
            ("i.instagram",      self._via_i_api),
            ("graphql_direct",   self._via_graphql_direct),
            ("og_meta",          self._via_og_reload),
        ]

        for name, fn in methods:
            try:
                time.sleep(random.uniform(0.5, 1.5))
                self._apply_fp(mobile=random.choice([True, True, False]))
                info(f"Trying: {name}")
                if fn() and self._is_real():
                    self._save()
                    ok(f"OSINT OK — @{self.data.get('username', self.username)}")
                    self.print_summary()
                    return self.data
            except requests.exceptions.ProxyError:
                self.fail_reason = "Proxy DEAD"
                return {}
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                continue
            except requests.exceptions.ConnectionError:
                continue
            except Exception:
                continue
        return {}

    def _warm(self):
        try:
            self.session.headers.update(Session.build_headers(for_api=False, mobile=True))
            r = self.session.get("https://www.instagram.com/", timeout=20, allow_redirects=True)
            csrf = self.session.cookies.get("csrftoken") or ""
            if not csrf:
                m = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', r.text or "")
                if m:
                    csrf = m.group(1)
                    self.session.cookies.set("csrftoken", csrf, domain=".instagram.com")
            if csrf:
                self.session.headers["X-CSRFToken"] = csrf
            if not self.session.cookies.get("ig_did"):
                self.session.cookies.set("ig_did", str(uuid.uuid4()).upper(), domain=".instagram.com")
            self.session.get(f"https://www.instagram.com/{self.username}/", timeout=20, allow_redirects=True)
            time.sleep(random.uniform(0.2, 0.8))
        except Exception:
            pass

    def _via_web_profile_info(self):
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={self.username}"
        h = Session.build_headers(self.username, mobile=True, for_api=True)
        h["X-IG-App-ID"] = self.APP_ID
        h["X-CSRFToken"] = self.session.cookies.get("csrftoken", "")
        r = self.session.get(url, headers=h, timeout=25)
        if r.status_code == 404:
            self.fail_reason = "not found"
            return False
        if r.status_code in (401, 403):
            self.fail_reason = f"login wall HTTP{r.status_code}"
            return False
        if r.status_code != 200:
            return False
        try:
            user = (r.json().get("data") or {}).get("user") or {}
        except Exception:
            return False
        if not user:
            return False
        self._from_user(user)
        if not self._is_real():
            self._parse_any_json_blob(r.text, self.username)
        return True

    def _via_i_api(self):
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={self.username}"
        h = {
            "User-Agent": Session.ig_app_ua(),
            "X-IG-App-ID": self.APP_ID,
            "Accept": "*/*",
            "Accept-Language": random.choice(Session.LANGS),
        }
        h.update(Session.new_device_ids())
        r = self.session.get(url, headers=h, timeout=25)
        if r.status_code != 200:
            return False
        try:
            user = (r.json().get("data") or {}).get("user") or {}
        except Exception:
            return False
        if not user:
            return False
        self._from_user(user)
        return True

    def _via_graphql_direct(self):
        uid = self.data.get("id") or ""
        if not uid:
            h = Session.build_headers(self.username, mobile=True, for_api=False)
            r = self.session.get(f"https://www.instagram.com/{self.username}/", headers=h, timeout=20)
            m = re.search(r'"id"\s*:\s*"(\d+)"', r.text or "")
            if m:
                uid = m.group(1)
        if not uid:
            return False
        url = f"https://www.instagram.com/api/v1/users/{uid}/info/"
        h = Session.build_headers(self.username, mobile=True, for_api=True)
        h["X-IG-App-ID"] = self.APP_ID
        try:
            r = self.session.get(url, headers=h, timeout=20)
            if r.status_code == 200:
                j = r.json()
                user = j.get("user") or j
                if user:
                    self._from_user(user)
                    return True
        except Exception:
            pass
        return False

    def _via_html(self):
        url = f"https://www.instagram.com/{self.username}/"
        h = Session.build_headers(self.username, mobile=True, for_api=False)
        r = self.session.get(url, headers=h, timeout=25)
        if r.status_code == 404:
            self.fail_reason = "not found"
            return False
        if r.status_code != 200:
            return False
        html = r.text or ""

        m = re.search(r"window\._sharedData\s*=\s*(\{.+?\});</script>", html, re.DOTALL)
        if m:
            try:
                shared = json.loads(m.group(1))
                user = (shared.get("entry_data", {}).get("ProfilePage", [{}])[0]
                            .get("graphql", {}).get("user"))
                if user:
                    self._from_user(user)
                if self._is_real():
                    return True
            except Exception:
                pass

        if self._parse_any_json_blob(html, self.username) and self._is_real():
            return True
        if self._parse_og(html):
            return True
        self.fail_reason = "no data in HTML"
        return False

    def _via_og_reload(self):
        url = f"https://www.instagram.com/{self.username}/"
        h = Session.build_headers(self.username, mobile=False, for_api=False)
        r = self.session.get(url, headers=h, timeout=25)
        if r.status_code != 200:
            return False
        return self._parse_og(r.text or "")

    def _parse_any_json_blob(self, html, username):
        pos = html.find(f'"{username}"')
        if pos == -1:
            pos = html.find(f"'{username}'")
        if pos == -1:
            return False
        start = max(0, pos - 15000)
        end = min(len(html), pos + 15000)
        chunk = html[start:end]
        for pk in ["full_name", "biography", "edge_followed_by", "is_private"]:
            if pk in chunk:
                d = {}
                d["id"] = _rx(chunk, r'"id"\s*:\s*"(\d+)"') or _rx(chunk, r'"pk"\s*:\s*(\d+)')
                d["username"] = username
                d["full_name"] = _jstr(chunk, r'"full_name"\s*:\s*"((?:\\.|[^"\\])*)"')
                d["biography"] = _jstr(chunk, r'"biography"\s*:\s*"((?:\\.|[^"\\])*)"')
                d["external_url"] = _jstr(chunk, r'"external_url"\s*:\s*"((?:\\.|[^"\\])*)"')
                prv = re.search(r'"is_private"\s*:\s*(true|false)', chunk)
                d["is_private"] = bool(prv and prv.group(1) == "true")
                ver = re.search(r'"is_verified"\s*:\s*(true|false)', chunk)
                d["is_verified"] = bool(ver and ver.group(1) == "true")
                d["is_business"] = False
                d["business_category"] = ""
                d["category"] = ""
                d["followers"] = _cnt(chunk,
                    r'"edge_followed_by"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"follower_count"\s*:\s*(\d+)')
                d["following"] = _cnt(chunk,
                    r'"edge_follow"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"following_count"\s*:\s*(\d+)')
                d["posts"] = _cnt(chunk,
                    r'"edge_owner_to_timeline_media"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"media_count"\s*:\s*(\d+)')
                d["profile_pic"] = (_jstr(chunk, r'"profile_pic_url_hd"\s*:\s*"((?:\\.|[^"\\])*)"')
                                    or _jstr(chunk, r'"profile_pic_url"\s*:\s*"((?:\\.|[^"\\])*)"')
                                    or "")
                self.data = d
                return True
        return False

    def _from_user(self, user):
        def cnt(ek, fk):
            v = user.get(ek)
            if isinstance(v, dict):
                return int(v.get("count") or 0)
            try:
                return int(user.get(fk) or 0)
            except Exception:
                return 0

        self.data = {
            "id": str(user.get("id") or user.get("pk") or ""),
            "username": user.get("username") or self.username,
            "full_name": user.get("full_name") or user.get("name") or "",
            "biography": user.get("biography") or user.get("bio") or "",
            "external_url": user.get("external_url") or user.get("website") or "",
            "is_private": bool(user.get("is_private", False)),
            "is_verified": bool(user.get("is_verified", False)),
            "is_business": bool(user.get("is_business_account", False)),
            "business_category": user.get("business_category_name") or "",
            "category": user.get("category_name") or "",
            "followers": cnt("edge_followed_by", "follower_count"),
            "following": cnt("edge_follow", "following_count"),
            "posts": cnt("edge_owner_to_timeline_media", "media_count"),
            "profile_pic": user.get("profile_pic_url_hd") or user.get("profile_pic_url") or "",
        }

    def _parse_og(self, html):
        desc = _meta(html, "og:description") or _meta(html, "description")
        title = _meta(html, "og:title") or ""
        followers = following = posts = 0
        full_name = ""
        priv = False

        if desc:
            def pnum(label):
                m = re.search(rf"([\d.,]+)\s*([KkMm])?\s*{label}", desc, re.I)
                if m:
                    try:
                        v = float(m.group(1).replace(",", ""))
                    except Exception:
                        return 0
                    su = (m.group(2) or "").upper()
                    if su == "K":
                        v *= 1000
                    elif su == "M":
                        v *= 1000000
                    return int(v)
                return 0
            followers = pnum("Followers")
            following = pnum("Following")
            posts = pnum("Posts")
            m = re.search(r"from\s+(.+?)\s*\(@", desc)
            if m:
                full_name = m.group(1).strip()
            if "private" in desc.lower():
                priv = True

        if title and not full_name:
            m = re.search(r"^(.+?)\s*\(@", title)
            if m:
                full_name = m.group(1).strip()

        if not any([followers, following, posts, full_name]):
            return False
        if full_name.lower() in ("login", "instagram") and not followers:
            return False

        self.data = {
            "id": "", "username": self.username,
            "full_name": (full_name if full_name.lower() != self.username.lower() else ""),
            "biography": "", "external_url": "", "is_private": priv,
            "is_verified": False, "is_business": False,
            "business_category": "", "category": "",
            "followers": followers, "following": following, "posts": posts,
            "profile_pic": _meta(html, "og:image") or "",
        }
        return self._is_real()

    def _is_real(self):
        d = self.data or {}
        if d.get("full_name") or d.get("biography") or d.get("id"):
            return True
        if int(d.get("followers") or 0) > 0:
            return True
        if int(d.get("posts") or 0) > 0:
            return True
        return False

    def _save(self):
        path = os.path.join(self.output_dir, self.username)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "osint.json"), "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _save_empty(self):
        self.data = {
            "id": "", "username": self.username, "full_name": "", "biography": "",
            "external_url": "", "is_private": False, "is_verified": False,
            "is_business": False, "business_category": "", "category": "",
            "followers": 0, "following": 0, "posts": 0, "profile_pic": "",
            "fail_reason": self.fail_reason or "no data",
        }
        self._save()

    def _report_failure(self):
        print()
        err(f"OSINT FAILED for @{self.username}")
        if self.fail_reason:
            warn(f"Reason: {self.fail_reason}")
        print(f"""
{C.Y}OSINT blocked or limited.{C.E}
  1) Use VPN then retry
  2) export IG_SESSIONID='cookie'
  3) Fill Interview manually (menu 2)
""")

    def print_summary(self):
        d = self.data
        print(f"""
{C.C}{'=' * 44}{C.E}
  Name       : {d.get('full_name') or 'N/A'}
  Username   : @{d.get('username', self.username)}
  ID         : {d.get('id') or 'N/A'}
  Private    : {d.get('is_private')}
  Verified   : {d.get('is_verified')}
  Followers  : {int(d.get('followers') or 0):,}
  Following  : {int(d.get('following') or 0):,}
  Posts      : {int(d.get('posts') or 0):,}
  Bio        : {(d.get('biography') or 'N/A')[:100]}
  Category   : {d.get('category') or d.get('business_category') or 'N/A'}
  URL        : {d.get('external_url') or 'N/A'}
{C.C}{'=' * 44}{C.E}
""")

    def get_hints(self):
        bio = self.data.get("biography") or ""
        name = self.data.get("full_name") or ""
        uname = self.data.get("username") or self.username
        blob = f"{bio} {name}"
        tokens = [t for t in re.findall(r"[a-zA-Z\u0600-\u06FF0-9_]+", blob.lower()) if 2 <= len(t) <= 32]
        years = re.findall(r"\b(19\d{2}|20[0-2]\d)\b", blob)
        phones = [re.sub(r"[\s\-]+", "", p) for p in re.findall(r"(?:\+?\d[\d\s\-]{6,}\d)", bio)]
        stats = []
        for n in (self.data.get("followers") or 0, self.data.get("posts") or 0, self.data.get("following") or 0):
            try:
                n = int(n)
                s = str(n)
                stats.append(s)
            except Exception:
                continue
            if len(s) >= 2:
                stats.append(s[-2:])
            if len(s) >= 4:
                stats.append(s[-4:])
        parts = [p for p in re.split(r"[._\-\s]+", uname) if len(p) >= 2]
        return {
            "username": uname, "full_name": name, "biography": bio,
            "bio_tokens": list(dict.fromkeys(tokens)),
            "years": list(dict.fromkeys(years)), "phones": phones,
            "followers": int(self.data.get("followers") or 0),
            "following": int(self.data.get("following") or 0),
            "posts": int(self.data.get("posts") or 0),
            "user_parts": parts,
            "stat_numbers": list(dict.fromkeys(stats)),
            "category": (self.data.get("category") or self.data.get("business_category") or ""),
            "external_url": self.data.get("external_url") or "",
            "is_private": bool(self.data.get("is_private")),
            "osint_ok": self._is_real(),
        }
