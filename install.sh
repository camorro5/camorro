#!/bin/bash
# GhostMedia Installation Script
# Works on: Termux (Android) and Linux

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  GhostMedia Framework - Installation${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Detect platform
if [ -d "/data/data/com.termux/files/usr" ]; then
    PLATFORM="termux"
    echo -e "${GREEN}[+] Termux detected${NC}"
elif [ "$(uname -s)" = "Linux" ]; then
    PLATFORM="linux"
    echo -e "${GREEN}[+] Linux detected${NC}"
else
    PLATFORM="unknown"
    echo -e "${YELLOW}[!] Unknown platform. Proceeding anyway...${NC}"
fi

# Install Python if needed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}[*] Installing Python3...${NC}"
    if [ "$PLATFORM" = "termux" ]; then
        pkg install python -y
    elif [ "$PLATFORM" = "linux" ]; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip
    fi
fi

# Install pip if needed
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${YELLOW}[*] Installing pip...${NC}"
    if [ "$PLATFORM" = "termux" ]; then
        pkg install python-pip -y
    elif [ "$PLATFORM" = "linux" ]; then
        sudo apt-get install -y python3-pip
    fi
fi

PIP=$(command -v pip3 || command -v pip)

# Install Python dependencies
echo -e "${YELLOW}[*] Installing Python packages...${NC}"
$PIP install --upgrade pip
$PIP install -r requirements.txt

# Check for Metasploit
echo ""
echo -e "${YELLOW}[*] Checking for Metasploit (optional)...${NC}"
if command -v msfvenom &> /dev/null; then
    echo -e "${GREEN}[+] msfvenom found${NC}"
else
    echo -e "${YELLOW}[!] msfvenom not found. Built-in ARM64 stager will be used.${NC}"
    echo -e "${YELLOW}    Install Metasploit for more payload options:${NC}"
    if [ "$PLATFORM" = "termux" ]; then
        echo -e "    pkg install unstable-repo && pkg install metasploit"
    else
        echo -e "    curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && bash msfinstall"
    fi
fi

# Make scripts executable
chmod +x ghostmedia.py

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Usage Examples:"
echo -e "  ${CYAN}# Exploit Mode${NC}"
echo -e "  python ghostmedia.py --format webp --lhost <IP> --lport <PORT>"
echo -e "  python ghostmedia.py --format all --lhost <IP> --lport <PORT>"
echo -e ""
echo -e "  ${CYAN}# Proxy Mode${NC}"
echo -e "  python ghostmedia.py --fetch-proxies --proxy-count 50 --min-anonymity HIA"
echo -e ""
echo -e "  ${CYAN}# AI Mode${NC}"
echo -e "  python ghostmedia.py --analyze-target"
echo -e "  python ghostmedia.py --full-diag"
echo -e "  python ghostmedia.py --diagnose \"your error here\""
echo ""
