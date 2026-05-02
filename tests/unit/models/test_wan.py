"""Unit tests for the WANConnection model."""

import pytest
from pydantic import ValidationError

from src.models.wan import WANConnection


class TestWANConnectionMinimalShape:
    """The integration-API list_wan_connections response is sparse —
    just `id` and `name` per WAN. Extra detail (site_id, wan_type,
    interface, status, IP config, stats) comes from per-WAN detail or
    the legacy v1 endpoint. The model must accept the minimal shape."""

    def test_minimal_wire_shape_parses(self):
        # Exact shape observed live against the UCK-G2 on 2026-05-01.
        wan = WANConnection(_id="6aaa2923-eb47-4099", name="Internet 1")
        assert wan.id == "6aaa2923-eb47-4099"
        assert wan.name == "Internet 1"
        assert wan.site_id is None
        assert wan.wan_type is None
        assert wan.interface is None
        assert wan.status is None

    def test_id_is_still_required(self):
        with pytest.raises(ValidationError):
            WANConnection(name="Internet 1")

    def test_name_is_still_required(self):
        with pytest.raises(ValidationError):
            WANConnection(_id="abc")

    def test_full_shape_still_parses(self):
        # The legacy detail endpoint returns the full shape; the model
        # must continue to accept it after relaxing the required fields.
        wan = WANConnection(
            _id="abc",
            site_id="site-1",
            name="Internet 1",
            wan_type="dhcp",
            interface="eth0",
            status="online",
            ip_address="1.2.3.4",
            uptime=42,
            rx_bytes=100,
            tx_bytes=50,
        )
        assert wan.wan_type == "dhcp"
        assert wan.interface == "eth0"
        assert wan.status == "online"
        assert wan.ip_address == "1.2.3.4"
