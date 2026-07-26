#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "[*] Installing CAMORO..."
pkg update -y 2>/dev/null || true
pkg install -y python python-pip 2>/dev/null || true
pip install -r requirements.txt || pip3 install -r requirements.txt
chmod +x camoro.py 2>/dev/null || true
mkdir -p output core/ai
echo ""
echo "[+] CAMORO ready. Run: python3 camoro.py"
