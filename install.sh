#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}[*] Installing IG Security Tool...${NC}"

if command -v pkg &>/dev/null; then
    pkg update -y
    pkg install python python-pip coreutils -y
elif command -v apt &>/dev/null; then
    sudo apt update -y
    sudo apt install python3 python3-pip -y
fi

pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}[+] Installation complete!${NC}"
echo -e "${GREEN}[+] Run: python3 igtool.py${NC}"
