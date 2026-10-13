"""Central data model for the KVM Switch integration.

Holds the room / sender configuration, persists it in the HA storage and
performs the actual switching (USB matrix + Videohub monitors).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import copy
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify

from .const import (
    CONF_IGNORED_SOURCES,
    CONF_OUTPUTS,
    CONF_RECEIVERS,
    DEFAULT_IGNORED_SOURCES,
    DOMAIN,
    NONE_OPTION,
    NUM_INPUTS,
    NUM_MONITORS,
    NUM_ROOMS,
    SAVE_DELAY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _empty_room() -> dict[str, Any]:
    return {
        "name": "",
        "usb": None,
        "follow": True,
        "monitors": [{"label": "", "output": None} for _ in range(NUM_MONITORS)],
    }


def _default_data() -> dict[str, Any]:
    return {
        "rooms": [_empty_room() for _ in range(NUM_ROOMS)],
        "senders": {},
        "known_senders": [],
        "known_inputs": [],
    }


class KvmData:
    """Configuration + switching logic, shared by all entities of an entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._data: dict[str, Any] = _default_data()
        self._listeners: list[Callable[[], None]] = []
        self._unsub_track: Callable[[], None] | None = None

    # ------------------------------------------------------------------ setup

    @property
    def _conf(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def receivers(self) -> list[str]:
        return list(self._conf.get(CONF_RECEIVERS, []))

    @property
    def outputs(self) -> list[str]:
        return list(self._conf.get(CONF_OUTPUTS, []))

    @property
    def ignored_sources(self) -> set[str]:
        raw = self._conf.get(CONF_IGNORED_SOURCES, DEFAULT_IGNORED_SOURCES) or ""
        return {s.strip() for s in raw.split(",") if s.strip()}

    async def async_load(self) -> None:
        """Load stored data and normalise its shape."""
        stored = await self._store.async_load()
        data = _default_data()
        if stored:
            for key in ("senders", "known_senders", "known_inputs"):
                if key in stored:
                    data[key] = stored[key]
            for idx, room in enumerate(stored.get("rooms", [])[:NUM_ROOMS]):
                target = data["rooms"][idx]
                target["name"] = room.get("name", "")
                target["usb"] = room.get("usb")
                target["follow"] = room.get("follow", True)
                for m_idx, mon in enumerate(room.get("monitors", [])[:NUM_MONITORS]):
                    target["monitors"][m_idx] = {
                        "label": mon.get("label", ""),
                        "output": mon.get("output"),
                    }
        self._data = data
        # Pick up whatever the devices currently report.
        self._refresh_known_senders()
        self._refresh_known_inputs()

    @callback
    def async_start(self) -> None:
        """Start following the receiver and output entities."""
        watched = self.receivers + self.outputs
        if watched:
            self._unsub_track = async_track_state_change_event(
                self.hass, watched, self._handle_state_change
            )

    @callback
    def async_stop(self) -> None:
        if self._unsub_track:
            self._unsub_track()
            self._unsub_track = None

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        if entity_id in self.receivers and self._refresh_known_senders():
            # New sender showed up -> reload so its entities get created.
            _LOGGER.info("New USB sender detected, reloading %s", DOMAIN)
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)
            return
        if entity_id in self.outputs:
            self._refresh_known_inputs()
        self._notify()

    # -------------------------------------------------------------- listeners

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        @callback
        def _remove() -> None:
            self._listeners.remove(update)

        return _remove

    @callback
    def _notify(self) -> None:
        for update in list(self._listeners):
            update()

    @callback
    def _changed(self) -> None:
        self._store.async_delay_save(lambda: copy.deepcopy(self._data), SAVE_DELAY)
        self._notify()

    # ------------------------------------------------------- device discovery

    def _usable_state(self, entity_id: str):
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        return state

    def receiver_sources(self, entity_id: str | None) -> list[str]:
        """Options of a receiver select (the USB senders)."""
        if not entity_id:
            return []
        state = self._usable_state(entity_id)
        if state is None:
            return []
        return list(state.attributes.get("options") or [])

    @callback
    def _refresh_known_senders(self) -> bool:
        """Add newly seen senders. Returns True if the list grew."""
        known: list[str] = self._data["known_senders"]
        ignored = self.ignored_sources
        added = False
        for receiver in self.receivers:
            for source in self.receiver_sources(receiver):
                if source not in known and source not in ignored:
                    known.append(source)
                    added = True
        if added:
            self._store.async_delay_save(lambda: copy.deepcopy(self._data), SAVE_DELAY)
        return added

    @callback
    def _refresh_known_inputs(self) -> None:
        """Take the Videohub input list from any output that reports one."""
        for output in self.outputs:
            state = self._usable_state(output)
            if state is None:
                continue
            sources = state.attributes.get("source_list")
            if sources:
                sources = list(sources)
                if sources != self._data["known_inputs"]:
                    self._data["known_inputs"] = sources
                    self._store.async_delay_save(
                        lambda: copy.deepcopy(self._data), SAVE_DELAY
                    )
                return

    @property
    def senders(self) -> list[str]:
        ignored = self.ignored_sources
        return [s for s in self._data["known_senders"] if s not in ignored]

    @property
    def inputs(self) -> list[str]:
        return list(self._data["known_inputs"])

    def friendly_name(self, entity_id: str) -> str:
        state = self.hass.states.get(entity_id)
        if state is not None and state.name:
            return state.name
        return entity_id

    def entity_options(self, entity_ids: list[str]) -> dict[str, str]:
        """Map display label -> entity_id (labels made unique)."""
        result: dict[str, str] = {}
        for entity_id in entity_ids:
            label = self.friendly_name(entity_id)
            if label in result or label == NONE_OPTION:
                label = f"{label} ({entity_id})"
            result[label] = entity_id
        return result

    # ------------------------------------------------------------ room access

    def room(self, idx: int) -> dict[str, Any]:
        return self._data["rooms"][idx]

    def room_title(self, idx: int) -> str:
        return self.room(idx)["name"].strip() or f"Raum {idx + 1}"

    def monitor_title(self, idx: int, m_idx: int) -> str:
        return (
            self.room(idx)["monitors"][m_idx]["label"].strip()
            or f"Monitor {m_idx + 1}"
        )

    @callback
    def set_room_name(self, idx: int, value: str) -> None:
        self.room(idx)["name"] = value
        self._changed()

    @callback
    def set_room_usb(self, idx: int, entity_id: str | None) -> None:
        self.room(idx)["usb"] = entity_id
        self._changed()

    @callback
    def set_room_follow(self, idx: int, value: bool) -> None:
        self.room(idx)["follow"] = value
        self._changed()

    @callback
    def set_monitor_label(self, idx: int, m_idx: int, value: str) -> None:
        self.room(idx)["monitors"][m_idx]["label"] = value
        self._changed()

    @callback
    def set_monitor_output(self, idx: int, m_idx: int, entity_id: str | None) -> None:
        self.room(idx)["monitors"][m_idx]["output"] = entity_id
        self._changed()

    # ---------------------------------------------------------- sender access

    def sender_inputs(self, sender: str) -> list[str | None]:
        values = list(self._data["senders"].get(sender, []))
        values += [None] * (NUM_INPUTS - len(values))
        return values[:NUM_INPUTS]

    @callback
    def set_sender_input(self, sender: str, k_idx: int, value: str | None) -> None:
        values = self.sender_inputs(sender)
        values[k_idx] = value
        self._data["senders"][sender] = values
        self._changed()

    @staticmethod
    def sender_slug(sender: str) -> str:
        return slugify(sender) or "quelle"

    # -------------------------------------------------------------- switching

    def room_current_source(self, idx: int) -> str | None:
        receiver = self.room(idx)["usb"]
        if not receiver:
            return None
        state = self.hass.states.get(receiver)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state.state

    def room_available(self, idx: int) -> bool:
        receiver = self.room(idx)["usb"]
        if not receiver:
            return False
        state = self.hass.states.get(receiver)
        return state is not None and state.state != STATE_UNAVAILABLE

    def room_routes(self, idx: int, sender: str) -> list[tuple[str, str]]:
        """Pair the room's monitors with the sender's inputs, in order.

        Only configured slots count. Extra monitors stay untouched, extra
        inputs are dropped.
        """
        outputs = [m["output"] for m in self.room(idx)["monitors"] if m["output"]]
        inputs = [i for i in self.sender_inputs(sender) if i]
        return list(zip(outputs, inputs))

    async def async_select_source(self, idx: int, sender: str) -> None:
        room = self.room(idx)
        receiver = room["usb"]
        if not receiver:
            raise HomeAssistantError(
                f"{self.room_title(idx)}: kein USB-Empfänger zugeordnet"
            )

        await self.hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: receiver, "option": sender},
            blocking=True,
        )

        if not room["follow"]:
            return

        routes = self.room_routes(idx, sender)
        if not routes:
            return

        results = await asyncio.gather(
            *(
                self.hass.services.async_call(
                    "media_player",
                    "select_source",
                    {ATTR_ENTITY_ID: output, "source": source},
                    blocking=True,
                )
                for output, source in routes
            ),
            return_exceptions=True,
        )
        failed = [
            f"{self.friendly_name(output)} ({err})"
            for (output, _), err in zip(routes, results)
            if isinstance(err, Exception)
        ]
        if failed:
            raise HomeAssistantError(
                "USB umgeschaltet, aber Monitore fehlgeschlagen: " + ", ".join(failed)
            )
