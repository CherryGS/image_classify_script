import logging
import os
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

path = Path("./log")
path.mkdir(exist_ok=True)
idx = 0
while True:
    log = path / f"{date.today()}-{idx}.log"
    if not log.is_file():
        path = log
        break
    elif os.path.getsize(log) / 1024 / 1024 < 10:
        path = log
        break
    else:
        idx += 1
file = open(path, "a+", encoding="utf8")


debug = os.environ.get("DEBUG")
level = logging.DEBUG if debug else logging.INFO
console = Console(file=file)
console_formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d │ %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
h1 = RichHandler(
    rich_tracebacks=True,
    tracebacks_show_locals=True,
    show_time=False,
    markup=True,
)
h2 = RichHandler(
    console=console,
    rich_tracebacks=True,
    tracebacks_show_locals=True,
    show_time=False,
    markup=True,
)
h1.setLevel(level)
h2.setLevel(logging.DEBUG)
h1.setFormatter(console_formatter)
h2.setFormatter(console_formatter)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[h1, h2],
    force=True,
)
logger = logging.getLogger()
