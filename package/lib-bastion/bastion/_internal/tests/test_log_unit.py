"""Unit tests for IBastionLog."""

from __future__ import annotations

import logging

from bastion._internal.log import IBastionLog


def test_get_logger_root():
    """Test getting the root bastion logger."""
    logger = IBastionLog.get_logger()
    assert logger.name == "bastion"
    assert isinstance(logger, logging.Logger)


def test_get_logger_named():
    """Test getting a named child logger."""
    logger = IBastionLog.get_logger("test_module")
    assert logger.name == "bastion.test_module"
    assert isinstance(logger, logging.Logger)


def test_get_logger_hierarchy():
    """Test logger hierarchy is maintained."""
    parent_logger = IBastionLog.get_logger("parent")
    child_logger = IBastionLog.get_logger("parent.child")
    assert parent_logger.name == "bastion.parent"
    assert child_logger.name == "bastion.parent.child"
    assert child_logger.parent == parent_logger


def test_get_logger_empty_string():
    """Test that empty string returns root logger."""
    logger = IBastionLog.get_logger("")
    assert logger.name == "bastion"
