#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "[*] Installing IGTOOL with AI Controller..."
pkg update -y 2>/dev/null || true
pkg install -y python python-pip 2>/dev/null || true
pip install -r requirements.txt || pip3 install -r requirements.txt
chmod +x igtool.py 2>/dev/null || true
mkdir -p output core/ai
echo "[+] Done. Run: python3 igtool.py"
