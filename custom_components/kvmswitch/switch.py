"""Switch per room: also switch the monitors, or USB only."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KvmConfigEntry
from .const import NUM_ROOMS
from .data import KvmData
from .entity import KvmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = entry.runtime_data
    async_add_entities(FollowSwitch(data, idx) for idx in range(NUM_ROOMS))


class FollowSwitch(KvmEntity, SwitchEntity):
    _attr_icon = "mdi:monitor-multiple"

    def __init__(self, data: KvmData, idx: int) -> None:
        super().__init__(data, f"raum{idx + 1}_monitore", "switch")
        self.idx = idx

    @property
    def name(self) -> str:
        return f"{self.data.room_title(self.idx)} Monitore mitschalten"

    @property
    def available(self) -> bool:
        return bool(self.data.room(self.idx)["usb"])

    @property
    def is_on(self) -> bool:
        return bool(self.data.room(self.idx)["follow"])

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.data.set_room_follow(self.idx, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.data.set_room_follow(self.idx, False)
