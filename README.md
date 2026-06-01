# Home Battery Manager

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that manages a home battery for **zero-export grid balancing**. It monitors your house power meter and automatically adjusts the battery charge/discharge power to keep your grid import/export as close to 0 W as possible.

## At a Glance

- **Purpose**: keep grid import/export near **0 W** by controlling battery set power
- **Control mode**: event-driven (runs when your power meter updates)
- **Setup**: UI-only config flow (no YAML)
- **Tuning**: options flow lets you change entities and limits later

## Quick Start (HACS)

1. In HACS, open **Integrations**.
2. Use **Custom repositories** and add:
	 `https://github.com/albatorsk/home-battery-manager` (Category: **Integration**)
3. Install **Home Battery Manager** from HACS.
4. Restart Home Assistant.
5. Go to **Settings -> Devices & Services -> Add Integration**.
6. Search for **Home Battery Manager** and follow the setup steps.

## You Need

- A house/grid power measurement in one of these modes
	- **Single meter mode**: one net power sensor in watts
	- Positive = importing from grid
	- Negative = exporting to grid
	- **Dual meter mode**: two separate sensors in watts
	- Import meter: positive when importing
	- Export meter: positive when exporting
- A **battery Set Power** `number` entity in watts
	- Positive = charge
	- Negative = discharge

## Features

- **Config flow** — set up entirely through the Home Assistant web UI; no YAML required
- **Options flow** — update configured entities and limits later without removing/re-adding the integration
- **Zero-export control loop** — reacts to every power meter state change and commands the battery power to offset house consumption or solar production
- **Automatic clamping** — respects the min/max limits declared by the battery number entity and your configured power caps
- **Power Setpoint sensor** — shows the last watt value commanded to the battery
- **Set Power Last Changed sensor** — timestamp of the most recent Set Power value change

## Requirements

- Home Assistant 2024.1 or newer
- A **power meter** sensor entity reporting net grid power in watts (positive = importing, negative = exporting)
- A **battery Set Power** `number` entity that accepts a watt value (positive = charge, negative = discharge)

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
| Use Separate Import and Export Meters | Toggle between one signed net meter and two positive-only meters. |
| House Power Meter | Sensor measuring net grid power (W). Positive = import, negative = export. |
| House Power Import Meter | Import sensor (W, positive values). Used in dual meter mode. |
| House Power Export Meter | Export sensor (W, positive values). Used in dual meter mode. |
| Battery Set Power | Number entity to command battery power (W). Positive = charge, negative = discharge. |
| Maximum Charge Power | Upper clamp for the charge setpoint (W). Default: 5000 W. |
| Maximum Discharge Power | Upper clamp for the discharge setpoint (W). Default: 5000 W. |
| Invert Set Power | Flip the sign of the calculated setpoint before sending it to the battery. |

After setup, open the integration and click **Configure** to change these values without removing and re-adding the integration.

## How it works

Every time the power meter changes state the integration computes:

```
battery_setpoint = clamp(-house_power, -max_discharge, max_charge)
```

Where:

- Single meter mode: `house_power = net_meter`
- Dual meter mode: `house_power = import_meter - export_meter`

If inversion is enabled, the sign is flipped before the value is clamped and written to the battery Set Power entity via `number.set_value`. If the battery entity exposes `min`/`max` attributes those are preferred over the configured limits.

### Example

- House power = `+1200 W` (importing)
	- Integration commands battery about `-1200 W` (discharge)
- House power = `-800 W` (exporting)
	- Integration commands battery about `+800 W` (charge)

Final command is always clamped to configured/entity limits.

## Entities created

| Entity | Description |
|--------|-------------|
| `sensor.*_power_setpoint` | Last power setpoint commanded to the battery (W) |
| `sensor.*_set_power_last_changed` | Timestamp when the Set Power value last changed |
