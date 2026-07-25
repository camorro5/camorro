#!/usr/bin/env bash
# Camoro installer — Linux & Termux

set -e
echo "[*] Installing Camoro dependencies..."

if command -v pkg >/dev/null 2>&1; then
  pkg update -y
  pkg install -y python git
elif command -v apt-get >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git
  else
    apt-get update -y
    apt-get install -y python3 python3-pip python3-venv git
  fi
fi

python3 -m pip install --upgrade pip -q 2>/dev/null || pip install --upgrade pip -q 2>/dev/null || true
python3 -m pip install -r requirements.txt 2>/dev/null || pip install -r requirements.txt

chmod +x camoro.py install.sh 2>/dev/null || true
echo "[+] Camoro ready."
echo "    python3 camoro.py -u TARGET"
