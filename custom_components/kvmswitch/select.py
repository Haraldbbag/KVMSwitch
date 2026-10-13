"""Select entities: the room source selector and all mapping dropdowns."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KvmConfigEntry
from .const import NONE_OPTION, NUM_INPUTS, NUM_MONITORS, NUM_ROOMS
from .data import KvmData
from .entity import KvmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = entry.runtime_data
    entities: list[SelectEntity] = []
    for idx in range(NUM_ROOMS):
        entities.append(RoomSourceSelect(data, idx))
        entities.append(RoomUsbSelect(data, idx))
        entities.extend(
            MonitorOutputSelect(data, idx, m) for m in range(NUM_MONITORS)
        )
    for sender in data.senders:
        entities.extend(SenderInputSelect(data, sender, k) for k in range(NUM_INPUTS))
    async_add_entities(entities)


class RoomSourceSelect(KvmEntity, SelectEntity):
    """Main control: pick a USB sender for the room (and its monitors)."""

    _attr_icon = "mdi:usb"

    def __init__(self, data: KvmData, idx: int) -> None:
        super().__init__(data, f"raum{idx + 1}_quelle", "select")
        self.idx = idx

    @property
    def name(self) -> str:
        return self.data.room_title(self.idx)

    @property
    def available(self) -> bool:
        return self.data.room_available(self.idx)

    @property
    def options(self) -> list[str]:
        return self.data.receiver_sources(self.data.room(self.idx)["usb"])

    @property
    def current_option(self) -> str | None:
        current = self.data.room_current_source(self.idx)
        return current if current in self.options else None

    @property
    def extra_state_attributes(self) -> dict:
        room = self.data.room(self.idx)
        return {
            "usb_empfaenger": room["usb"],
            "monitore_mitschalten": room["follow"],
            "monitore": [
                m["output"] for m in room["monitors"] if m["output"]
            ],
        }

    async def async_select_option(self, option: str) -> None:
        await self.data.async_select_source(self.idx, option)


class _EntityRefSelect(KvmEntity, SelectEntity):
    """Dropdown whose options are other HA entities (stored by entity_id)."""

    _attr_entity_category = EntityCategory.CONFIG

    def _candidates(self) -> list[str]:
        raise NotImplementedError

    def _get(self) -> str | None:
        raise NotImplementedError

    def _set(self, entity_id: str | None) -> None:
        raise NotImplementedError

    def _mapping(self) -> dict[str, str]:
        candidates = self._candidates()
        current = self._get()
        if current and current not in candidates:
            candidates = [*candidates, current]
        return self.data.entity_options(candidates)

    @property
    def options(self) -> list[str]:
        return [NONE_OPTION, *self._mapping()]

    @property
    def current_option(self) -> str | None:
        current = self._get()
        if not current:
            return NONE_OPTION
        for label, entity_id in self._mapping().items():
            if entity_id == current:
                return label
        return NONE_OPTION

    async def async_select_option(self, option: str) -> None:
        self._set(None if option == NONE_OPTION else self._mapping().get(option))


class RoomUsbSelect(_EntityRefSelect):
    _attr_icon = "mdi:usb-port"

    def __init__(self, data: KvmData, idx: int) -> None:
        super().__init__(data, f"raum{idx + 1}_usb", "select")
        self.idx = idx

    @property
    def name(self) -> str:
        return f"{self.data.room_title(self.idx)} USB-Empfänger"

    def _candidates(self) -> list[str]:
        return self.data.receivers

    def _get(self) -> str | None:
        return self.data.room(self.idx)["usb"]

    def _set(self, entity_id: str | None) -> None:
        self.data.set_room_usb(self.idx, entity_id)


class MonitorOutputSelect(_EntityRefSelect):
    _attr_icon = "mdi:monitor"

    def __init__(self, data: KvmData, idx: int, m_idx: int) -> None:
        super().__init__(data, f"raum{idx + 1}_monitor{m_idx + 1}_ausgang", "select")
        self.idx = idx
        self.m_idx = m_idx

    @property
    def name(self) -> str:
        return (
            f"{self.data.room_title(self.idx)} "
            f"{self.data.monitor_title(self.idx, self.m_idx)} Videohub-Ausgang"
        )

    def _candidates(self) -> list[str]:
        return self.data.outputs

    def _get(self) -> str | None:
        return self.data.room(self.idx)["monitors"][self.m_idx]["output"]

    def _set(self, entity_id: str | None) -> None:
        self.data.set_monitor_output(self.idx, self.m_idx, entity_id)


class SenderInputSelect(KvmEntity, SelectEntity):
    """Videohub input n belonging to a USB sender."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:video-input-hdmi"

    def __init__(self, data: KvmData, sender: str, k_idx: int) -> None:
        super().__init__(
            data,
            f"quelle_{data.sender_slug(sender)}_eingang{k_idx + 1}",
            "select",
        )
        self.sender = sender
        self.k_idx = k_idx

    @property
    def name(self) -> str:
        return f"{self.sender} Videohub-Eingang {self.k_idx + 1}"

    @property
    def options(self) -> list[str]:
        inputs = self.data.inputs
        current = self.data.sender_inputs(self.sender)[self.k_idx]
        if current and current not in inputs:
            inputs = [*inputs, current]
        return [NONE_OPTION, *[i for i in inputs if i != NONE_OPTION]]

    @property
    def current_option(self) -> str | None:
        return self.data.sender_inputs(self.sender)[self.k_idx] or NONE_OPTION

    async def async_select_option(self, option: str) -> None:
        self.data.set_sender_input(
            self.sender, self.k_idx, None if option == NONE_OPTION else option
        )
