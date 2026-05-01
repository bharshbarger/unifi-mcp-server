"""Unit tests for the Network model."""

import pytest
from pydantic import ValidationError

from src.models.network import Network


def _minimal_payload(**overrides):
    payload = {
        "_id": "507f191e810c19729de860ea",
        "name": "LAN",
        "purpose": "corporate",
    }
    payload.update(overrides)
    return payload


class TestNetworkVlanCoercion:
    """`vlan` from the local controller is sometimes returned as the empty string
    for VLAN-disabled networks; the model must treat that the same as missing."""

    def test_empty_string_vlan_coerces_to_none(self):
        net = Network(**_minimal_payload(vlan=""))
        assert net.vlan_id is None

    def test_whitespace_vlan_coerces_to_none(self):
        net = Network(**_minimal_payload(vlan="   "))
        assert net.vlan_id is None

    def test_missing_vlan_remains_none(self):
        net = Network(**_minimal_payload())
        assert net.vlan_id is None

    def test_integer_vlan_passes_through(self):
        net = Network(**_minimal_payload(vlan=2))
        assert net.vlan_id == 2

    def test_numeric_string_vlan_still_parses(self):
        # Pydantic's default int coercion handles "42" -> 42; the validator
        # must not eat numeric strings.
        net = Network(**_minimal_payload(vlan="42"))
        assert net.vlan_id == 42

    def test_non_numeric_non_blank_string_still_rejected(self):
        with pytest.raises(ValidationError):
            Network(**_minimal_payload(vlan="bogus"))
