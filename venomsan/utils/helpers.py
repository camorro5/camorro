"""Helper utilities for VenomScan."""
import random, string, hashlib, time, re, base64, json
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, quote
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

BANNER = r"""
██╗   ██╗███████╗███╗   ██╗ ██████╗ ███╗   ███╗
██║   ██║██╔════╝████╗  ██║██╔═══██╗████╗ ████║
██║   ██║█████╗  ██╔██╗ ██║██║   ██║██╔████╔██║
╚██╗ ██╔╝██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║
 ╚████╔╝ ███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
  ╚═══╝  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝
███████╗ ██████╗ █████╗ ███╗   ██╗
██╔════╝██╔════╝██╔══██╗████╗  ██║
███████╗██║     ███████║██╔██╗ ██║
╚════██║██║     ██╔══██║██║╚██╗██║
███████║╚██████╗██║  ██║██║ ╚████║
╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
"""

def print_banner():
    console.print(BANNER, style="bold #FF0000")
    console.print("  SQLi • XSS • LFI • RCE • CSRF • PrivEsc • Buffer Overflow", style="dim #FF4444")
    console.print()

def status(msg: str, level: str = "info"):
    colors = {"info":"blue","success":"green","warning":"yellow","error":"red","critical":"bold white on red"}
    prefix = {"info":"[*]","success":"[+]","warning":"[!]","error":"[-]","critical":"[!!!]"}
    console.print(f"[{colors.get(level,'white')}]{prefix.get(level,'[*]')} {msg}[/{colors.get(level,'white')}]")

def random_ua() -> str:
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1",
    ]
    return random.choice(agents)

def random_ip() -> str:
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def random_str(length: int = 12) -> str:
    return ''.join(random.choices(string.ascii_letters+string.digits, k=length))

def random_hex(length: int = 32) -> str:
    return ''.join(random.choices(string.hexdigits.lower(), k=length))

def timestamp() -> str:
    return datetime.now().isoformat()

def load_config(path: str = "config/venom.yaml") -> dict:
    p = Path(path)
    if p.exists():
        with open(p, "r") as f:
            return yaml.safe_load(f)
    return {}

def display_table(title: str, rows: list[dict], style: str = "cyan"):
    if not rows:
        status(f"No data: {title}", "warning")
        return
    table = Table(title=title, style=style, box=box.ROUNDED)
    for k in rows[0].keys():
        table.add_column(k.replace("_"," ").title(), style=style, no_wrap=False)
    for row in rows:
        table.add_row(*[str(v)[:80] for v in row.values()])
    console.print(table)

SEVERITY_COLORS = {"CRITICAL":"bold white on red","HIGH":"bold red","MEDIUM":"bold yellow","LOW":"blue","INFO":"dim"}

def severity_tag(sev: str) -> str:
    return f"[{SEVERITY_COLORS.get(sev,'white')}]{sev}[/{SEVERITY_COLORS.get(sev,'white')}]"

def cvss_score(av="N", ac="L", pr="N", ui="N", s="U", c_="H", i_="H", a_="H") -> float:
    av_m={"N":0.85,"A":0.62,"L":0.55,"P":0.2}
    ac_m={"L":0.77,"H":0.44}
    pr_m={"N":0.85,"L":0.62,"H":0.27}
    ui_m={"N":0.85,"R":0.62}
    base=av_m.get(av,0.85)*ac_m.get(ac,0.77)*pr_m.get(pr,0.85)*ui_m.get(ui,0.85)
    c_m={"H":0.56,"L":0.22,"N":0}
    i_m={"H":0.56,"L":0.22,"N":0}
    a_m={"H":0.56,"L":0.22,"N":0}
    impact=1-((1-c_m.get(c_,0))*(1-i_m.get(i_,0))*(1-a_m.get(a_,0)))
    if s=="C": impact=1.08*impact
    return min(10,round(base*impact*10,1))

def save_json(data, filepath):
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    status(f"Saved: {filepath}", "success")
