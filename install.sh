#!/bin/bash
# ============================================================
# SPID-Xploit v2.0 - AI-Powered SPID Penetration Framework
# Advanced Installer for Linux (Kali/Ubuntu/Debian) & Termux
# ============================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║          SPID-Xploit v2.0 - AI EDITION          ║"
    echo "║     Italian SPID Penetration Testing Framework   ║"
    echo "║     CVE-2025-24894 | CVE-2025-24895 Exploits    ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    sleep 1
}

check_termux() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        return 0
    else
        return 1
    fi
}

install_system_deps() {
    echo -e "${GREEN}[+] Installing system dependencies...${NC}"
    
    if check_termux; then
        echo -e "${YELLOW}[!] Detected Termux environment${NC}"
        pkg update -y
        pkg upgrade -y
        pkg install -y python python-pip git curl wget openssl-tool
        pkg install -y binutils rust cmake make clang
        pkg install -y libxml2 libxslt libffi
        pkg install -y nmap netcat-openbsd
    else
        echo -e "${YELLOW}[!] Detected Linux environment${NC}"
        sudo apt update -y
        sudo apt upgrade -y
        sudo apt install -y python3 python3-pip python3-dev
        sudo apt install -y git curl wget openssl netcat-openbsd
        sudo apt install -y build-essential libssl-dev libffi-dev
        sudo apt install -y libxml2-dev libxslt1-dev
        sudo apt install -y nmap jq
        sudo apt install -y python3-venv
    fi
    
    echo -e "${GREEN}[✓] System dependencies installed${NC}"
}

install_python_deps() {
    echo -e "${GREEN}[+] Installing Python dependencies...${NC}"
    
    # Create virtual environment if not in Termux
    if ! check_termux; then
        python3 -m venv spid-xploit-env 2>/dev/null
        source spid-xploit-env/bin/activate 2>/dev/null
    fi
    
    # Upgrade pip
    python3 -m pip install --upgrade pip --quiet
    
    # Core dependencies
    echo -e "${CYAN}  → Installing core packages...${NC}"
    pip install requests==2.31.0 --quiet
    pip install beautifulsoup4==4.12.3 --quiet
    pip install lxml==5.1.0 --quiet
    
    # Crypto dependencies
    echo -e "${CYAN}  → Installing cryptography packages...${NC}"
    pip install cryptography==41.0.7 --quiet
    pip install pycryptodome==3.20.0 --quiet
    pip install signxml==7.0.2 --quiet
    pip install xmlsec==1.3.14 --quiet
    
    # XML parsing
    echo -e "${CYAN}  → Installing XML packages...${NC}"
    pip install elementpath==4.4.0 --quiet
    pip install xmlschema==3.4.1 --quiet
    
    # AI & ML dependencies
    echo -e "${CYAN}  → Installing AI/ML packages...${NC}"
    pip install numpy==1.26.3 --quiet
    pip install pandas==2.1.5 --quiet
    pip install scikit-learn==1.4.0 --quiet
    
    # Try to install transformers (might fail on Termux)
    pip install transformers==4.36.2 --quiet 2>/dev/null || {
        echo -e "${YELLOW}[!] Transformers not available, using fallback AI${NC}"
        pip install onnxruntime==1.16.3 --quiet 2>/dev/null || true
    }
    
    # Try torch (might fail on Termux)
    pip install torch==2.1.2 --quiet 2>/dev/null || {
        echo -e "${YELLOW}[!] PyTorch not available, using scikit-learn fallback${NC}"
    }
    
    # CLI and UI
    echo -e "${CYAN}  → Installing CLI packages...${NC}"
    pip install rich==13.7.0 --quiet
    pip install colorama==0.4.6 --quiet
    pip install art==6.1.0 --quiet
    pip install tqdm==4.66.1 --quiet
    pip install prompt_toolkit==3.0.43 --quiet
    
    # Networking
    echo -e "${CYAN}  → Installing networking packages...${NC}"
    pip install dnspython==2.6.1 --quiet
    pip install scapy==2.5.0 --quiet 2>/dev/null || true
    
    echo -e "${GREEN}[✓] Python dependencies installed${NC}"
}

create_directories() {
    echo -e "${GREEN}[+] Creating project directories...${NC}"
    
    mkdir -p modules
    mkdir -p data/idps
    mkdir -p data/payloads
    mkdir -p data/captured
    mkdir -p data/logs
    mkdir -p reports
    
    # Create __init__.py for modules package
    touch modules/__init__.py
    
    # Set permissions
    chmod -R 755 modules/
    chmod -R 777 data/
    chmod -R 777 reports/
    
    echo -e "${GREEN}[✓] Directories created${NC}"
}

check_existing_files() {
    echo -e "${GREEN}[+] Checking existing files...${NC}"
    
    required_files=(
        "main.py"
        "modules/__init__.py"
        "modules/ai_engine.py"
        "modules/cve_2025_24894.py"
        "modules/metadata_parser.py"
        "modules/payload_generator.py"
        "modules/recon.py"
        "modules/registry_scraper.py"
        "modules/saml_forger.py"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}[!] Missing file: $file${NC}"
            echo -e "${YELLOW}[!] Please ensure all source files are present${NC}"
            return 1
        fi
    done
    
    echo -e "${GREEN}[✓] All required files present${NC}"
    return 0
}

print_success() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        SPID-Xploit INSTALLED SUCCESSFULLY!            ║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  Usage:                                               ║${NC}"
    echo -e "${GREEN}║  python3 main.py --interactive                        ║${NC}"
    echo -e "${GREEN}║  python3 main.py -m recon                             ║${NC}"
    echo -e "${GREEN}║  python3 main.py -m cve_2025_24894                    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Main execution
main() {
    banner
    
    # Check if running as root (not needed for Termux)
    if ! check_termux; then
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}[!] Some features require root. Consider running with sudo.${NC}"
            sleep 2
        fi
    fi
    
    install_system_deps
    install_python_deps
    create_directories
    check_existing_files
    
    if [ $? -eq 0 ]; then
        print_success
    else
        echo -e "${RED}[!] Installation completed with warnings${NC}"
        echo -e "${YELLOW}[!] Please ensure all source files are in place${NC}"
    fi
}

# Run
main
