from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    format_mac,
    DeviceInfo,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfPower,
)

from . import (
    PowersensorDevicesManager,
    powersensor_localConfigEntry,
)
from .const import DOMAIN


class PsSensorEntity(SensorEntity):
    should_poll = False
    _attr_has_entity_name = True

    def __init__(self, psm:PowersensorDevicesManager, evt: dict, name: str, devclass, unit, event: str, key: str, formatter, precision: int):
        self._psm = psm
        self._mac = evt['mac']
        self._typ = evt['device_type']

        self.device_class = devclass
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
            self._attr_native_value = self._formatter(msg[self._key])
        self.async_write_ha_state()


FMT_INT = lambda f: int(f)
FMT_3DEC = lambda f: f"{f:.3f}"
FMT_NONEGINT = lambda f: int(max(0, f))

SUPPORTED_DEVICE_ENTITIES = {
    'sensor': (
        ('Power', SensorDeviceClass.POWER, UnitOfPower.WATT, 'average_power', 'watts', FMT_INT, 0),
        ('Battery Level (Volts)', SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, 'battery_level', 'volts', FMT_3DEC, 3)
    ),
    'plug': [
        ('Power', SensorDeviceClass.POWER, UnitOfPower.WATT, 'average_power', 'watts', FMT_NONEGINT, 0),
        ('Mains Voltage', SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, 'voltage', 'volts', FMT_3DEC, 3)
    ]
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
                entities.append(PsSensorEntity(psm, evt, *desc))
            async_add_entities(entities)

    # Dynamically add as devices are found
    await psm.set_found_callback(add_found)
