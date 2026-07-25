# 🐍 VenomScan v2.0

**أقوى أداة اختراق تطبيقات ويب - SQLi, XSS, LFI, RCE, CSRF, PrivEsc, Buffer Overflow**

## ⚠️ AUTHORIZATION REQUIRED
للاستخدام المرخص فقط مع إذن كتابي مسبق.

## ✨ المميزات

### 🔍 الاستطلاع
- كشف CMS: Joomla, WordPress, Drupal, Magento
- تعداد الإضافات والمكونات
- كشف WAF: Cloudflare, ModSecurity, AWS, Akamai
- فحص المنافذ السريع

### 💣 الثغرات
- **SQL Injection**: Auth bypass, Union, Error, Time, Boolean
- **XSS**: Reflected, Stored, DOM, Polyglot
- **LFI/RFI**: Path traversal, PHP wrappers
- **CSRF**: Missing token detection
- **Command Injection**: Unix/Windows
- **Buffer Overflow**: Detection for common services

### 🔓 الاستغلال
- **Brute Force**: Joomla/WordPress admin panels
- **RCE**: Template modification, webshell deployment
- **Privilege Escalation**: Linux & Windows vectors
- **DNS Exfiltration**: Data theft via DNS

### 🛡️ التخفي
- User-Agent rotation
- IP spoofing (X-Forwarded-For)
- Adaptive rate limiting
- Multi-layer payload encoding
- WAF bypass engine
- Local AI analysis

## 📦 التثبيت

```bash
git clone https://github.com/your-username/VenomScan.git
cd VenomScan
pip install -r requirements.txt
pip install .
