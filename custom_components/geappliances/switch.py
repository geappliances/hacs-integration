"""Support for GE Appliances switches."""

import logging
from typing import Any

from homeassistant.components import switch
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ENABLED,
    ATTR_UNIQUE_ID,
    GEA_ENTITY_NEW,
    SERVICE_ENABLE_OR_DISABLE_BASE,
    SERVICE_ENABLE_OR_DISABLE_SCHEMA,
)
from .entity import GeaEntity
from .models import GeaSwitchConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GE Appliances switch dynamically through discovery."""
    platform = entity_platform.async_get_current_platform()
    SERVICE_ENABLE_OR_DISABLE = SERVICE_ENABLE_OR_DISABLE_BASE + "_switch"

    async def handle_service_call(entity: GeaSwitch, service_call: ServiceCall) -> None:
        if entity.unique_id == service_call.data[ATTR_UNIQUE_ID]:
            if service_call.service == SERVICE_ENABLE_OR_DISABLE:
                await entity.enable_or_disable(service_call.data[ATTR_ENABLED])

    platform.async_register_entity_service(
        SERVICE_ENABLE_OR_DISABLE,
        SERVICE_ENABLE_OR_DISABLE_SCHEMA,
        handle_service_call,
    )

    entity_registry = er.async_get(hass)

    @callback
    async def async_discover(config: GeaSwitchConfig) -> None:
        """Discover and add a GE Appliances switch."""
        _LOGGER.debug("Adding switch with name: %s", config.name)

        nonlocal entity_registry
        entity = GeaSwitch(config)
        async_add_entities([entity])

        entity_registry.async_update_entity(
            entity.entity_id, device_id=config.device_id
        )

    async_dispatcher_connect(
        hass,
        GEA_ENTITY_NEW.format(switch.const.DOMAIN),
        async_discover,
    )


class GeaSwitch(SwitchEntity, GeaEntity):
    """Representation of a GE Appliances switch."""

    def __init__(self, config: GeaSwitchConfig) -> None:
        """Initialize the switch."""
        self._attr_unique_id = config.unique_identifier
        self._attr_has_entity_name = True
        self._attr_name = config.name
        self._attr_should_poll = False
        self._erd = config.erd
        self._status_erd = config.status_erd or config.erd
        self._device_name = config.device_name
        self._data_source = config.data_source
        self._offset = config.offset
        self._size = config.size
        self._bit_mask = config.bit_mask

    @classmethod
    async def is_correct_platform_for_field(
        cls, field: dict[str, Any], writeable: bool
    ) -> bool:
        """Return true if switch is an appropriate platform for the field."""
        return field["type"] == "bool" and writeable

    async def async_added_to_hass(self) -> None:
        """Set initial state from ERD and set up callback for updates."""
        value = await self._data_source.erd_read(self._device_name, self._status_erd)
        await self.erd_updated(value)

        await self._data_source.erd_subscribe(
            self._device_name, self._status_erd, self.erd_updated
        )
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the ERD."""
        await self._data_source.erd_unsubscribe(
            self._device_name, self._status_erd, self.erd_updated
        )

    @callback
    async def erd_updated(self, value: bytes | None) -> None:
        """Update state from ERD."""
        if value is None:
            self._attr_is_on = None
        else:
            self._attr_is_on = (
                int.from_bytes(await self.get_field_bytes(value)) & self._bit_mask != 0
            )

        self.async_schedule_update_ha_state(True)

    @property
    async def async_is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        value = await self._data_source.erd_read(self._device_name, self._erd)
        if value is not None:
            if self._bit_mask == 0xFF:
                value = await self.set_field_bytes(value, bytes.fromhex("01"))
            else:
                value = await self.set_field_bytes(
                    value,
                    (value[self._offset] | self._bit_mask).to_bytes(),
                )

            await self._data_source.erd_publish(self._device_name, self._erd, value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        value = await self._data_source.erd_read(self._device_name, self._erd)
        if value is not None:
            value = await self.set_field_bytes(
                value,
                (value[self._offset] & ~self._bit_mask).to_bytes(),
            )
            await self._data_source.erd_publish(self._device_name, self._erd, value)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        if self._attr_is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()
