# 🔥 SPID-Xploit v2.0 (مصحح بالكامل)

**AI-Powered SPID Penetration Testing Framework**  
Target: `spid.gov.it` Ecosystem | CVE-2025-24894 (CVSS 9.1) | CVE-2025-24895

> **⚠️ تنبيه قانوني:** هذه الأداة مخصصة فقط لاختبار الاختراق الأخلاقي (Ethical Hacking) على أنظمة تمتلك إذنًا رسميًا باختبارها. الاستخدام غير المصرح به يعتبر جريمة يعاقب عليها القانون.

---

## 📋 الوصف

SPID-Xploit هو إطار عمل متقدم لاختبار الاختراق مدعوم بالذكاء الاصطناعي، يستهدف نظام الهوية الرقمية الإيطالي (SPID). يقوم بأتمتة استغلال الثغرات الحرجة في نظام المصادقة SPID، بما في ذلك **CVE-2025-24894 (CVSS 9.1)** التي تسمح بتجاوز التحقق من توقيع SAML وانتحال هوية أي مستخدم.

### 🎯 الثغرات المستهدفة

| الثغرة | CVSS | الوصف | التأثير |
|--------|------|-------|---------|
| **CVE-2025-24894** | 9.1 (Critical) | SAML Signature Verification Bypass | انتحال هوية أي مستخدم SPID |
| **CVE-2025-24895** | 8.8 (High) | CIE SAML Signature Bypass | انتحال هوية عبر SAML |
| **CVE-2024-11758** | 6.4 (Medium) | WP SPID Italia Stored XSS | تنفيذ سكربتات في ووردبريس |

---

## 🚀 الميزات

### الوحدات (Modules)

| الوحدة | الوصف |
|--------|-------|
| **AI Reconnaissance** | OSINT، فحص DNS، بصمة التقنيات، تحليل SSL/TLS |
| **Registry Scraper** | استخراج كل كيانات SPID (+5000) من السجل الرسمي |
| **CVE-2025-24894 Exploit** | استغلال SAML Signature Bypass مع التقنية الصحيحة لحقن التوقيع |
| **SAML Forger AI** | تزوير استجابات SAML ببيانات مستخدمين إيطاليين واقعيين |
| **Metadata Analyzer** | تحليل شهادات IdP/SP، التحقق من انتهاء الصلاحية، نقاط الضعف |
| **Payload Generator** | توليد Payloads SAML و XSS مع طفرات ذكية للتهرب |
| **Full Attack Chain** | هجوم متكامل أوتوماتيكي: Recon → Scrape → Analyze → Exploit → Report |

### 🎯 بيئة الهدف

| الهدف | الرابط | الدور |
|-------|--------|-------|
| SPID Website | https://www.spid.gov.it | البوابة الرسمية (WordPress, nginx/1.26.2) |
| SAML Validator | https://validator.spid.gov.it | مدقق بروتوكول SAML/OIDC |
| Demo Environment | https://demo.spid.gov.it | بيئة اختبار IdP |
| Federation Registry | https://registry.spid.gov.it | سجل الكيانات (IdPs, SPs, AAs) |
| Admin Portal | https://login.agid.gov.it | نظام الدخول المركزي / SPID OnBoarding |
| AgID Official | https://www.agid.gov.it | الموقع الرسمي للجهة المشرفة |

---

## 🔥 CVE-2025-24894 - شرح الثغرة

### آلية الاستغلال الصحيحة (CORRECTED)

هذه الثغرة موجودة في مكتبة `SPID.AspNetCore.Authentication` (إصدار ≤ 3.3.0). دالة `VerifySignature` تتحقق فقط من أول توقيع XML (`nodeList[0]`) بغض النظر عن موقعه أو سياقه.
1 ---

## 💻 التثبيت

### Linux (Kali/Ubuntu/Debian)

```bash
git clone https://github.com/tracciamento1/tracciamento-.git
cd tracciamento-
chmod +x install.sh
sudo bash install.sh
pkg install git -y
git clone https://github.com/tracciamento1/tracciamento-.git
cd tracciamento-
bash install.sh

pip install -r requirements.txt
python3 main.py -i
python3 main.py -i
# استطلاع
python3 main.py -m recon

# استغلال CVE-2025-24894
python3 main.py -m cve_2025_24894

# سحب سجل SPID
python3 main.py -m registry

# تزوير استجابات SAML
python3 main.py -m saml_forger


# هجوم كامل أوتوماتيكي
python3 main.py -m full_attack

# تقرير
python3 main.py -m report
python3 main.py -m cve_2025_24894 -t https://login.agid.gov.it


