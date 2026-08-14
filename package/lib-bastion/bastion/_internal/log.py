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
    Logger accessor.

    Returns a child of the root ``bastion`` logger.
    """

    @staticmethod
    def get_logger(name: str = "") -> logging.Logger:
        _name = f"bastion.{name}" if name else "bastion"
        return logging.getLogger(_name)
