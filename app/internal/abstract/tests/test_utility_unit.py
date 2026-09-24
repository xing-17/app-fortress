from __future__ import annotations

import pytest

from app.internal.abstract.utility import IAbstractUtility


class TestIAbstractUtility:
    def test_instantiation_raises_type_error(self):
        with pytest.raises(TypeError):
            IAbstractUtility()
