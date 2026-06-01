"""Home Battery Manager integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

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
    SIGNAL_SETPOINT_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


def _entry_value(entry: ConfigEntry, key: str, default):
    """Read a setting from options first, then data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


class HomeBatteryManagerCoordinator:
    """Runs the zero-export battery control loop for one config entry.

    Each time the house power meter changes state, the coordinator computes
    the required battery power setpoint (battery = −house_power) to keep
    grid import/export at zero, clamps it to the battery entity's declared
    limits, and writes the value via the ``number.set_value`` service.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        # Last setpoint sent to the battery, exposed to sensor entities.
        self.battery_power_setpoint: float | None = None
        # Timestamp for when the setpoint value last changed.
        self.set_power_last_changed: datetime | None = None
        self._cancel_listener: callable | None = None

    @callback
    def async_start(self) -> None:
        """Begin listening to the configured power meter entity or entities."""
        meter_entities = self._meter_entities()
        if not meter_entities:
            _LOGGER.warning("No power meter entities configured; control loop is inactive")
            return

        self._cancel_listener = async_track_state_change_event(
            self.hass, meter_entities, self._handle_power_meter_change
        )
        _LOGGER.debug("Listening to power meter entities %s", meter_entities)

    def _meter_entities(self) -> list[str]:
        """Return meter entities that should trigger control loop updates."""
        if _entry_value(self.entry, CONF_USE_DUAL_POWER_METERS, False):
            meter_import = _entry_value(self.entry, CONF_POWER_METER_IMPORT, "")
            meter_export = _entry_value(self.entry, CONF_POWER_METER_EXPORT, "")
            return [entity for entity in (meter_import, meter_export) if entity]

        power_meter = _entry_value(self.entry, CONF_POWER_METER, "")
        return [power_meter] if power_meter else []

    def _house_power_from_event(self, event: Event) -> float | None:
        """Read house power using the configured single or dual meter mode."""
        if _entry_value(self.entry, CONF_USE_DUAL_POWER_METERS, False):
            meter_import = _entry_value(self.entry, CONF_POWER_METER_IMPORT, "")
            meter_export = _entry_value(self.entry, CONF_POWER_METER_EXPORT, "")
            import_state = self.hass.states.get(meter_import)
            export_state = self.hass.states.get(meter_export)

            if import_state is None or export_state is None:
                return None
            if (
                import_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, "")
                or export_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, "")
            ):
                return None

            try:
                import_power = float(import_state.state)
                export_power = float(export_state.state)
            except ValueError:
                _LOGGER.warning(
                    "Cannot parse dual meter states import='%s' export='%s' as watts; skipping",
                    import_state.state,
                    export_state.state,
                )
                return None

            # With dual meters, both are positive values; net house power is import minus export.
            return import_power - export_power

        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            return None

        try:
            return float(new_state.state)
        except ValueError:
            _LOGGER.warning(
                "Cannot parse power meter state '%s' as watts; skipping",
                new_state.state,
            )
            return None

    @callback
    def async_stop(self) -> None:
        """Stop the control loop."""
        if self._cancel_listener is not None:
            self._cancel_listener()
            self._cancel_listener = None

    @callback
    def _handle_power_meter_change(self, event: Event) -> None:
        """React to a power meter state change and update the battery setpoint."""
        house_power = self._house_power_from_event(event)
        if house_power is None:
            return

        # Determine allowed range from the number entity attributes, falling
        # back to the user-configured limits when the entity is not yet available.
        max_charge = float(
            _entry_value(self.entry, CONF_MAX_CHARGE_POWER, DEFAULT_MAX_CHARGE_POWER)
        )
        max_discharge = float(
            _entry_value(
                self.entry,
                CONF_MAX_DISCHARGE_POWER,
                DEFAULT_MAX_DISCHARGE_POWER,
            )
        )

        battery_set_power_id = _entry_value(self.entry, CONF_BATTERY_SET_POWER, "")
        number_state = self.hass.states.get(battery_set_power_id)
        if number_state is not None:
            try:
                entity_min = float(number_state.attributes.get("min", -max_discharge))
                entity_max = float(number_state.attributes.get("max", max_charge))
            except (ValueError, TypeError):
                entity_min = -max_discharge
                entity_max = max_charge
        else:
            entity_min = -max_discharge
            entity_max = max_charge

        current_command = None
        if number_state is not None and number_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
            "",
        ):
            try:
                current_command = float(number_state.state)
            except ValueError:
                current_command = None

        if current_command is None:
            current_command = float(self.battery_power_setpoint or 0)

        invert_set_power = _entry_value(self.entry, CONF_INVERT_SET_POWER, False)

        # Corrective control in the integration's native sign convention:
        # target_native = current_native - house_power
        current_native = -current_command if invert_set_power else current_command
        target_native = current_native - house_power
        battery_power = -target_native if invert_set_power else target_native
        battery_power = max(entity_min, min(entity_max, battery_power))
        battery_power = int(round(battery_power))

        _LOGGER.debug(
            "House power %.1f W, current setpoint %.1f W → target %.1f W (limits %.1f..%.1f W)",
            house_power,
            current_command,
            battery_power,
            entity_min,
            entity_max,
        )

        previous_setpoint = self.battery_power_setpoint
        if previous_setpoint == battery_power:
            return

        self.battery_power_setpoint = battery_power
        changed_state = event.data.get("new_state")
        if previous_setpoint != battery_power and changed_state is not None:
            self.set_power_last_changed = changed_state.last_changed

        # Command the battery asynchronously; errors are logged by HA.
        self.hass.async_create_task(
            self.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": battery_set_power_id, "value": battery_power},
                blocking=False,
            )
        )

        # Notify sensor entities that the setpoint has changed.
        async_dispatcher_send(
            self.hass,
            SIGNAL_SETPOINT_UPDATED.format(entry_id=self.entry.entry_id),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Battery Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = HomeBatteryManagerCoordinator(hass, entry)
    coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: HomeBatteryManagerCoordinator | None = hass.data[DOMAIN].get(
        entry.entry_id
    )
    if coordinator is not None:
        coordinator.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
