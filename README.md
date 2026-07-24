# 🎯 Camoro - Instagram Profile Scanner

**Camoro** is an OSINT reconnaissance tool for gathering public Instagram profile information. Designed for security professionals and penetration testers.

## ⚠️ Legal Disclaimer

This tool is intended for **authorized security testing only**. Only use against accounts you own or have explicit written permission to test. The user assumes all responsibility for lawful usage.

## ✨ Features

- 📊 **Follower/Following/Posts count** extraction
- 🔒 **Private/Public account detection**
- ✓ **Verified account detection**
- 📝 **Bio & External URL extraction**
- 🖼️ **HD Profile picture URL retrieval**
- 💾 **JSON export** of results
- 🎨 **Beautiful colored terminal UI**
- 🔄 **Multiple fallback extraction methods**
- 📱 **Cross-platform**: Termux, Linux, iSH, macOS, Windows

## 📦 Installation

### Termux
```bash
pkg update && pkg install git python3 -y
git clone https://github.com/YOUR_USERNAME/camoro.git
cd camoro
bash setup.sh
