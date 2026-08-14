from __future__ import annotations

import json


class IBastionObject:
    """
    Base class providing serialization utilities for objects.

    Methods:
        export(): Exports the object metadata to a dictionary.
        describe(): Returns a JSON string representation of the object.

    Example:
        ```python
        from bastion._internal.object import IBastionObject

        class MyObject(IBastionObject):
            def __init__(self, name):
                self.name = name

        obj = MyObject("example")
        print(obj.describe())
        # Output: {"__class__": "MyObject", "__module__": "__main__"}
        ```
    """

    def export(self) -> dict:
        """Export the object metadata to a dictionary."""
        return {
            "__class__": self.__class__.__name__,
            "__module__": self.__class__.__module__,
        }

    def describe(self) -> str:
        """Return a JSON string representation of the object."""
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
            default=str,
        )
