# 📱 SMS-Grabber

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-red)
![Android](https://img.shields.io/badge/Android-5.0%2B-brightgreen)
![Kotlin](https://img.shields.io/badge/Kotlin-1.9.22-purple)
![License](https://img.shields.io/badge/license-MIT-blue)

**Advanced Android SMS Interception & Forwarding Tool**
<br>
*For Authorized Security Research & Penetration Testing Only*

</div>

---

## ⚠️ DISCLAIMER

> **This tool is strictly for authorized security testing and educational purposes.**
>
> Unauthorized use of this software to intercept communications without explicit consent is illegal and violates privacy laws in most jurisdictions including but not limited to:
> - Computer Fraud and Abuse Act (CFAA) - USA
> - General Data Protection Regulation (GDPR) - EU
> - Telecommunications Act violations
> - State/local wiretapping statutes
>
> **The developer assumes NO liability for misuse. Use responsibly and legally.**

---

## 🎯 Overview

SMS-Grabber is a stealth Android application designed for **authorized** SMS penetration testing and red team engagements. It operates invisibly in the background, intercepting all incoming SMS messages and forwarding them to a Telegram bot in real-time.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| 🔇 **Full Stealth Mode** | No app icon in launcher, transparent activity, hidden from recents |
| 📩 **SMS Interception** | Highest broadcast priority (2147483647) — captures SMS before any other app |
| 🔄 **Auto-Restart** | Persists across reboots via `BOOT_COMPLETED` receiver |
| 🛡️ **Anti-Kill** | Foreground service with Wakelock — survives system cleanup |
| 📲 **Telegram Forwarding** | Real-time SMS forwarding to your Telegram bot |
| 🔒 **Obfuscated Code** | ProGuard + R8 optimized, class names and strings obfuscated |
| 🌐 **Multi-Carrier** | Works across all GSM/CDMA carriers globally |

---

## 🏗️ Architecture
