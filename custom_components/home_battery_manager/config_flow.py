"""Config flow for Home Battery Manager."""
from __future__ import annotations

from typing import Any

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
    CONF_INVERT_SET_POWER,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_POWER_METER,
    CONF_POWER_METER_EXPORT,
    CONF_POWER_METER_IMPORT,
    CONF_USE_DUAL_POWER_METERS,
    DEFAULT_MAX_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
    DOMAIN,
)


def _optional_entity_key(field: str, current_values: dict[str, Any]):
    """Build an optional entity schema key with default when available."""
    value = current_values.get(field)
    if value:
        return vol.Optional(field, default=value)
    return vol.Optional(field)


def _required_entity_key(field: str, current_values: dict[str, Any]):
    """Build a required entity schema key with default when available."""
    value = current_values.get(field)
    if value:
        return vol.Required(field, default=value)
    return vol.Required(field)


def _validate_meter_inputs(user_input: dict[str, Any]) -> str | None:
    """Validate meter configuration for single or dual meter mode."""
    use_dual = user_input.get(CONF_USE_DUAL_POWER_METERS, False)
    if use_dual:
        meter_import = user_input.get(CONF_POWER_METER_IMPORT)
        meter_export = user_input.get(CONF_POWER_METER_EXPORT)
        if not meter_import or not meter_export:
            return "dual_meters_required"
        if meter_import == meter_export:
            return "dual_meters_must_differ"
        return None

    if not user_input.get(CONF_POWER_METER):
        return "single_meter_required"

    return None


def _build_schema(current_values: dict[str, Any]) -> vol.Schema:
    """Build config schema with defaults from provided values."""
    power_meter_key = _optional_entity_key(CONF_POWER_METER, current_values)
    power_meter_import_key = _optional_entity_key(CONF_POWER_METER_IMPORT, current_values)
    power_meter_export_key = _optional_entity_key(CONF_POWER_METER_EXPORT, current_values)
    set_power_key = _required_entity_key(CONF_BATTERY_SET_POWER, current_values)

    return vol.Schema(
        {
            vol.Optional(
                CONF_USE_DUAL_POWER_METERS,
                default=current_values.get(CONF_USE_DUAL_POWER_METERS, False),
            ): bool,
            power_meter_key: EntitySelector(EntitySelectorConfig(domain="sensor")),
            power_meter_import_key: EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            power_meter_export_key: EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            set_power_key: EntitySelector(EntitySelectorConfig(domain="number")),
            vol.Optional(
                CONF_MAX_CHARGE_POWER,
                default=current_values.get(
                    CONF_MAX_CHARGE_POWER,
                    DEFAULT_MAX_CHARGE_POWER,
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100_000,
                    step=100,
                    unit_of_measurement="W",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_MAX_DISCHARGE_POWER,
                default=current_values.get(
                    CONF_MAX_DISCHARGE_POWER,
                    DEFAULT_MAX_DISCHARGE_POWER,
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100_000,
                    step=100,
                    unit_of_measurement="W",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_INVERT_SET_POWER,
                default=current_values.get(CONF_INVERT_SET_POWER, False),
            ): bool,
        }
    )


class HomeBatteryManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of Home Battery Manager."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return HomeBatteryManagerOptionsFlow(entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show an information page before setup."""
        return await self.async_step_intro(user_input)

    async def async_step_intro(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show integration information before configuration."""
        if user_input is not None:
            return await self.async_step_config()

        return self.async_show_form(
            step_id="intro",
            data_schema=vol.Schema({}),
        )

    async def async_step_config(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show the setup form and create an entry when submitted."""
        errors: dict[str, str] = {}
        if user_input is not None:
            meter_error = _validate_meter_inputs(user_input)
            if meter_error is None:
                return self.async_create_entry(
                    title="Home Battery Manager",
                    data=user_input,
                )
            errors["base"] = meter_error

        return self.async_show_form(
            step_id="config",
            data_schema=_build_schema({}),
            errors=errors,
        )


class HomeBatteryManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle Home Battery Manager options."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the integration options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            meter_error = _validate_meter_inputs(user_input)
            if meter_error is None:
                return self.async_create_entry(title="", data=user_input)
            errors["base"] = meter_error

        current_values = {
            CONF_USE_DUAL_POWER_METERS: self._entry.options.get(
                CONF_USE_DUAL_POWER_METERS,
                self._entry.data.get(CONF_USE_DUAL_POWER_METERS, False),
            ),
            CONF_POWER_METER: self._entry.options.get(
                CONF_POWER_METER,
                self._entry.data.get(CONF_POWER_METER),
            ),
            CONF_POWER_METER_IMPORT: self._entry.options.get(
                CONF_POWER_METER_IMPORT,
                self._entry.data.get(CONF_POWER_METER_IMPORT),
            ),
            CONF_POWER_METER_EXPORT: self._entry.options.get(
                CONF_POWER_METER_EXPORT,
                self._entry.data.get(CONF_POWER_METER_EXPORT),
            ),
            CONF_BATTERY_SET_POWER: self._entry.options.get(
                CONF_BATTERY_SET_POWER,
                self._entry.data.get(CONF_BATTERY_SET_POWER),
            ),
            CONF_MAX_CHARGE_POWER: self._entry.options.get(
                CONF_MAX_CHARGE_POWER,
                self._entry.data.get(CONF_MAX_CHARGE_POWER, DEFAULT_MAX_CHARGE_POWER),
            ),
            CONF_MAX_DISCHARGE_POWER: self._entry.options.get(
                CONF_MAX_DISCHARGE_POWER,
                self._entry.data.get(
                    CONF_MAX_DISCHARGE_POWER,
                    DEFAULT_MAX_DISCHARGE_POWER,
                ),
            ),
            CONF_INVERT_SET_POWER: self._entry.options.get(
                CONF_INVERT_SET_POWER,
                self._entry.data.get(CONF_INVERT_SET_POWER, False),
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current_values),
            errors=errors,
        )
