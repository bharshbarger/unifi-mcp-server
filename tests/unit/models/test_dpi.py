"""Unit tests for DPI models."""

import pytest
from pydantic import ValidationError

from src.models.dpi import DPIApplication, DPICategory


def _payload(**overrides):
    payload = {"_id": "cat-123", "name": "Streaming"}
    payload.update(overrides)
    return payload


def _app_payload(**overrides):
    payload = {"_id": "app-123", "name": "ICQ"}
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


class TestDPIApplicationCoercion:
    """DPIApplication has the same int-id pattern as DPICategory, plus the
    controller often omits category_id entirely — the model must accept
    both shapes."""

    def test_int_id_coerces_to_str(self):
        app = DPIApplication(**_app_payload(_id=3))
        assert app.id == "3"

    def test_int_category_id_coerces_to_str(self):
        app = DPIApplication(**_app_payload(category_id=24))
        assert app.category_id == "24"

    def test_missing_category_id_is_allowed(self):
        # Wire shape observed live: {'id': 3, 'name': 'ICQ'} with no
        # category_id at all. Was crashing before the field was made Optional.
        app = DPIApplication(**_app_payload(_id=3))
        assert app.id == "3"
        assert app.category_id is None

    def test_string_ids_pass_through(self):
        app = DPIApplication(**_app_payload(_id="app-abc", category_id="cat-xyz"))
        assert app.id == "app-abc"
        assert app.category_id == "cat-xyz"
