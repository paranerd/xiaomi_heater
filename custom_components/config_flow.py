"""Config flow for Xiaomi Mi Smart Heater integration."""
from __future__ import annotations

import logging
from typing import Any

from miio import Device, DeviceException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("name"): str,
        vol.Required("token"): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        device = Device(data[CONF_HOST], data["token"])
        device_info = await hass.async_add_executor_job(device.info)
    except DeviceException as ex:
        raise CannotConnect from ex

    # Return info that you want to store in the config entry.
    return {
        "title": data["name"],
        "model": device_info.model,
        "mac": device_info.mac_address
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xiaomi Mi Smart Heater."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.info("User input: %s", user_input)
            try:
                device_info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device_info["mac"])
                self._abort_if_unique_id_configured({CONF_HOST: user_input[CONF_HOST]})

                return self.async_create_entry(
                    title=device_info["title"],
                    data={
                        **user_input,
                        "model": device_info["model"],
                        "mac": device_info["mac"]
                    }
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
