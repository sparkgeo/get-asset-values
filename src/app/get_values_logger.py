"""
Setup logging
"""

import logging

logger = logging.getLogger("getvalues_logger")
logger.setLevel(logging.INFO)

log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# add a file handler
file_handler = logging.FileHandler("/tmp/app.log")
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

# Check if a StreamHandler already exists
if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_format)
    logger.addHandler(stream_handler)

for handler in logger.handlers:
    handler.setFormatter(log_format)
