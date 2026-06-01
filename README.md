# Home Battery Manager

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that manages a home battery for **zero-export grid balancing**. It monitors your house power meter and automatically adjusts the battery charge/discharge power to keep your grid import/export as close to 0 W as possible.

## Features

- **Config flow** — set up entirely through the Home Assistant web UI; no YAML required
- **Zero-export control loop** — reacts to every power meter state change and commands the battery power to offset house consumption or solar production
- **Automatic clamping** — respects the min/max limits declared by the battery number entity and your configured power caps
- **Battery State of Charge sensor** — tracks and exposes your battery SoC with the correct device class
- **Power Setpoint sensor** — shows the last watt value commanded to the battery

## Requirements

- Home Assistant 2024.1 or newer
- A **power meter** sensor entity reporting net grid power in watts (positive = importing, negative = exporting)
- A **battery Set Power** `number` entity that accepts a watt value (positive = charge, negative = discharge)
- A **battery State of Charge** sensor entity reporting a percentage

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** and click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/albatorsk/home-battery-manager` as an **Integration**.
4. Search for **Home Battery Manager** and click **Download**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/home_battery_manager` folder into your `<config>/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

After installation, go to **Settings → Devices & Services → Add Integration** and search for **Home Battery Manager**.

You will be asked to select:

| Field | Description |
|-------|-------------|
| House Power Meter | Sensor measuring net grid power (W). Positive = import, negative = export. |
| Battery Set Power | Number entity to command battery power (W). Positive = charge, negative = discharge. |
| Battery State of Charge | Sensor reporting battery SoC (%). |
| Maximum Charge Power | Upper clamp for the charge setpoint (W). Default: 5000 W. |
| Maximum Discharge Power | Upper clamp for the discharge setpoint (W). Default: 5000 W. |

## How it works

Every time the power meter changes state the integration computes:

```
battery_setpoint = clamp(-house_power, -max_discharge, max_charge)
```

The clamped value is written to the battery Set Power entity via `number.set_value`. If the battery entity exposes `min`/`max` attributes those are preferred over the configured limits.

## Entities created

| Entity | Description |
|--------|-------------|
| `sensor.*_soc` | Battery State of Charge (%, device class: battery) |
| `sensor.*_power_setpoint` | Last power setpoint commanded to the battery (W) |
