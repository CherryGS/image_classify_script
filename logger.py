import logging
import os

from rich.logging import RichHandler
from datetime import date

debug = os.environ.get("DEBUG")
logging.basicConfig(
    level=(logging.DEBUG if debug is not None else logging.INFO),
    handlers=[
        RichHandler(rich_tracebacks=True, tracebacks_show_locals=True),
        logging.FileHandler(f"./log/{date.today()}.log"),
    ],
)
logger = logging.getLogger()
