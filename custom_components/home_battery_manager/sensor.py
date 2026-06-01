"""Sensor platform for Home Battery Manager."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeBatteryManagerCoordinator
from .const import DOMAIN, SIGNAL_SETPOINT_UPDATED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensor entities for this config entry."""
    coordinator: HomeBatteryManagerCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BatteryPowerSetpointSensor(hass, entry, coordinator),
            BatterySetPowerLastChangedSensor(hass, entry, coordinator),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Shared device info so both sensors appear under one device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Home Battery Manager",
        manufacturer="Custom",
        model="Battery Controller",
        entry_type=DeviceEntryType.SERVICE,
    )


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


class BatterySetPowerLastChangedSensor(SensorEntity):
    """Shows when the battery Set Power value was last changed."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "set_power_last_changed"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: HomeBatteryManagerCoordinator,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_set_power_last_changed"
        self._attr_device_info = _device_info(entry)
        self._attr_native_value: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to setpoint update signals from the coordinator."""
        signal = SIGNAL_SETPOINT_UPDATED.format(entry_id=self._entry.entry_id)
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_setpoint_update)
        )

    @callback
    def _handle_setpoint_update(self) -> None:
        self._attr_native_value = self._coordinator.set_power_last_changed
        self.async_write_ha_state()
