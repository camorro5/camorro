#!/usr/bin/env python3
"""
camoro v2.0 - Instagram Profile Information Gathering Tool
Updated: July 2026 - Uses i.instagram.com web_profile_info API
"""

import json
import re
import sys
import os
import textwrap
from datetime import datetime

# نحاول استيراد curl_cffi إذا متوفر، وإلا نستخدم requests
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    HAS_CURL_CFFI = False

# ==================== COLORS ====================
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    P = '\033[95m'
    C = '\033[96m'
    W = '\033[97m'
    BL = '\033[1m'
    RE = '\033[0m'

def cprint(text, color=C.W, bold=False):
    prefix = C.BL if bold else ""
    print(f"{prefix}{color}{text}{C.RE}")

# ==================== CAMORO v2 ====================
class Camoro:
    # Instagram public App ID - لم يتغير منذ سنوات
    IG_APP_ID = "936619743392459"

    # User-Agent يشبه متصفح حقيقي
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self):
        self._init_session()
        self.cookie_file = os.path.expanduser('~/.camoro_cookies_v2')

    def _init_session(self):
        """إنشاء session جديد مع headers أساسية"""
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
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1',
        })

    def _warmup_session(self):
        """زيارة صفحة إنستقرام الرئيسية للحصول على الكوكيز اللازمة"""
        cprint("[*] Warming up session (getting cookies)...", C.C)
        try:
            self.session.get(
                "https://www.instagram.com/",
                timeout=15,
                allow_redirects=True
            )
            return True
        except Exception:
            return False

    def fetch_profile(self, username):
        username = username.strip().replace('@', '')

        # أولاً: تسخين الجلسة
        self._warmup_session()

        # الطريقة 1: i.instagram.com API (الطريقة الرئيسية)
        cprint("[*] Method 1: i.instagram.com API...", C.C)
        data = self._try_i_instagram_api(username)
        if data:
            return data

        # الطريقة 2: www.instagram.com API
        cprint("[*] Method 2: www.instagram.com API...", C.C)
        data = self._try_www_instagram_api(username)
        if data:
            return data

        # الطريقة 3: HTML scraping - __additionalDataLoaded
        cprint("[*] Method 3: HTML scraping...", C.C)
        data = self._try_html_additional_data(username)
        if data:
            return data

        # الطريقة 4: instagram.com/?__a=1 (تجربة أخيرة)
        cprint("[*] Method 4: Legacy __a=1 endpoint...", C.C)
        data = self._try_legacy_endpoint(username)
        if data:
            return data

        return None

    def _try_i_instagram_api(self, username):
        """i.instagram.com - يعمل بدون تسجيل دخول مع x-ig-app-id"""
        try:
            url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"

            headers = {
                'x-ig-app-id': self.IG_APP_ID,
                'User-Agent': self.session.headers.get('User-Agent',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'),
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.instagram.com',
                'Referer': 'https://www.instagram.com/',
            }

            resp = self.session.get(url, headers=headers, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                user = data.get('data', {}).get('user')
                if user:
                    return self._parse_user_mobile_api(user)
            elif resp.status_code == 403:
                cprint("[!] 403 Forbidden - Instagram is blocking this IP. Try using a VPN/proxy.", C.Y)
            elif resp.status_code == 404:
                cprint("[!] 404 - Profile not found or doesn't exist.", C.R)

        except Exception as e:
            cprint(f"[-] Error: {str(e)[:80]}", C.Y)
        return None

    def _try_www_instagram_api(self, username):
        """www.instagram.com - نفس الـ API لكن على domain مختلف"""
        try:
            url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"

            headers = {
                'x-ig-app-id': self.IG_APP_ID,
                'x-requested-with': 'XMLHttpRequest',
                'Accept': '*/*',
            }

            resp = self.session.get(url, headers=headers, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                user = data.get('data', {}).get('user')
                if user:
                    return self._parse_user_mobile_api(user)

        except Exception:
            pass
        return None

    def _try_html_additional_data(self, username):
        """استخراج من window.__additionalDataLoaded في HTML"""
        try:
            url = f"https://www.instagram.com/{username}/"
            resp = self.session.get(url, timeout=15, allow_redirects=True)

            if resp.status_code != 200:
                return None

            html = resp.text

            # البحث عن window.__additionalDataLoaded
            patterns = [
                r'window\.__additionalDataLoaded\(\s*[\'"]feed[^\'"]*[\'"]\s*,\s*({.*?})\s*\)\s*;',
                r'window\.__additionalDataLoaded\(\s*[\'"][^\'"]*[\'"]\s*,\s*({.*?})\s*\)',
                r'window\._sharedData\s*=\s*({.*?});\s*</script>',
            ]

            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        user = None

                        if 'graphql' in data:
                            user = data['graphql'].get('user')
                        elif 'entry_data' in data:
                            profiles = data['entry_data'].get('ProfilePage', [])
                            if profiles:
                                user = profiles[0].get('graphql', {}).get('user')

                        if user:
                            return self._parse_user_graphql(user)
                    except (json.JSONDecodeError, KeyError):
                        continue

            # فحص إذا الصفحة تطلب تسجيل دخول
            if '"csrf_token"' in html and 'login' in html.lower():
                cprint("[!] Login wall detected. Profile may be private.", C.Y)

        except Exception:
            pass
        return None

    def _try_legacy_endpoint(self, username):
        """محاولة أخيرة: ?__a=1 القديم"""
        try:
            url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
            resp = self.session.get(url, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                user = data.get('graphql', {}).get('user')
                if user:
                    return self._parse_user_graphql(user)
        except Exception:
            pass
        return None

    def _parse_user_mobile_api(self, user):
        """تحليل بيانات المستخدم من mobile API"""
        return {
            'username': user.get('username', 'N/A'),
            'full_name': user.get('full_name', 'N/A'),
            'bio': user.get('biography', ''),
            'followers': user.get('follower_count', 0),
            'following': user.get('following_count', 0),
            'posts': user.get('media_count', 0),
            'is_private': user.get('is_private', False),
            'is_verified': user.get('is_verified', False),
            'is_business': user.get('is_business', False),
            'profile_pic_hd': user.get('profile_pic_url_hd', user.get('profile_pic_url', '')),
            'profile_pic': user.get('profile_pic_url', ''),
            'external_url': user.get('external_url', ''),
            'category': user.get('category_name', user.get('category', 'N/A')),
            'id': user.get('id', user.get('pk', 'N/A')),
            'highlight_reel_count': user.get('highlight_reel_count', 0),
        }

    def _parse_user_graphql(self, user):
        """تحليل بيانات المستخدم من GraphQL"""
        return {
            'username': user.get('username', 'N/A'),
            'full_name': user.get('full_name', 'N/A'),
            'bio': user.get('biography', ''),
            'followers': user.get('edge_followed_by', {}).get('count', 0),
            'following': user.get('edge_follow', {}).get('count', 0),
            'posts': user.get('edge_owner_to_timeline_media', {}).get('count', 0),
            'is_private': user.get('is_private', False),
            'is_verified': user.get('is_verified', False),
            'is_business': user.get('is_business_account', False),
            'profile_pic_hd': user.get('profile_pic_url_hd', ''),
            'profile_pic': user.get('profile_pic_url', ''),
            'external_url': user.get('external_url', ''),
            'category': user.get('category_name', 'N/A'),
            'id': user.get('id', 'N/A'),
            'highlight_reel_count': user.get('highlight_reel_count', 0),
        }

    def _fmt(self, num):
        if num is None:
            return 'N/A'
        return f"{num:,}"

    def display(self, data):
        os.system('clear' if os.name == 'posix' else 'cls')

        print(f"""
    {C.P}╔══════════════════════════════════════════════╗
    ║           {C.BL}C A M O R O  v2.0{C.RE}{C.P}                  ║
    ║       Instagram Profile Scanner            ║
    ╚══════════════════════════════════════════════╝{C.RE}
""")

        # Status
        priv = f"{C.R}PRIVATE 🔒{C.RE}" if data['is_private'] else f"{C.G}PUBLIC 🌐{C.RE}"
        verif = f"{C.B}VERIFIED ✓{C.RE}" if data['is_verified'] else ""
        biz = f"{C.Y}BUSINESS{ C.RE}" if data['is_business'] else ""

        status = f"  Status: {priv}"
        if verif:
            status += f" | {verif}"
        if biz:
            status += f" | {biz}"
        print(status + "\n")

        print(f"  {C.C}{C.BL}╔══ Profile Information ═══════════════════════╗{C.RE}")

        rows = [
            ("📛 Username", data['username']),
            ("👤 Full Name", data['full_name']),
            ("🆔 User ID", str(data['id'])),
            ("📂 Category", data['category']),
            ("👥 Followers", self._fmt(data['followers'])),
            ("🔗 Following", self._fmt(data['following'])),
            ("📸 Posts", self._fmt(data['posts'])),
            ("🌟 Highlights", str(data['highlight_reel_count'])),
        ]

        for label, value in rows:
            print(f"  {C.G}{label}{C.RE}: {C.W}{value}{C.RE}")

        if data['bio']:
            print(f"\n  {C.Y}{C.BL}📝 Bio:{C.RE}")
            for line in textwrap.wrap(data['bio'], width=46):
                print(f"  {C.W}{line}{C.RE}")

        if data['external_url']:
            print(f"\n  {C.C}{C.BL}🔗 External URL:{C.RE}")
            print(f"  {C.W}{data['external_url']}{C.RE}")

        if data['profile_pic_hd']:
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
{C.RE}{C.W}                    Version 2.0 | 2026
{C.RE}
""")


def save_json(data, username):
    fname = f"camoro_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return fname


def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    banner()

    # تحقق من دعم curl_cffi
    if HAS_CURL_CFFI:
        cprint("[✓] Using curl_cffi for TLS fingerprint evasion", C.G)
    else:
        cprint("[!] curl_cffi not installed. Install: pip3 install curl_cffi", C.Y)
        cprint("[!] Falling back to requests (may be blocked by Instagram)", C.Y)

    camoro = Camoro()

    while True:
        try:
            username = input(
                f"\n{C.G}[?]{C.RE} {C.BL}Target username{C.RE} {C.W}(exit to quit){C.RE}: "
            ).strip()

            if username.lower() in ['exit', 'quit', 'q', 'خروج']:
                cprint("\n👋 Goodbye!", C.P)
                sys.exit(0)

            if not username:
                cprint("[!] Username cannot be empty!", C.R)
                continue

            username = username.replace('@', '')

            print(f"\n{C.C}─── Fetching: @{username} ───{C.RE}\n")

            data = camoro.fetch_profile(username)

            if data is None:
                cprint(f"\n[✗] FAILED to fetch @{username}", C.R)
                cprint("\n[!] Troubleshooting:", C.Y)
                print("  1. تأكد أن الحساب موجود وعام (Public)")
                print("  2. جرب تستخدم VPN - إنستقرام يحجب بعض الـ IPs")
                print("  3. ثبت curl_cffi: pip3 install curl_cffi")
                print("  4. انتظر شوي وحاول مرة ثانية (rate limiting)")
                continue

            camoro.display(data)

            sv = input(f"{C.G}[?]{C.RE} Save to file? {C.W}(y/n){C.RE}: ").strip().lower()
            if sv in ['y', 'yes', 'نعم']:
                f = save_json(data, username)
                cprint(f"[✓] Saved: {f}", C.G)

            again = input(f"\n{C.G}[?]{C.RE} Scan another? {C.W}(y/n){C.RE}: ").strip().lower()
            if again not in ['y', 'yes', 'نعم']:
                cprint("\n👋 Goodbye!", C.P)
                sys.exit(0)

        except KeyboardInterrupt:
            cprint("\n\n👋 Interrupted. Goodbye!", C.Y)
            sys.exit(0)
        except Exception as e:
            cprint(f"\n[✗] Error: {e}", C.R)


if __name__ == "__main__":
    main()
