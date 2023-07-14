import logging
import os
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

path = Path("./log")
path.mkdir(exist_ok=True)
file = open(path / f"{date.today()}.log", "a+", encoding="utf8")

debug = os.environ.get("DEBUG")
console = Console(file=file)
console_formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d │ %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
h1 = RichHandler(rich_tracebacks=True, tracebacks_show_locals=True, show_time=False)
h2 = RichHandler(
    console=console, rich_tracebacks=True, tracebacks_show_locals=True, show_time=False
)
h1.setFormatter(console_formatter)
h2.setFormatter(console_formatter)
logging.basicConfig(
    level=(logging.DEBUG if debug is not None else logging.WARNING),
    handlers=[h1, h2],
    force=True,
)
logger = logging.getLogger()
