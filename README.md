# Local Powersensor integration for HomeAssistant

A minimal project to get a feel for how much effort would be required
to implement full Powersensor support for HomeAssistant.

This integration only uses the network-local interface to source data from
the Powersensor devices (sensors and plugs), and does not provide any
integration with the full Powersensor account or cloud API.

To install this integration, download a Zip archive of this repo and extract
it under {your-HA-config-dir}/custom\_components/ (e.g.
`/home/homeassistant/.homeassistant/custom_components` — you may need to also
create the `custom_components/` directory yourself.

To add the integration, go to Settings -> Integrations -> Add Integration
and search for "Powersensor (local)". It will automatically discover the
Powersensor devices on your network. To discovery all devices may take just
over 30 seconds.

If for some reason not all devices were discovered, you can disable and
re-enable the integration to force a new discovery.

The custom device names as set in the app are not available locally. Manually
match up the devices by checking their MAC addresses from the device info via
the Devices tab.
