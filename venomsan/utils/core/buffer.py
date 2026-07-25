"""Buffer Overflow Detection - Checks for services vulnerable to buffer overflow."""
import asyncio, socket, struct
from ..utils.helpers import status, random_str
from ..utils.network import COMMON_PORTS, resolve_host

class BufferOverflowTester:
    """Detects services potentially vulnerable to buffer overflow."""

    # Services commonly vulnerable
    TARGET_SERVICES = [
        {"port":21,"service":"FTP","probe":b"USER " + b"A" * 500 + b"\r\n"},
        {"port":25,"service":"SMTP","probe":b"EHLO " + b"A" * 2000 + b"\r\n"},
        {"port":110,"service":"POP3","probe":b"USER " + b"A" * 2000 + b"\r\n"},
        {"port":143,"service":"IMAP","probe":b"A001 LOGIN " + b"A" * 1000 + b" test\r\n"},
        {"port":80,"service":"HTTP","probe":b"GET /" + b"A" * 4000 + b" HTTP/1.0\r\n\r\n"},
        {"port":443,"service":"HTTPS","probe":b"\x16\x03\x01" + b"\x00" * 2000},
    ]

    def __init__(self, target: str, timeout: float = 5.0):
        self.target = target
        self.timeout = timeout
        self.vulnerable = []

    async def test_service(self, host: str, port: int, service: str, probe: bytes) -> dict:
        """Test a single service for BO vulnerability indication."""
        result = {"host":host,"port":port,"service":service,"vulnerable":False,"evidence":None}

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=self.timeout
            )

            # Read banner first
            try:
                banner = await asyncio.wait_for(reader.read(4096), timeout=2.0)
            except: banner = b""

            # Send oversized payload
            writer.write(probe)
            await writer.drain()

            # Check response
            try:
                response = await asyncio.wait_for(reader.read(4096), timeout=3.0)
                # If server crashes, connection drops
                if len(response) == 0:
                    result["vulnerable"] = True
                    result["evidence"] = "Connection dropped after payload"
            except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError):
                result["vulnerable"] = True
                result["evidence"] = "Connection lost after payload (possible crash)"

            writer.close()
            try: await writer.wait_closed()
            except: pass

        except Exception as e:
            pass

        return result

    async def scan(self) -> list:
        """Scan target for BO-prone services."""
        host = resolve_host(self.target) or self.target
        status(f"Testing {host} for buffer overflow prone services...", "info")

        tasks = []
        for svc in self.TARGET_SERVICES:
            tasks.append(self.test_service(host, svc["port"], svc["service"], svc["probe"]))

        results = []
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            if r["vulnerable"]:
                self.vulnerable.append(r)
                status(f"Potential BO: {r['service']} on port {r['port']}", "warning")

        status(f"BO scan: {len(self.vulnerable)} potential target(s)", "success")
        return self.vulnerable
