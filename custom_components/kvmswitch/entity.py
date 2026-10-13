"""Base entity for the KVM Switch integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .data import KvmData


class KvmEntity(Entity):
    """Entity bound to the shared KvmData; refreshes whenever it changes."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, data: KvmData, key: str, domain: str) -> None:
        self.data = data
        self._attr_unique_id = f"{data.entry.entry_id}_{key}"
        self.entity_id = f"{domain}.{DOMAIN}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.entry.entry_id)},
            name="KVM Switch",
            manufacturer="Haraldbbag",
            model="USB-Matrix + Videohub",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.data.async_add_listener(self.async_write_ha_state))
