#!/usr/bin/env python3
"""
camoro v2.1 - Instagram Profile Information Gathering Tool
Updated: July 2026
Fix: Handles both flat (follower_count) and nested (edge_followed_by.count) formats
"""

import json
import re
import sys
import os
import textwrap
from datetime import datetime

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    HAS_CURL_CFFI = False

# ==================== COLORS ====================
class C:
    R = '\033[91m'; G = '\033[92m'; Y = '\033[93m'
    B = '\033[94m'; P = '\033[95m'; C = '\033[96m'
    W = '\033[97m'; BL = '\033[1m'; RE = '\033[0m'

def cprint(text, color=C.W, bold=False):
    prefix = C.BL if bold else ""
    print(f"{prefix}{color}{text}{C.RE}")

# ==================== CAMORO v2.1 ====================
class Camoro:
    IG_APP_ID = "936619743392459"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self, debug=False):
        self.debug = debug
        self._init_session()

    def _init_session(self):
        import random
        if HAS_CURL_CFFI:
            self.session = cffi_requests.Session()
        else:
            self.session = requests.Session()

        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        })

    def _warmup(self):
        """تسخين الجلسة بزيارة instagram.com + الحصول على csrf token"""
        cprint("[*] Warming up session...", C.C)
        try:
            # الزيارة الأولى للحصول على الكوكيز الأساسية
            r1 = self.session.get("https://www.instagram.com/", timeout=15)
            if self.debug:
                cprint(f"    Warmup status: {r1.status_code}", C.Y)
                cprint(f"    Cookies: {dict(self.session.cookies)}", C.Y)

            # استخراج csrf token إن وجد
            if 'csrftoken' not in self.session.cookies:
                # نجرب الزيارة مرة ثانية
                self.session.get("https://www.instagram.com/accounts/login/", timeout=15)

            return True
        except Exception as e:
            if self.debug:
                cprint(f"    Warmup error: {e}", C.R)
            return False

    def fetch_profile(self, username):
        username = username.strip().replace('@', '')

        # تسخين
        self._warmup()

        # الطريقة 1: i.instagram.com (أفضل طريقة)
        cprint("[*] Method 1: i.instagram.com API...", C.C)
        data = self._try_api("i.instagram.com", username)
        if data and data.get('followers', 0) > 0:
            return data
        if data:
            cprint("[!] Got partial data from method 1, trying next...", C.Y)

        # الطريقة 2: www.instagram.com
        cprint("[*] Method 2: www.instagram.com API...", C.C)
        data = self._try_api("www.instagram.com", username)
        if data and data.get('followers', 0) > 0:
            return data

        # الطريقة 3: HTML scraping مع __additionalDataLoaded
        cprint("[*] Method 3: HTML scraping...", C.C)
        data = self._try_html(username)
        if data:
            return data

        # إذا وصلنا هنا ومعانا بيانات جزئية من method 1 أو 2، نرجعها
        if data:
            return data

        return None

    def _try_api(self, domain, username):
        """استدعاء web_profile_info من domain محدد"""
        try:
            url = f"https://{domain}/api/v1/users/web_profile_info/?username={username}"

            headers = {
                'x-ig-app-id': self.IG_APP_ID,
                'x-requested-with': 'XMLHttpRequest',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.instagram.com',
                'Referer': f'https://www.instagram.com/{username}/',
                'Sec-Fetch-Site': 'same-origin' if domain == 'www.instagram.com' else 'same-site',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
            }

            resp = self.session.get(url, headers=headers, timeout=20)

            if self.debug:
                cprint(f"    [{domain}] Status: {resp.status_code}", C.Y)
                cprint(f"    [{domain}] Content length: {len(resp.text)}", C.Y)

            if resp.status_code == 200:
                raw = resp.json()

                if self.debug:
                    # طباعة أول 1000 حرف من الـ response عشان نشوف الهيكل
                    cprint(f"    [{domain}] Response keys: {list(raw.keys())}", C.Y)
                    if 'data' in raw:
                        user_keys = list(raw['data'].get('user', {}).keys())
                        cprint(f"    [{domain}] User keys: {user_keys}", C.Y)

                user = raw.get('data', {}).get('user')
                if user:
                    return self._parse(user, raw)

            elif resp.status_code == 403:
                cprint(f"[!] 403 Forbidden on {domain} - IP may be blocked", C.Y)

        except Exception as e:
            if self.debug:
                cprint(f"    [{domain}] Error: {str(e)[:100]}", C.R)
        return None

    def _try_html(self, username):
        """استخراج من HTML"""
        try:
            url = f"https://www.instagram.com/{username}/"
            headers = {
                'Accept': 'text/html,application/xhtml+xml',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            }
            resp = self.session.get(url, headers=headers, timeout=20)
            html = resp.text

            if self.debug:
                cprint(f"    HTML status: {resp.status_code}, length: {len(html)}", C.Y)

            # محاولة 1: __additionalDataLoaded
            patterns = [
                r'window\.__additionalDataLoaded\(\s*[\'"]feed[^\'"]*[\'"]\s*,\s*({.*?})\s*\)\s*;',
                r'window\.__additionalDataLoaded\(\s*[\'"][^\'"]*[\'"]\s*,\s*({.*?})\s*\)',
                r'window\._sharedData\s*=\s*({.*?});\s*</script>',
                r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.*?});</script>',
            ]

            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        raw = json.loads(match.group(1))
                        user = None

                        if 'graphql' in raw:
                            user = raw['graphql'].get('user')
                        elif 'entry_data' in raw:
                            profiles = raw['entry_data'].get('ProfilePage', [])
                            if profiles:
                                user = profiles[0].get('graphql', {}).get('user')
                        elif 'user' in raw:
                            user = raw.get('user')

                        if user:
                            return self._parse(user, raw)
                    except (json.JSONDecodeError, KeyError):
                        continue

            # محاولة 2: LD+JSON schema
            ld_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                html, re.DOTALL
            )
            if ld_match:
                try:
                    ld_data = json.loads(ld_match.group(1))
                    if ld_data.get('@type') == 'Person':
                        return self._parse_ld_json(ld_data, username)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            if self.debug:
                cprint(f"    HTML error: {str(e)[:100]}", C.R)
        return None

    def _parse(self, user, raw=None):
        """
        تحليل بيانات المستخدم.
        يتعامل مع الصيغتين:
        - Flat: follower_count, following_count, media_count
        - Nested: edge_followed_by.count, edge_follow.count, edge_owner_to_timeline_media.count
        """
        def _get_count(*keys_sets):
            """محاولة استخراج count من عدة مسارات محتملة"""
            for keys in keys_sets:
                val = user
                for k in keys:
                    if isinstance(val, dict):
                        val = val.get(k)
                    else:
                        val = None
                        break
                if val is not None and not isinstance(val, dict):
                    return val
            return 0

        followers = _get_count(
            ('follower_count',),
            ('edge_followed_by', 'count'),
            ('edge_follow', 'count'),  # بعض الإصدارات تخلط
        )

        following = _get_count(
            ('following_count',),
            ('edge_follow', 'count'),
            ('edge_followed_by', 'count'),
        )

        posts = _get_count(
            ('media_count',),
            ('edge_owner_to_timeline_media', 'count'),
            ('edge_felix_video_timeline', 'count'),
        )

        highlight_count = _get_count(
            ('highlight_reel_count',),
        )

        # profile_pic: جرب hd أولاً ثم العادي
        pp = user.get('profile_pic_url_hd') or user.get('profile_pic_url', '')

        # external url
        ext_url = user.get('external_url', '') or user.get('bio_links', [{}])[0].get('url', '')

        # category
        category = user.get('category_name') or user.get('category', 'N/A')

        result = {
            'username': user.get('username', 'N/A'),
            'full_name': user.get('full_name', 'N/A'),
            'bio': user.get('biography', user.get('bio', '')),
            'followers': int(followers) if followers else 0,
            'following': int(following) if following else 0,
            'posts': int(posts) if posts else 0,
            'is_private': user.get('is_private', False),
            'is_verified': user.get('is_verified', False),
            'is_business': user.get('is_business_account', user.get('is_business', False)),
            'profile_pic_hd': pp,
            'profile_pic': user.get('profile_pic_url', pp),
            'external_url': ext_url,
            'category': category,
            'id': str(user.get('id') or user.get('pk', 'N/A')),
            'highlight_reel_count': int(highlight_count) if highlight_count else 0,
        }

        # إذا فيه business contact info
        if user.get('business_contact_method'):
            result['business_contact'] = user.get('business_contact_method')
            result['business_email'] = user.get('business_email', '')
            result['business_phone'] = user.get('business_phone_number', '')

        return result

    def _parse_ld_json(self, ld, username):
        """تحليل LD+JSON schema"""
        followers = 0
        following = 0
        posts = 0

        if 'InteractionStatistic' in ld:
            for stat in ld['InteractionStatistic']:
                name = stat.get('name', '').lower()
                count = stat.get('userInteractionCount', 0)
                if 'follow' in name and 'ing' not in name:
                    followers = int(count) if count else 0
                elif 'following' in name or 'follows' in name:
                    following = int(count) if count else 0
                elif 'post' in name or 'media' in name:
                    posts = int(count) if count else 0

        return {
            'username': ld.get('alternateName', username),
            'full_name': ld.get('name', 'N/A'),
            'bio': ld.get('description', ''),
            'followers': followers,
            'following': following,
            'posts': posts,
            'is_private': False,
            'is_verified': False,
            'is_business': False,
            'profile_pic_hd': ld.get('image', {}).get('url', '') if isinstance(ld.get('image'), dict) else ld.get('image', ''),
            'profile_pic': '',
            'external_url': ld.get('url', ''),
            'category': 'N/A',
            'id': ld.get('identifier', 'N/A'),
            'highlight_reel_count': 0,
        }

    def _fmt(self, num):
        if num is None:
            return '0'
        return f"{num:,}"

    def display(self, data):
        os.system('clear' if os.name == 'posix' else 'cls')

        print(f"""
    {C.P}╔══════════════════════════════════════════════╗
    ║           {C.BL}C A M O R O  v2.1{C.RE}{C.P}                  ║
    ║       Instagram Profile Scanner            ║
    ╚══════════════════════════════════════════════╝{C.RE}
""")

        # Status badges
        priv = f"{C.R}PRIVATE 🔒{C.RE}" if data['is_private'] else f"{C.G}PUBLIC 🌐{C.RE}"
        parts = [f"Status: {priv}"]
        if data['is_verified']:
            parts.append(f"{C.B}VERIFIED ✓{C.RE}")
        if data['is_business']:
            parts.append(f"{C.Y}BUSINESS{C.RE}")
        print("  " + " | ".join(parts) + "\n")

        print(f"  {C.C}{C.BL}╔══ Profile Information ═══════════════════════╗{C.RE}")

        rows = [
            ("📛 Username", data['username']),
            ("👤 Full Name", data['full_name']),
            ("🆔 User ID", str(data['id'])),
            ("📂 Category", data['category']),
            ("👥 Followers", self._fmt(data['followers'])),
            ("🔗 Following", self._fmt(data['following'])),
            ("📸 Posts", self._fmt(data['posts'])),
            ("🌟 Highlights", str(data.get('highlight_reel_count', 0))),
        ]

        for label, value in rows:
            print(f"  {C.G}{label}{C.RE}: {C.W}{value}{C.RE}")

        # Business info
        if data.get('business_email'):
            print(f"  {C.G}📧 Business Email{C.RE}: {C.W}{data['business_email']}{C.RE}")
        if data.get('business_phone'):
            print(f"  {C.G}📞 Business Phone{C.RE}: {C.W}{data['business_phone']}{C.RE}")

        # Bio
        if data.get('bio'):
            print(f"\n  {C.Y}{C.BL}📝 Bio:{C.RE}")
            for line in textwrap.wrap(data['bio'], width=46):
                print(f"  {C.W}{line}{C.RE}")

        # External URL
        if data.get('external_url'):
            print(f"\n  {C.C}{C.BL}🔗 External URL:{C.RE}")
            print(f"  {C.W}{data['external_url']}{C.RE}")

        # Profile Picture
        if data.get('profile_pic_hd'):
            print(f"\n  {C.P}{C.BL}🖼️  Profile Picture:{C.RE}")
            print(f"  {C.W}{data['profile_pic_hd']}{C.RE}")

        print(f"\n  {C.C}╚══════════════════════════════════════════════╝{C.RE}\n")


