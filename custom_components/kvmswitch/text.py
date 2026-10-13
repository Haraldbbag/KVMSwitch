"""Text entities: room names and monitor labels."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KvmConfigEntry
from .const import NUM_MONITORS, NUM_ROOMS
from .data import KvmData
from .entity import KvmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = entry.runtime_data
    entities: list[TextEntity] = []
    for idx in range(NUM_ROOMS):
        entities.append(RoomNameText(data, idx))
        entities.extend(MonitorLabelText(data, idx, m) for m in range(NUM_MONITORS))
    async_add_entities(entities)


class _KvmText(KvmEntity, TextEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 64


class RoomNameText(_KvmText):
    _attr_icon = "mdi:door"

    def __init__(self, data: KvmData, idx: int) -> None:
        super().__init__(data, f"raum{idx + 1}_name", "text")
        self.idx = idx

    @property
    def name(self) -> str:
        return f"Raum {self.idx + 1} Name"

    @property
    def native_value(self) -> str:
        return self.data.room(self.idx)["name"]

    async def async_set_value(self, value: str) -> None:
        self.data.set_room_name(self.idx, value.strip())


class MonitorLabelText(_KvmText):
    _attr_icon = "mdi:form-textbox"

    def __init__(self, data: KvmData, idx: int, m_idx: int) -> None:
        super().__init__(data, f"raum{idx + 1}_monitor{m_idx + 1}_name", "text")
        self.idx = idx
        self.m_idx = m_idx

    @property
    def name(self) -> str:
        return f"{self.data.room_title(self.idx)} Monitor {self.m_idx + 1} Bezeichnung"

    @property
    def native_value(self) -> str:
        return self.data.room(self.idx)["monitors"][self.m_idx]["label"]

    async def async_set_value(self, value: str) -> None:
        self.data.set_monitor_label(self.idx, self.m_idx, value.strip())
