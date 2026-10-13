"""KVM Switch: couples the USB matrix with the Videohub monitors per room."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .data import KvmData

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SWITCH, Platform.TEXT]

type KvmConfigEntry = ConfigEntry[KvmData]


async def async_setup_entry(hass: HomeAssistant, entry: KvmConfigEntry) -> bool:
    data = KvmData(hass, entry)
    await data.async_load()
    entry.runtime_data = data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    data.async_start()
    entry.async_on_unload(data.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KvmConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: KvmConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