# ==================== MAIN ====================
def banner():
    print(f"""
{C.P}{C.BL}
   ▄████████  ▄▄▄▄███▄▄▄▄    ▄▄▄▄███▄▄▄▄   ▄██████▄   ▄████████    ▄████████
  ███    ███ ▄██▀▀▀███▀▀▀██▄ ▄██▀▀▀███▀▀▀██▄ ███    ███ ███    ███   ███    ███
  ███    █▀  ███   ███   ███ ███   ███   ███ ███    ███ ███    █▀    ███    ███
  ███        ███   ███   ███ ███   ███   ███ ███    ███ ███         ▄███▄▄▄▄██▀
  ███        ███   ███   ███ ███   ███   ███ ███    ███ ███        ▀▀███▀▀▀▀▀
  ███    █▄  ███   ███   ███ ███   ███   ███ ███    ███ ███    █▄  ▀███████████
  ███    ███ ███   ███   ███ ███   ███   ███ ███    ███ ███    ███   ███    ███
  ████████▀   ▀█   ███   █▀   ▀█   ███   █▀   ▀██████▀  ████████▀    ███    ███
{C.RE}
{C.C}{C.BL}     Instagram Profile Information Gathering Tool
{C.RE}{C.W}                    Version 2.1 | July 2026
{C.RE}
""")


