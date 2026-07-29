# 🔥 HikCam-Hijack — Hikvision IP Camera Exploitation Tool

**Zero Bruteforce — 100% Cookie Bypass & Direct Endpoint Access**

اختراق كاميرات Hikvision IP بدون الحاجة لكلمة سر ولا تخمين.
يعتمد على ثغرات مصادقة معروفة (CVE-2013-4976) و endpoints مكشوفة.

---

## ⚡ المميزات

| الميزة | الوصف |
|--------|-------|
| 🍪 **Cookie Bypass** | تزوير كوكي anonymous وتجاوز اللوجن بالكامل (CVE-2013-4976) |
| 🚪 **Direct Endpoint Access** | الوصول المباشر لصفحات الإدارة الحساسة بدون مصادقة |
| ⬇️ **Config Download** | سحب ملف الإعدادات الكامل (فيه كل كلمات السر مشفرة ومشفوفة) |
| 📸 **Snapshot Capture** | التقاط صورة حية من كاميرات المراقبة عن بعد |
| 📡 **RTSP Stream Detection** | كشف روابط البث المباشر وتشغيلها في VLC |
| 💉 **Config Injection** | رفع ملف إعدادات معدّل لتغيير باسورد admin (اختياري) |
| 🔑 **Credential Extraction** | استخراج كل creds الموجودة في ملف الإعدادات |
| 🔌 **Multi-Port Support** | يدعم أي بورت HTTP (80, 8080, 8000, إلخ) |

---

## 📦 التثبيت

```bash
# استنساخ المستودع
git clone https://github.com/YOUR_USERNAME/HikCam-Hijack.git
cd HikCam-Hijack

# تثبيت المتطلبات
pip3 install requests
