"""The powersensor_local integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from powersensor_local import PowersensorDevices

PLATFORMS: list[Platform] = [Platform.SENSOR]

class PowersensorDevicesManager:
    """Wrapper to collate devices and route events to the right entities."""
    def __init__(self, hass: HomeAssistant):
        self._hass: HomeAssistant = hass
        self._psd: PowersensorDevices = PowersensorDevices()
        self._found: dict[str,dict] = dict()
        self._subscribed = dict() # {[mac]: { [evname]: (cb, cb...) }}
        self._loaded: dict[str,list[Entity]] = dict() # [mac]: (Entity, ...)

    async def start(self):
        """Start listening for Powersensor device events."""
        await self._psd.start(self._on_event)

    async def stop(self):
        """Stop listening for Powersensor device events."""
        await self._psd.stop()

    async def _on_event(self, msg):
        """Common event callback for Powersensor device events.
        Dispatches non-device_{found,lost}events to any subscribed handlers.
        """
        if not 'mac' in msg:
            # e.g. scan_complete message
            return
        mac = msg['mac']
        if (msg['event'] == 'device_found'):
            self._found[mac] = msg
            if mac in self._loaded.keys():
                for entity in self._loaded[mac]:
                    entity.set_available(True)
        elif (msg['event'] == 'device_lost'):
            del self._found[mac]
            if mac in self._loaded.keys():
                for entity in self._loaded[mac]:
                    entity.set_available(False)
        elif mac in self._subscribed:
            dev = self._subscribed[mac]
            ev = msg['event']
            if ev in dev:
                cb_list = dev[ev]
                for cb in cb_list:
                    await cb(msg)

    def get_newfound(self):
        """Returns the {mac,evt} list of devices which have not already been
        added to HomeAssistant.
        """
        out = dict()
        for mac in self._found:
            if not mac in self._loaded.keys():
                out[mac] = self._found[mac]
        return out

    def mark_loaded(self, mac: str, entity: Entity):
        """Mark a device as loaded, and provide the entity for future reference."""
        if not mac in self._loaded.keys():
            self._loaded[mac] = list()
        self._loaded[mac].append(entity)

    def mark_unloaded(self, mac:str, entity: Entity):
        """Marks a device as no longer being loaded into HomeAssistant."""
        if mac in self._loaded.keys():
            entities = self._loaded[mac]
            if entity in entities:
                entities.remove(entity)
                if len(entities) == 0:
                    del self._loaded[mac]

    def subscribe(self, mac: str, event: str, async_callback):
        need_subscribe = False
        if not mac in self._subscribed:
            self._subscribed[mac] = dict()
            need_subscribe = True
        dev = self._subscribed[mac]
        if not event in dev:
            dev[event] = []
            need_subscribe = True
        cb_list = dev[event]
        if not async_callback in cb_list:
            cb_list.append(async_callback)
        if need_subscribe:
            self._psd.subscribe(mac)

    def unsubscribe(self, mac: str, event: str, async_callback):
        last = False
        if mac in self._subscribed:
            dev = self._subscribed[mac]
            if event in dev:
                cb_list = dev[event]
                if async_callback in cb_list:
                    cb_list.remove(async_callback)
                if len(cb_list) == 0:
                    last = True
                    del dev[event]
            if last and len(dev.keys()) == 0:
                del self._subscribed[mac]
                self._psd.unsubscribe(mac)


type powersensor_localConfigEntry = ConfigEntry[PowersensorDevicesManager]


async def async_setup_entry(hass: HomeAssistant, entry: powersensor_localConfigEntry) -> bool:
    """Set up powersensor_local from a config entry."""
    psm = PowersensorDevicesManager(hass)
    entry.runtime_data = psm
    await psm.start()
    await asyncio.sleep(33) # Enough time for 30sec samplers to come through

    # TODO: can we call this later too if we discover additional devices?
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: powersensor_localConfigEntry) -> bool:
    """Unload a config entry."""
    #await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS)
    psm = entry.runtime_data
    await psm.stop()
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return result
