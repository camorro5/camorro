"""Network utilities."""
import asyncio, socket, struct, random, ipaddress
from typing import Optional, Tuple
from urllib.parse import urlparse

def validate_target(target: str) -> Tuple[bool, str]:
    target = target.strip()
    try:
        ipaddress.ip_address(target)
        return True, target
    except ValueError:
        pass
    if len(target) <= 255 and all(c.isalnum() or c in ".-" for c in target):
        return True, target
    return False, f"Invalid: {target}"

def resolve_host(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None

def parse_url(url: str) -> dict:
    if not url.startswith(("http://","https://")):
        url = f"https://{url}"
    p = urlparse(url)
    return {"scheme":p.scheme,"hostname":p.hostname,"port":p.port or (443 if p.scheme=="https" else 80),"path":p.path or "/"}

async def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        _, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        w.close()
        await w.wait_closed()
        return True
    except:
        return False

COMMON_PORTS = {21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",110:"POP3",143:"IMAP",443:"HTTPS",993:"IMAPS",995:"POP3S",3306:"MySQL",3389:"RDP",5432:"PostgreSQL",6379:"Redis",8080:"HTTP-Proxy",8443:"HTTPS-Alt",9200:"Elasticsearch",27017:"MongoDB"}
