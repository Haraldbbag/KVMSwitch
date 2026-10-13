"""Base entity for the KVM Switch integration."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .data import KvmData


class KvmEntity(Entity):
    """Entity bound to the shared KvmData; refreshes whenever it changes."""

    _attr_should_poll = False
    # No device: HA would prefix every friendly name with the device name,
    # but the room selector should show just the room name on the dashboard.
    _attr_has_entity_name = True

    def __init__(self, data: KvmData, key: str, domain: str) -> None:
        self.data = data
        self._attr_unique_id = f"{data.entry.entry_id}_{key}"
        self.entity_id = f"{domain}.{DOMAIN}_{key}"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.data.async_add_listener(self.async_write_ha_state))
