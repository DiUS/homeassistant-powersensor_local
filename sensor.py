from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    format_mac,
    DeviceInfo,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)

from . import (
    PowersensorDevicesManager,
    powersensor_localConfigEntry,
)
from .const import DOMAIN

from datetime import datetime, timezone

class PsHouseholdEntity(SensorEntity):
    should_poll = False
    _attr_has_entity_name = True
    _attr_available = True

    def __init__(self, psm:PowersensorDevicesManager, name: str, devclass, state_class, unit, event: str, key: str, formatter, precision: int):
        self._psm = psm
        self._attr_name = name
        self._attr_friendly_name = name
        self.device_class = devclass
        self.state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_display_precision = precision
        self._attr_unique_id = f"PsVHH{event}/{key}"

        self._event = event
        self._key = key
        self._formatter = formatter

    @property
    def device_info(self) -> DeviceInfo:
        return {
            'identifiers': {(DOMAIN, 'vhh')},
            'manufacturer': 'Powersensor',
            'model': 'Virtual',
            'name': 'Powersensor Household View',
        }

    async def async_added_to_hass(self):
        self._psm.vhh.subscribe(self._event, self._on_event)

    async def async_will_remove_from_hass(self):
        self._psm.vhh.unsubscribe(self._event, self._on_event)

    async def _on_event(self, _, msg):
        if self._key in msg:
            val = msg[self._key]
            self._attr_native_value = self._formatter(val)
            sru = 'summation_resettime_utc'
            if sru in msg:
                self._attr_last_reset = datetime.fromtimestamp(msg[sru])
            self.async_write_ha_state()

class PsSensorEntity(SensorEntity):
    should_poll = False
    _attr_has_entity_name = True

    def __init__(self, psm:PowersensorDevicesManager, evt: dict, name: str, devclass, state_class, unit, event: str, key: str, formatter, precision: int):
        self._psm = psm
        self._mac = evt['mac']
        self._typ = evt['device_type']

        self.device_class = devclass
        self.state_class = state_class
        self._attr_name = name
        self._attr_friendly_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_available = True
        self._attr_unique_id = f"{format_mac(self._mac)}_{event}_{key}"

        self._event = event
        self._key = key
        self._formatter = formatter
        self._attr_suggested_display_precision = precision

        self._model = f"Powersensor{' Plug' if self._typ=='plug' else ''}"
        self._device_name = f"{self._model} ({self._mac})"

    def set_available(self, avail: bool):
        self._attr_available = avail
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return {
            'identifiers': {(DOMAIN, self._mac)},
            'manufacturer': "Powersensor",
            'model': self._model,
            'name': self._device_name,
            # "via_device": # if we use this, can it be updated dynamically?
        }

    def _clamp_solar_value(self, val: float):
        return -val if val <= 0 else 0

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._psm.subscribe(self._mac, self._event, self._on_event)
        self._psm.mark_loaded(self._mac, self)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._psm.unsubscribe(self._mac, self._event, self._on_event)
        self._psm.mark_unloaded(self._mac, self)

    async def _on_event(self, msg: dict):
        """Callback for consuming event messages."""
        if self._key in msg:
            val = msg[self._key]
            if 'role' in msg and msg['role'] == 'solar' and self._key != 'volts':
                val = self._clamp_solar_value(val)
            self._attr_native_value = self._formatter(val)
            sru = 'summation_resettime_utc'
            if sru in msg:
                self._attr_last_reset = datetime.fromtimestamp(msg[sru])
            self.async_write_ha_state()


FMT_INT = lambda f: int(f)
FMT_3DEC = lambda f: f"{f:.3f}"
FMT_NONEGINT = lambda f: int(max(0, f))
FMT_WS_TO_KWH = lambda f: FMT_3DEC(f/3600000)

SUPPORTED_DEVICE_ENTITIES = {
    'sensor': [
        ('Power', SensorDeviceClass.POWER, None, UnitOfPower.WATT, 'average_power', 'watts', FMT_INT, 0),
        ('Battery Level (Volts)', SensorDeviceClass.VOLTAGE, None, UnitOfElectricPotential.VOLT, 'battery_level', 'volts', FMT_3DEC, 3),
        ('Total energy', SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.KILO_WATT_HOUR, 'summation_energy', 'summation_joules', FMT_WS_TO_KWH, 1),
    ],
    'plug': [
        ('Power', SensorDeviceClass.POWER, None, UnitOfPower.WATT, 'average_power', 'watts', FMT_NONEGINT, 0),
        ('Mains Voltage', SensorDeviceClass.VOLTAGE, None, UnitOfElectricPotential.VOLT, 'average_power_components', 'volts', FMT_3DEC, 3),
        ('Total energy', SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.KILO_WATT_HOUR, 'summation_energy', 'summation_joules', FMT_WS_TO_KWH, 3),
    ],
    'virtual_household': [
        ('Power - Home use', SensorDeviceClass.POWER, None, UnitOfPower.WATT, 'home_usage', 'watts', FMT_INT, 0),
        ('Power - From grid', SensorDeviceClass.POWER, None, UnitOfPower.WATT, 'from_grid', 'watts', FMT_INT, 0),
        ('Power - To grid', SensorDeviceClass.POWER, None, UnitOfPower.WATT, 'to_grid', 'watts', FMT_INT, 0),
        ('Power - Solar generation', SensorDeviceClass.POWER, None, UnitOfPower.WATT, 'solar_generation', 'watts', FMT_INT, 0),
        ('Energy - Home usage', SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.KILO_WATT_HOUR, 'home_usage_summation', 'summation_joules', FMT_WS_TO_KWH, 3),
        ('Energy - From grid', SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.KILO_WATT_HOUR, 'from_grid_summation', 'summation_joules', FMT_WS_TO_KWH, 3),
        ('Energy - To grid', SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.KILO_WATT_HOUR, 'to_grid_summation', 'summation_joules', FMT_WS_TO_KWH, 3),
        ('Energy - Solar generation', SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.KILO_WATT_HOUR, 'solar_generation_summation', 'summation_joules', FMT_WS_TO_KWH, 3),
    ],
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: powersensor_localConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    psm = config_entry.runtime_data

    async def add_found(mac: str, evt: dict):
        devtype = evt['device_type']
        if devtype in SUPPORTED_DEVICE_ENTITIES:
            entities = []
            descriptions = SUPPORTED_DEVICE_ENTITIES[devtype]
            for desc in descriptions:
                try:
                    entities.append(PsSensorEntity(psm, evt, *desc))
                except Exception as e:
                    print(e)
            async_add_entities(entities)

    # Dynamically add as devices are found
    await psm.set_found_callback(add_found)

    # Register virtual household
    # TODO should only add solar if solar found
    entities = []
    descriptions = SUPPORTED_DEVICE_ENTITIES['virtual_household']
    for desc in descriptions:
        entities.append(PsHouseholdEntity(psm, *desc))
    async_add_entities(entities)
