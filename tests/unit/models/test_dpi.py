"""Unit tests for DPI models."""

import pytest
from pydantic import ValidationError

from src.models.dpi import DPICategory


def _payload(**overrides):
    payload = {"_id": "cat-123", "name": "Streaming"}
    payload.update(overrides)
    return payload


class TestDPICategoryIdCoercion:
    """The local controller returns DPI category ids as bare ints
    (e.g. 0, 1, 2) for system-defined categories; the model declares
    str so callers can treat all id fields uniformly."""

    def test_int_id_coerces_to_str(self):
        cat = DPICategory(**_payload(_id=0))
        assert cat.id == "0"
        assert isinstance(cat.id, str)

    def test_large_int_id_coerces_to_str(self):
        cat = DPICategory(**_payload(_id=42))
        assert cat.id == "42"

    def test_string_id_passes_through(self):
        cat = DPICategory(**_payload(_id="cat-abc"))
        assert cat.id == "cat-abc"

    def test_numeric_string_id_passes_through(self):
        cat = DPICategory(**_payload(_id="7"))
        assert cat.id == "7"

    def test_bool_id_rejected(self):
        # Bools are technically a subclass of int in Python; they should
        # not silently coerce to "True"/"False" via this validator.
        with pytest.raises(ValidationError):
            DPICategory(**_payload(_id=True))

    def test_none_id_rejected(self):
        with pytest.raises(ValidationError):
            DPICategory(**_payload(_id=None))
