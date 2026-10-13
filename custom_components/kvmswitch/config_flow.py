"""Config flow for the KVM Switch integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_IGNORED_SOURCES,
    CONF_OUTPUTS,
    CONF_RECEIVERS,
    DEFAULT_IGNORED_SOURCES,
    DOMAIN,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_RECEIVERS, default=defaults.get(CONF_RECEIVERS, [])
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="select", multiple=True)
            ),
            vol.Required(
                CONF_OUTPUTS, default=defaults.get(CONF_OUTPUTS, [])
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player", multiple=True)
            ),
            vol.Optional(
                CONF_IGNORED_SOURCES,
                default=defaults.get(CONF_IGNORED_SOURCES, DEFAULT_IGNORED_SOURCES),
            ): selector.TextSelector(),
        }
    )


class KvmSwitchConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="KVM Switch", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return KvmSwitchOptionsFlow()


class KvmSwitchOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
