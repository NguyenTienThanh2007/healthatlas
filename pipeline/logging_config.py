from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str = "INFO") -> logging.Logger:
    root = Path(__file__).resolve().parents[1]
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("healthatlas.pipeline")
    logger.setLevel(getattr(logging, level, logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_dir / "pipeline.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(stream)
    logger.addHandler(file_handler)
    return logger
