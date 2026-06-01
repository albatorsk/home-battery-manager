"""Sensor platform for Home Battery Manager."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import HomeBatteryManagerCoordinator
from .const import CONF_BATTERY_SOC, DOMAIN, SIGNAL_SETPOINT_UPDATED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensor entities for this config entry."""
    coordinator: HomeBatteryManagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    soc_entity_id: str = entry.data[CONF_BATTERY_SOC]

    async_add_entities(
        [
            BatterySocSensor(hass, entry, soc_entity_id),
            BatteryPowerSetpointSensor(hass, entry, coordinator),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Shared device info so both sensors appear under one device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Home Battery Manager",
        manufacturer="Custom",
        model="Battery Controller",
        entry_type="service",
    )


class BatterySocSensor(SensorEntity):
    """Mirrors the user-selected SoC entity and classifies it as a battery sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "battery_soc"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source_entity_id: str,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._source_entity_id = source_entity_id
        self._attr_unique_id = f"{entry.entry_id}_soc"
        self._attr_device_info = _device_info(entry)
        self._attr_native_value: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore current value and subscribe to future changes."""
        state = self.hass.states.get(self._source_entity_id)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._attr_native_value = float(state.state)
            except ValueError:
                pass

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._handle_source_state_change,
            )
        )

    @callback
    def _handle_source_state_change(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_native_value = None
        else:
            try:
                self._attr_native_value = float(new_state.state)
            except ValueError:
                self._attr_native_value = None
        self.async_write_ha_state()


class BatteryPowerSetpointSensor(SensorEntity):
    """Shows the power setpoint most recently commanded to the battery."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "power_setpoint"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: HomeBatteryManagerCoordinator,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_power_setpoint"
        self._attr_device_info = _device_info(entry)
        self._attr_native_value: float | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to setpoint update signals from the coordinator."""
        signal = SIGNAL_SETPOINT_UPDATED.format(entry_id=self._entry.entry_id)
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_setpoint_update)
        )

    @callback
    def _handle_setpoint_update(self) -> None:
        self._attr_native_value = self._coordinator.battery_power_setpoint
        self.async_write_ha_state()
