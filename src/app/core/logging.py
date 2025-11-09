import logging, sys

def _configure_root_logger() -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

_configure_root_logger()

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
