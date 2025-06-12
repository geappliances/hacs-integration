"""Support for GE Appliances select inputs."""

import logging
from typing import Any

from homeassistant.components import select
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ALLOWABLE,
    ATTR_ENABLED,
    ATTR_UNIQUE_ID,
    GEA_ENTITY_NEW,
    SERVICE_ENABLE_OR_DISABLE_BASE,
    SERVICE_ENABLE_OR_DISABLE_SCHEMA,
    SERVICE_SET_ALLOWABLES,
    SERVICE_SET_ALLOWABLES_SCHEMA,
)
from .entity import GeaEntity
from .models import GeaSelectConfig

_LOGGER = logging.getLogger(__name__)


class SelectConfigAttributes:
    """Class with helper functions for setting select config fields."""

    @classmethod
    async def get_enum_values(cls, field: dict[str, Any]) -> dict[int, str]:
        """Return possible enum values."""

        vals: dict[int, str] = {}
        for key, val in field["values"].items():
            vals[int(key, base=10)] = val
        return vals


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GE Appliances select dropdown dynamically through discovery."""
    platform = entity_platform.async_get_current_platform()
    SERVICE_ENABLE_OR_DISABLE = SERVICE_ENABLE_OR_DISABLE_BASE + "_select"

    async def handle_service_call(entity: GeaSelect, service_call: ServiceCall) -> None:
        if entity.unique_id == service_call.data[ATTR_UNIQUE_ID]:
            if service_call.service == SERVICE_ENABLE_OR_DISABLE:
                await entity.enable_or_disable(service_call.data[ATTR_ENABLED])
            elif service_call.service == SERVICE_SET_ALLOWABLES:
                await entity.set_allowables(
                    service_call.data[ATTR_ALLOWABLE], service_call.data[ATTR_ENABLED]
                )

    platform.async_register_entity_service(
        SERVICE_ENABLE_OR_DISABLE,
        SERVICE_ENABLE_OR_DISABLE_SCHEMA,
        handle_service_call,
    )

    platform.async_register_entity_service(
        SERVICE_SET_ALLOWABLES, SERVICE_SET_ALLOWABLES_SCHEMA, handle_service_call
    )

    entity_registry = er.async_get(hass)

    @callback
    async def async_discover(config: GeaSelectConfig) -> None:
        """Discover and add a GE Appliances select dropdown."""
        _LOGGER.debug("Adding select with name: %s", config.name)

        nonlocal entity_registry
        entity = GeaSelect(config)
        async_add_entities([entity])

        entity_registry.async_update_entity(
            entity.entity_id, device_id=config.device_id
        )

    async_dispatcher_connect(
        hass,
        GEA_ENTITY_NEW.format(select.const.DOMAIN),
        async_discover,
    )


class GeaSelect(SelectEntity, GeaEntity):
    """Representation of a GE Appliances select dropdown - allows users to select enumerated values."""

    def __init__(self, config: GeaSelectConfig) -> None:
        """Initialize the select."""
        self._attr_unique_id = config.unique_identifier
        self._attr_has_entity_name = True
        self._attr_name = config.name
        self._attr_should_poll = False
        self._field_bytes: bytes | None = None
        self._enum_vals = config.enum_vals
        self._attr_options = list(config.enum_vals.values())
        self._erd = config.erd
        self._status_erd = config.status_erd or config.erd
        self._device_name = config.device_name
        self._data_source = config.data_source
        self._offset = config.offset
        self._size = config.size

    @classmethod
    async def is_correct_platform_for_field(
        cls, field: dict[str, Any], writeable: bool
    ) -> bool:
        """Return true if select is an appropriate platform for the field."""
        return field["type"] == "enum" and writeable

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

    async def _get_bytes_from_option(self, value: str) -> bytes:
        """Get the correct enum value for the selected option."""
        for key, item in self._enum_vals.items():
            if item == value:
                return key.to_bytes(length=self._size)

        raise HomeAssistantError

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        erd_value = await self._data_source.erd_read(self._device_name, self._erd)
        if erd_value is not None:
            option_bytes = await self._get_bytes_from_option(option)
            await self._data_source.erd_publish(
                self._device_name,
                self._erd,
                await self.set_field_bytes(erd_value, option_bytes),
            )

    @property
    def current_option(self) -> str | None:
        """Return value of the select."""
        if self._field_bytes is None:
            return None

        return self._enum_vals[int.from_bytes(self._field_bytes)]

    async def set_allowables(self, allowable: str, enabled: bool) -> None:
        """Update the allowable list of options."""
        if enabled:
            if allowable not in self._attr_options:
                self._attr_options.append(allowable)
        elif allowable in self._attr_options:
            self._attr_options.remove(allowable)
        self.async_schedule_update_ha_state(True)
