"""
Logging bootstrap for the bastion package.

Attaches a NullHandler to the root ``bastion`` logger so the library stays
silent by default.  Callers configure handlers in their own application code.
"""

from __future__ import annotations

import logging

logging.getLogger("bastion").addHandler(logging.NullHandler())


class IBastionLog:
    """
    Provides logger accessor for the bastion package.

    Methods:
        get_logger(str name): Returns a child logger of the root bastion logger.

    Example:
        ```python
        from bastion._internal.log import IBastionLog

        # Get root bastion logger
        logger = IBastionLog.get_logger()

        # Get named logger
        module_logger = IBastionLog.get_logger("module_name")
        module_logger.info("Log message")
        ```
    """

    @staticmethod
    def get_logger(name: str = "") -> logging.Logger:
        """Return a child logger of the root bastion logger."""
        _name = f"bastion.{name}" if name else "bastion"
        return logging.getLogger(_name)
