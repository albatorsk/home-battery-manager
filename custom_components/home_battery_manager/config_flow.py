"""Config flow for Home Battery Manager."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_BATTERY_SET_POWER,
    CONF_BATTERY_SOC,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_POWER_METER,
    DEFAULT_MAX_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
    DOMAIN,
)

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POWER_METER): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_BATTERY_SET_POWER): EntitySelector(
            EntitySelectorConfig(domain="number")
        ),
        vol.Required(CONF_BATTERY_SOC): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_MAX_CHARGE_POWER, default=DEFAULT_MAX_CHARGE_POWER): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=100_000,
                step=100,
                unit_of_measurement="W",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_MAX_DISCHARGE_POWER, default=DEFAULT_MAX_DISCHARGE_POWER): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=100_000,
                step=100,
                unit_of_measurement="W",
                mode=NumberSelectorMode.BOX,
            )
        ),
    }
)


class HomeBatteryManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of Home Battery Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        """Show the setup form and create an entry when submitted."""
        if user_input is not None:
            return self.async_create_entry(
                title="Home Battery Manager",
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=_STEP_USER_SCHEMA)
