"""Home Battery Manager integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_BATTERY_SET_POWER,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_POWER_METER,
    DEFAULT_MAX_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
    DOMAIN,
    SIGNAL_SETPOINT_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


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
        self._cancel_listener: callable | None = None

    @callback
    def async_start(self) -> None:
        """Begin listening to the power meter entity."""
        power_meter = self.entry.data[CONF_POWER_METER]
        self._cancel_listener = async_track_state_change_event(
            self.hass, [power_meter], self._handle_power_meter_change
        )
        _LOGGER.debug("Listening to power meter '%s'", power_meter)

    @callback
    def async_stop(self) -> None:
        """Stop the control loop."""
        if self._cancel_listener is not None:
            self._cancel_listener()
            self._cancel_listener = None

    @callback
    def _handle_power_meter_change(self, event: Event) -> None:
        """React to a power meter state change and update the battery setpoint."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            return

        try:
            house_power = float(new_state.state)
        except ValueError:
            _LOGGER.warning(
                "Cannot parse power meter state '%s' as watts; skipping",
                new_state.state,
            )
            return

        # Determine allowed range from the number entity attributes, falling
        # back to the user-configured limits when the entity is not yet available.
        max_charge = float(
            self.entry.data.get(CONF_MAX_CHARGE_POWER, DEFAULT_MAX_CHARGE_POWER)
        )
        max_discharge = float(
            self.entry.data.get(CONF_MAX_DISCHARGE_POWER, DEFAULT_MAX_DISCHARGE_POWER)
        )

        battery_set_power_id: str = self.entry.data[CONF_BATTERY_SET_POWER]
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

        # Zero-export setpoint: negate house power so the battery offsets it.
        # Positive → charging, negative → discharging.
        battery_power = max(entity_min, min(entity_max, -house_power))
        battery_power = round(battery_power, 1)

        _LOGGER.debug(
            "House power %.1f W → battery setpoint %.1f W (limits %.1f..%.1f W)",
            house_power,
            battery_power,
            entity_min,
            entity_max,
        )

        self.battery_power_setpoint = battery_power

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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


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
