import logging
import sys
from pathlib import Path

LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

# On Windows the default stdout/stderr encoding is cp1252, which blows up on
# the Unicode box-drawing glyphs we print ("├── ...") and on any subtitle in
# non-latin scripts. Switch both streams to UTF-8 so logs and prints work the
# same locally and in CI (Linux is UTF-8 by default, so this is a no-op there).
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Some test harnesses replace stdout with objects that don't
            # support reconfigure(); falling back silently is fine.
            pass

# Format choices, optimized for scanning logs during CI runs:
#  - time only (HH:MM:SS): a run lasts minutes, the full date is noise;
#  - fixed-width level (7 chars) so columns line up;
#  - logger name (e.g. "src.poster"), not "module | funcName | line N",
#    which was mostly redundant for our one-file-per-module layout.
# The file and line that produced the record are still available via
# ``logger.error(..., exc_info=True)`` tracebacks when something breaks.
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s %(levelname)-7s %(name)-18s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

