"""Constants for Home Battery Manager."""

DOMAIN = "home_battery_manager"

# Config entry keys
CONF_USE_DUAL_POWER_METERS = "use_dual_power_meters"

# Single-meter mode
CONF_POWER_METER = "power_meter_entity"

# Dual-meter mode
CONF_POWER_METER_IMPORT = "power_meter_import_entity"
CONF_POWER_METER_EXPORT = "power_meter_export_entity"

CONF_BATTERY_SET_POWER = "battery_set_power_entity"
CONF_INVERT_SET_POWER = "invert_set_power"
CONF_MAX_CHARGE_POWER = "max_charge_power"
CONF_MAX_DISCHARGE_POWER = "max_discharge_power"
CONF_UPDATE_INTERVAL_SECONDS = "update_interval_seconds"
CONF_OVERSHOOT_POWER = "overshoot_power"

# Defaults
DEFAULT_MAX_CHARGE_POWER = 5000  # W
DEFAULT_MAX_DISCHARGE_POWER = 5000  # W
DEFAULT_UPDATE_INTERVAL_SECONDS = 5  # s
DEFAULT_OVERSHOOT_POWER = 0  # W

# Dispatcher signal sent when the battery power setpoint changes.
# Format with entry_id before use.
SIGNAL_SETPOINT_UPDATED = DOMAIN + "_{entry_id}_setpoint_updated"
