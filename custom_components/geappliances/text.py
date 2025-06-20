"""Support for GE Appliances text inputs."""

import logging
from typing import Any

from homeassistant.components import text
from homeassistant.components.text import TextEntity
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
from .models import GeaTextConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GE Appliances text input dynamically through discovery."""
    platform = entity_platform.async_get_current_platform()
    SERVICE_ENABLE_OR_DISABLE = SERVICE_ENABLE_OR_DISABLE_BASE + "_text"

    async def handle_service_call(entity: GeaText, service_call: ServiceCall) -> None:
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
    async def async_discover(config: GeaTextConfig) -> None:
        """Discover and add a GE Appliances text input."""
        _LOGGER.debug("Adding text with name: %s", config.name)

        nonlocal entity_registry
        entity = GeaText(config)
        async_add_entities([entity])

        entity_registry.async_update_entity(
            entity.entity_id, device_id=config.device_id
        )

    async_dispatcher_connect(
        hass,
        GEA_ENTITY_NEW.format(text.const.DOMAIN),
        async_discover,
    )


class GeaText(TextEntity, GeaEntity):
    """Representation of a GE Appliances text input - allows the user to set values for string ERDs."""

    def __init__(self, config: GeaTextConfig) -> None:
        """Initialize the text."""
        self._attr_unique_id = config.unique_identifier
        self._attr_has_entity_name = True
        self._attr_name = config.name
        self._attr_should_poll = False
        self._field_bytes: bytes | None = None
        self._attr_native_max = config.size * 2 if config.is_raw_bytes else config.size
        self._erd = config.erd
        self._status_erd = config.status_erd or config.erd
        self._device_name = config.device_name
        self._data_source = config.data_source
        self._offset = config.offset
        self._size = config.size
        self._is_raw_bytes = config.is_raw_bytes

    @classmethod
    async def is_correct_platform_for_field(
        cls, field: dict[str, Any], writeable: bool
    ) -> bool:
        """Return true if text is an appropriate platform for the field."""
        return field["type"] in ["string", "raw"] and writeable

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
            self._field_bytes = None
        else:
            self._field_bytes = await self.get_field_bytes(value)

        self.async_schedule_update_ha_state(True)

    async def _get_bytes_from_value(self, value: str) -> bytes:
        """Convert the string value to bytes."""
        return value.encode()

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        erd_value = await self._data_source.erd_read(self._device_name, self._erd)
        if erd_value is not None:
            if self._is_raw_bytes:
                value_bytes = bytes.fromhex(value)
            else:
                value_bytes = await self._get_bytes_from_value(value)

            await self._data_source.erd_publish(
                self._device_name,
                self._erd,
                await self.set_field_bytes(erd_value, value_bytes),
            )

    @property
    def native_value(self) -> str | None:
        """Return value of the text."""
        if self._field_bytes is None:
            return None
        if self._is_raw_bytes:
            return self._field_bytes.hex()

        return self._field_bytes.decode()
