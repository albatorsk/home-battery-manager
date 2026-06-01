"""Constants for Home Battery Manager."""

DOMAIN = "home_battery_manager"

# Config entry keys
CONF_POWER_METER = "power_meter_entity"
CONF_BATTERY_SET_POWER = "battery_set_power_entity"
CONF_BATTERY_SOC = "battery_soc_entity"
CONF_MAX_CHARGE_POWER = "max_charge_power"
CONF_MAX_DISCHARGE_POWER = "max_discharge_power"

# Defaults
DEFAULT_MAX_CHARGE_POWER = 5000  # W
DEFAULT_MAX_DISCHARGE_POWER = 5000  # W

# Dispatcher signal sent when the battery power setpoint changes.
# Format with entry_id before use.
SIGNAL_SETPOINT_UPDATED = DOMAIN + "_{entry_id}_setpoint_updated"
