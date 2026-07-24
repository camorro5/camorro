#!/usr/bin/env python3
"""
camoro v3.0 - Instagram Profile Scanner
Method 1: instaloader (stable, well-maintained)
Method 2: i.instagram.com API (fast fallback)
Method 3: HTML scraping (last resort)
"""

import json
import re
import sys
import os
import textwrap
from datetime import datetime

# ==================== COLORS ====================
class C:
    R = '\033[91m'; G = '\033[92m'; Y = '\033[93m'
    B = '\033[94m'; P = '\033[95m'; C = '\033[96m'
    W = '\033[97m'; BL = '\033[1m'; RE = '\033[0m'

def cprint(text, color=C.W, bold=False):
    prefix = C.BL if bold else ""
    print(f"{prefix}{color}{text}{C.RE}")

# ==================== CAMORO v3 ====================
class Camoro:
    IG_APP_ID = "936619743392459"

    IPHONE_UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5.1 "
        "Mobile/15E148 Safari/604.1"
    )

    def __init__(self, debug=False):
        self.debug = debug

    # ========== METHOD 1: INSTALOADER ==========
    def _try_instaloader(self, username):
        """Instaloader - المكتبة الأكثر ثباتاً لسحب بيانات إنستقرام العامة"""
        cprint("[*] Method 1: Instaloader (stable)...", C.C)
        try:
            import instaloader

            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                quiet=True,
                user_agent=self.IPHONE_UA,
            )

            profile = instaloader.Profile.from_username(L.context, username)

            result = {
                'username': profile.username,
                'full_name': profile.full_name,
                'bio': profile.biography,
                'followers': profile.followers,
                'following': profile.followees,
                'posts': profile.mediacount,
                'is_private': profile.is_private,
                'is_verified': profile.is_verified,
                'is_business': profile.is_business_account,
                'profile_pic_hd': profile.profile_pic_url,
                'profile_pic': profile.profile_pic_url,
                'external_url': profile.external_url or '',
                'category': profile.business_category_name or 'N/A',
                'id': str(profile.userid),
                'highlight_reel_count': profile.igtvcount,
                '_source': 'instaloader',
            }

            if self.debug:
                cprint(f"    [instaloader] ✓ Success", C.G)

            return result

        except ImportError:
            cprint("[!] instaloader not installed. Run: pip3 install instaloader", C.Y)
        except instaloader.exceptions.ProfileNotExistsException:
            cprint("[!] Profile does not exist", C.R)
        except instaloader.exceptions.LoginRequiredException:
            cprint("[!] Login required - profile may be private or blocked", C.Y)
        except Exception as e:
            if self.debug:
                cprint(f"    [instaloader] Error: {str(e)[:100]}", C.R)
            else:
                cprint(f"[-] Instaloader failed: {str(e)[:60]}", C.Y)

        return None

    # ========== METHOD 2: API ==========
    def _try_api(self, username):
        """i.instagram.com web_profile_info API"""
        cprint("[*] Method 2: i.instagram.com API...", C.C)

        try:
            # استخدام curl_cffi إذا متوفر
            try:
                from curl_cffi import requests as req
                if self.debug:
                    cprint("    Using curl_cffi (TLS fingerprint spoofing)", C.Y)
            except ImportError:
                import requests as req
                if self.debug:
                    cprint("    Using standard requests (may be blocked)", C.Y)

            session = req.Session()
            session.headers.update({
                'User-Agent': self.IPHONE_UA,
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
            })

            # الخطوة 1: تسخين الجلسة - زيارة instagram.com
            cprint("    Warming up session...", C.C)
            try:
                r = session.get("https://www.instagram.com/", timeout=20)
                if self.debug:
                    cprint(f"    Warmup status: {r.status_code}", C.Y)
                    cprint(f"    Cookies: {dict(session.cookies)}", C.Y)
            except Exception as e:
                if self.debug:
                    cprint(f"    Warmup failed: {e}", C.Y)

            # الخطوة 2: استدعاء الـ API
            url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
            headers = {
                'x-ig-app-id': self.IG_APP_ID,
                'x-requested-with': 'XMLHttpRequest',
                'Origin': 'https://www.instagram.com',
                'Referer': f'https://www.instagram.com/{username}/',
                'Sec-Fetch-Site': 'same-site',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
            }

            resp = session.get(url, headers=headers, timeout=20)

            if self.debug:
                cprint(f"    API status: {resp.status_code}", C.Y)
                cprint(f"    Response length: {len(resp.text)} chars", C.Y)

            if resp.status_code != 200:
                cprint(f"[!] HTTP {resp.status_code}", C.Y)
                if resp.status_code == 403:
                    cprint("[!] IP blocked by Instagram. Use VPN or proxy.", C.R)
                return None

            raw = resp.json()
            user = raw.get('data', {}).get('user')

            if not user:
                cprint("[!] No user data in response", C.Y)
                if self.debug:
                    cprint(f"    Raw keys: {list(raw.keys())}", C.Y)
                return None

            if self.debug:
                cprint(f"    User fields: {list(user.keys())}", C.Y)

            result = self._parse_user_obj(user)
            result['_source'] = 'api'
            return result

        except Exception as e:
            if self.debug:
                cprint(f"    API error: {str(e)[:150]}", C.R)
            else:
                cprint(f"[-] API failed: {str(e)[:60]}", C.Y)
        return None

    # ========== METHOD 3: HTML SCRAPING ==========
    def _try_html(self, username):
        """استخراج من HTML الصفحة"""
        cprint("[*] Method 3: HTML scraping...", C.C)

        try:
            import requests as req
            session = req.Session()
            session.headers.update({'User-Agent': self.IPHONE_UA})

            resp = session.get(
                f"https://www.instagram.com/{username}/",
                timeout=20,
                headers={'Accept': 'text/html,application/xhtml+xml'}
            )

            if resp.status_code != 200:
                return None

            html = resp.text

            if self.debug:
                cprint(f"    HTML length: {len(html)} chars", C.Y)

            # المحاولة 1: window.__additionalDataLoaded
            pattern = r'window\.__additionalDataLoaded\(\s*[\'"][^\'"]*[\'"]\s*,\s*({.*?})\s*\)\s*;'
            match = re.search(pattern, html, re.DOTALL)

            if match:
                try:
                    data = json.loads(match.group(1))
                    user = data.get('graphql', {}).get('user')
                    if user:
                        result = self._parse_user_obj(user)
                        result['_source'] = 'html_additionalData'
                        return result
                except (json.JSONDecodeError, KeyError):
                    pass

            # المحاولة 2: window._sharedData (قديم)
            match = re.search(r'window\._sharedData\s*=\s*({.*?});\s*</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    profiles = data.get('entry_data', {}).get('ProfilePage', [])
                    if profiles:
                        user = profiles[0].get('graphql', {}).get('user')
                        if user:
                            result = self._parse_user_obj(user)
                            result['_source'] = 'html_sharedData'
                            return result
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass

            # المحاولة 3: LD+JSON
            ld_match = re.search(
                r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
                html, re.DOTALL
            )
            if ld_match:
                try:
                    ld = json.loads(ld_match.group(1))
                    if ld.get('@type') == 'Person':
                        result = self._parse_ld_json(ld, username)
                        result['_source'] = 'html_ldjson'
                        return result
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            if self.debug:
                cprint(f"    HTML error: {str(e)[:100]}", C.R)
        return None

    # ========== PARSING ==========
    def _parse_user_obj(self, user):
        """تحليل كائن user من API أو HTML - يتعامل مع جميع الصيغ"""

        def _get(*keys):
            """استخراج قيمة من مسار متداخل"""
            val = user
            for k in keys:
                if isinstance(val, dict):
                    val = val.get(k)
                else:
                    return None
            return val

        # Followers: جرب كل الصيغ الممكنة
        followers = (
            _get('follower_count') or
            _get('edge_followed_by', 'count') or
            _get('edge_follow', 'count') or
            0
        )

        # Following
        following = (
            _get('following_count') or
            _get('edge_follow', 'count') or
            _get('edge_followed_by', 'count') or
            0
        )

        # Posts
        posts = (
            _get('media_count') or
            _get('edge_owner_to_timeline_media', 'count') or
            0
        )

        # Highlights
        highlights = (
            _get('highlight_reel_count') or
            0
        )

        # Profile picture
        pp = _get('profile_pic_url_hd') or _get('profile_pic_url') or ''

        # External URL
        ext_url = _get('external_url') or ''
        if not ext_url:
            bio_links = _get('bio_links')
            if bio_links and isinstance(bio_links, list) and len(bio_links) > 0:
                ext_url = bio_links[0].get('url', '')

        # Category
        category = _get('category_name') or _get('category') or 'N/A'

        # ID
        uid = _get('id') or _get('pk') or 'N/A'

        return {
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
            'profile_pic': pp,
            'external_url': ext_url,
            'category': category,
            'id': str(uid),
            'highlight_reel_count': int(highlights) if highlights else 0,
        }

    def _parse_ld_json(self, ld, username):
        """تحليل LD+JSON schema"""
        followers = 0
        for stat in ld.get('InteractionStatistic', []):
            name = stat.get('name', '').lower()
            count = stat.get('userInteractionCount', 0)
            if 'follow' in name and 'ing' not in name:
                followers = int(count) if count else 0

        return {
            'username': ld.get('alternateName', username),
            'full_name': ld.get('name', 'N/A'),
            'bio': ld.get('description', ''),
            'followers': followers,
            'following': 0,
            'posts': 0,
            'is_private': False,
            'is_verified': False,
            'is_business': False,
            'profile_pic_hd': ld.get('image', ''),
            'profile_pic': '',
            'external_url': ld.get('url', ''),
            'category': 'N/A',
            'id': ld.get('identifier', 'N/A'),
            'highlight_reel_count': 0,
        }

    # ========== MAIN FETCH ==========
    def fetch_profile(self, username):
        username = username.strip().replace('@', '')

        # الطريقة 1: Instaloader (الأكثر ثباتاً)
        data = self._try_instaloader(username)
        if data:
            return data

        # الطريقة 2: API مباشر
        data = self._try_api(username)
        if data:
            return data

        # الطريقة 3: HTML scraping
        data = self._try_html(username)
        if data:
            return data

        return None

    # ========== DISPLAY ==========
    def _fmt(self, num):
        if num is None: return '0'
        return f"{num:,}"

    def display(self, data):
        os.system('clear' if os.name == 'posix' else 'cls')

        print(f"""
    {C.P}╔══════════════════════════════════════════════╗
    ║           {C.BL}C A M O R O  v3.0{C.RE}{C.P}                  ║
    ║       Instagram Profile Scanner            ║
    ╚══════════════════════════════════════════════╝{C.RE}
""")

        # Status
        priv = f"{C.R}PRIVATE 🔒{C.RE}" if data['is_private'] else f"{C.G}PUBLIC 🌐{C.RE}"
        parts = [f"Status: {priv}"]
        if data['is_verified']: parts.append(f"{C.B}VERIFIED ✓{C.RE}")
        if data['is_business']: parts.append(f"{C.Y}BUSINESS{C.RE}")
        if data.get('_source'): parts.append(f"{C.C}[{data['_source']}]{C.RE}")
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

        if data.get('bio'):
            print(f"\n  {C.Y}{C.BL}📝 Bio:{C.RE}")
            for line in textwrap.wrap(data['bio'], width=46):
                print(f"  {C.W}{line}{C.RE}")

        if data.get('external_url'):
            print(f"\n  {C.C}{C.BL}🔗 External URL:{C.RE}")
            print(f"  {C.W}{data['external_url']}{C.RE}")

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
{C.RE}{C.W}                    Version 3.0 | July 2026
{C.RE}
""")


def save_json(data, username):
    fname = f"camoro_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return fname


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', help='Target username')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    parser.add_argument('-o', '--output', help='Output JSON file')
    args = parser.parse_args()

    os.system('clear' if os.name == 'posix' else 'cls')
    banner()

    # تحقق من المكتبات
    try:
        import instaloader
        cprint("[✓] instaloader: AVAILABLE", C.G)
    except ImportError:
        cprint("[!] instaloader not installed!", C.Y)
        cprint("    Run: pip3 install instaloader", C.Y)

    try:
        from curl_cffi import requests
        cprint("[✓] curl_cffi: AVAILABLE", C.G)
    except ImportError:
        cprint("[!] curl_cffi not installed (optional)", C.Y)
        cprint("    Run: pip3 install curl_cffi", C.Y)

    camoro = Camoro(debug=args.debug)
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
            print(f"\n{C.C}═══ Fetching: @{target} ═══{C.RE}\n")

            data = camoro.fetch_profile(target)

            if data is None:
                cprint(f"\n[✗] FAILED - All 3 methods exhausted", C.R)
                cprint("\n[!] الأسباب المحتملة:", C.Y)
                print("  1. الحساب خاص (Private) أو غير موجود")
                print("  2. الإنستقرام حاجب IP حقك - جرب VPN")
                print("  3. تأكد من تثبيت: pip3 install instaloader curl_cffi")
                print("  4. جرب مع وضع التصحيح: python3 camoro.py -d -u username")
            else:
                camoro.display(data)

                if args.output:
                    f = save_json(data, target)
                    cprint(f"[✓] Saved: {f}", C.G)
                else:
                    sv = input(f"{C.G}[?]{C.RE} Save to file? {C.W}(y/n){C.RE}: ").strip().lower()
                    if sv in ['y', 'yes', 'نعم']:
                        f = save_json(data, target)
                        cprint(f"[✓] Saved: {f}", C.G)

            if args.username:
                sys.exit(0)

            target = None
            again = input(f"\n{C.G}[?]{C.RE} Scan another? {C.W}(y/n){C.RE}: ").strip().lower()
            if again not in ['y', 'yes', 'نعم']:
                cprint("\n👋 Goodbye!", C.P)
                sys.exit(0)

        except KeyboardInterrupt:
            cprint("\n\n👋 Goodbye!", C.Y)
            sys.exit(0)
        except Exception as e:
            cprint(f"\n[✗] Error: {e}", C.R)
            if args.debug:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
