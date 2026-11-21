"""Base for AmpX's gateway-backed entities: one 'AI gateway' service device."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .const import CONF_GW_MODEL, DOMAIN


class GatewayEntity(Entity):
    _attr_has_entity_name = True
    _key = ""

    def __init__(self, brain) -> None:
        self.brain = brain
        entry = brain.entry
        self._attr_unique_id = f"{entry.entry_id}_gateway_{self._key}"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_gateway")},
            name="AmpX",
            manufacturer="AmpX",
            model=f"AI gateway · {brain.opts.get(CONF_GW_MODEL) or 'auto'}",
            entry_type=dr.DeviceEntryType.SERVICE,
            configuration_url=brain.gateway.base_url.removesuffix("/v1") or None,
        )
