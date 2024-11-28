"""Config flow for powersensor_local."""

from powersensor_local import PowersensorDevices

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN

async def ignore(_: dict):
    pass

async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    psd = PowersensorDevices()
    count = await psd.start(ignore)
    await psd.stop()
    return count > 0


config_entry_flow.register_discovery_flow(DOMAIN, "powersensor_local", _async_has_devices)