def save_json(data, username):
    fname = f"camoro_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return fname


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Camoro - Instagram Profile Scanner')
    parser.add_argument('-u', '--username', help='Target username')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('-o', '--output', help='Output JSON file')
    args = parser.parse_args()

    os.system('clear' if os.name == 'posix' else 'cls')
    banner()

    if HAS_CURL_CFFI:
        cprint("[✓] curl_cffi: TLS fingerprint evasion ACTIVE", C.G)
    else:
        cprint("[!] curl_cffi not installed. Run: pip3 install curl_cffi", C.Y)

    if args.debug:
        cprint("[D] Debug mode ON - Raw API responses will be shown", C.Y)

    camoro = Camoro(debug=args.debug)

    # إذا تم تمرير username مباشرة من command line
    target = args.username

    while True:
        try:
            if not target:
                target = input(
                    f"\n{C.G}[?]{C.RE} {C.BL}Target username{C.RE} {C.W}(exit to quit){C.RE}: "
                ).strip()

            if target.lower() in ['exit', 'quit', 'q', 'خروج']:
                cprint("\n👋 Goodbye!", C.P)
                sys.exit(0)

            if not target:
                cprint("[!] Username cannot be empty!", C.R)
                continue

            target = target.replace('@', '')

            print(f"\n{C.C}─── Fetching: @{target} ───{C.RE}\n")

            data = camoro.fetch_profile(target)

            if data is None:
                cprint(f"\n[✗] FAILED to fetch @{target}", C.R)
                cprint("\n[!] Troubleshooting:", C.Y)
                print("  1. تأكد أن الحساب موجود وعام (Public)")
                print("  2. جرب تستخدم VPN - إنستقرام يحجب بعض الـ IPs")
                print("  3. جرب مع --debug عشان تشوف الـ raw response")
                print("  4. ثبت curl_cffi: pip3 install curl_cffi")
            else:
                camoro.display(data)

                # Auto-save إذا محدد output
                if args.output:
                    f = save_json(data, target)
                    cprint(f"[✓] Auto-saved: {f}", C.G)
                else:
                    sv = input(f"{C.G}[?]{C.RE} Save to file? {C.W}(y/n){C.RE}: ").strip().lower()
                    if sv in ['y', 'yes', 'نعم']:
                        f = save_json(data, target)
                        cprint(f"[✓] Saved: {f}", C.G)

            # إذا username من command line، نخرج بعد التنفيذ
            if args.username:
                sys.exit(0)

            target = None

            again = input(f"\n{C.G}[?]{C.RE} Scan another? {C.W}(y/n){C.RE}: ").strip().lower()
            if again not in ['y', 'yes', 'نعم']:
                cprint("\n👋 Goodbye!", C.P)
                sys.exit(0)

        except KeyboardInterrupt:
            cprint("\n\n👋 Interrupted. Goodbye!", C.Y)
            sys.exit(0)
        except Exception as e:
            cprint(f"\n[✗] Error: {e}", C.R)
            import traceback
            if args.debug:
                traceback.print_exc()


if __name__ == "__main__":
    main()
