"""Support for GE Appliances number inputs."""

from collections.abc import Callable
import logging
import re
from typing import Any

from homeassistant.components import number
from homeassistant.components.number import NumberEntity
from homeassistant.components.number.const import NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ENABLED,
    ATTR_MAX_VAL,
    ATTR_MIN_VAL,
    ATTR_UNIQUE_ID,
    ATTR_UNIT,
    GEA_ENTITY_NEW,
    SERVICE_ENABLE_OR_DISABLE_BASE,
    SERVICE_ENABLE_OR_DISABLE_SCHEMA,
    SERVICE_SET_MAX,
    SERVICE_SET_MAX_SCHEMA,
    SERVICE_SET_MIN,
    SERVICE_SET_MIN_SCHEMA,
    SERVICE_SET_UNIT,
    SERVICE_SET_UNIT_SCHEMA,
)
from .entity import GeaEntity
from .models import GeaNumberConfig

_LOGGER = logging.getLogger(__name__)


class NumberConfigAttributes:
    """Class with helper functions for setting number config fields."""

    device_class_mapping: dict[str, NumberDeviceClass] = {
        r"Temperature": NumberDeviceClass.TEMPERATURE,
        r"Battery Level": NumberDeviceClass.BATTERY,
        r"kWh": NumberDeviceClass.ENERGY,
        r"Humidity": NumberDeviceClass.HUMIDITY,
        r"(in Pa)": NumberDeviceClass.PRESSURE,
        r"gallons|(oz)": NumberDeviceClass.VOLUME_STORAGE,
        r"lbs": NumberDeviceClass.WEIGHT,
        r"mA": NumberDeviceClass.CURRENT,
        r"days|hours|minutes|seconds": NumberDeviceClass.DURATION,
        r"Watts": NumberDeviceClass.POWER,
        r"Voltage": NumberDeviceClass.VOLTAGE,
        r"Hz": NumberDeviceClass.FREQUENCY,
    }

    @classmethod
    async def get_device_class(cls, field: dict[str, Any]) -> NumberDeviceClass | None:
        """Determine the appropriate number device class for the given field."""
        for name_substring, device_class in cls.device_class_mapping.items():
            if re.search(name_substring, field["name"]) is not None:
                return device_class

        return None

    @classmethod
    async def get_min(cls, field: dict[str, Any]) -> float:
        """Return the correct minimum value for the data type."""
        if field["type"] == "i8":
            return -128.0

        if field["type"] == "i16":
            return -32_768.0

        if field["type"] == "i32":
            return -2_147_483_648.0

        if field["type"] == "i64":
            return -9_223_372_036_854_775_808.0

        return 0.0

    @classmethod
    async def get_max(cls, field: dict[str, Any]) -> float:
        """Return the correct maximum value for the data type."""
        if field["type"] == "i8":
            return 127.0

        if field["type"] == "i16":
            return 32_767.0

        if field["type"] == "i32":
            return 214_7483_647.0

        if field["type"] == "i64":
            return 9_223_372_036_854_775_807.0

        if field["type"] == "u8":
            return 255.0

        if field["type"] == "u16":
            return 65_535.0

        if field["type"] == "u32":
            return 4_294_967_296.0

        if field["type"] == "u64":
            return 18_446_744_073_709_551_615.0

        return 0.0

    @classmethod
    async def is_value_signed(cls, field: dict[str, Any]) -> bool:
        """Return true if the field is a signed integer and false otherwise."""
        return field["type"] in ["i8", "i16", "i32"]

    @classmethod
    async def get_value_function(cls, field: dict[str, Any]) -> Callable[[bytes], Any]:
        """Return the appropriate function to format the number's value."""
        if await cls.is_value_signed(field):
            return lambda value: int.from_bytes(value, signed=True)

        return lambda value: int.from_bytes(value)  # pylint: disable=unnecessary-lambda


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GE Appliances number input dynamically through discovery."""
    platform = entity_platform.async_get_current_platform()
    SERVICE_ENABLE_OR_DISABLE = SERVICE_ENABLE_OR_DISABLE_BASE + "_number"

    async def handle_service_call(entity: GeaNumber, service_call: ServiceCall):
        if entity.unique_id == service_call.data[ATTR_UNIQUE_ID]:
            if service_call.service == SERVICE_ENABLE_OR_DISABLE:
                await entity.enable_or_disable(service_call.data[ATTR_ENABLED])
            elif service_call.service == SERVICE_SET_MIN:
                await entity.set_min(service_call.data[ATTR_MIN_VAL])
            elif service_call.service == SERVICE_SET_MAX:
                await entity.set_max(service_call.data[ATTR_MAX_VAL])
            elif service_call.service == SERVICE_SET_UNIT:
                await entity.set_unit(service_call.data[ATTR_UNIT])

    platform.async_register_entity_service(
        SERVICE_ENABLE_OR_DISABLE,
        SERVICE_ENABLE_OR_DISABLE_SCHEMA,
        handle_service_call,
    )

    platform.async_register_entity_service(
        SERVICE_SET_MIN,
        SERVICE_SET_MIN_SCHEMA,
        handle_service_call,
    )

    platform.async_register_entity_service(
        SERVICE_SET_MAX,
        SERVICE_SET_MAX_SCHEMA,
        handle_service_call,
    )

    platform.async_register_entity_service(
        SERVICE_SET_UNIT,
        SERVICE_SET_UNIT_SCHEMA,
        handle_service_call,
    )

    entity_registry = er.async_get(hass)

    @callback
    async def async_discover(config: GeaNumberConfig) -> None:
        """Discover and add a GE Appliances number input."""
        _LOGGER.debug("Adding number with name: %s", config.name)

        nonlocal entity_registry
        entity = GeaNumber(config)
        async_add_entities([entity])

        entity_registry.async_update_entity(
            entity.entity_id, device_id=config.device_id
        )

    async_dispatcher_connect(
        hass,
        GEA_ENTITY_NEW.format(number.const.DOMAIN),
        async_discover,
    )


class GeaNumber(NumberEntity, GeaEntity):
    """Representation of a GE Appliances number input - allows the user to set values for numerical ERDs."""

    def __init__(self, config: GeaNumberConfig) -> None:
        """Initialize the number."""
        self._attr_unique_id = config.unique_identifier
        self._attr_has_entity_name = True
        self._attr_name = config.name
        self._attr_should_poll = False
        self._attr_device_class = config.device_class
        self._field_bytes: bytes | None = None
        self._attr_native_unit_of_measurement = config.unit
        self._attr_suggested_unit_of_measurement = config.unit
        self._attr_native_min_value = config.min
        self._attr_native_max_value = config.max
        self._attr_native_step = 1 / config.scale
        self._scale = config.scale
        self._erd = config.erd
        self._status_erd = config.status_erd or config.erd
        self._device_name = config.device_name
        self._data_source = config.data_source
        self._offset = config.offset
        self._size = config.size
        self._value_fn = config.value_func
        self._bit_mask = config.bit_mask
        self._bit_size = config.bit_size
        self._bit_offset = config.bit_offset

    @classmethod
    async def is_correct_platform_for_field(
        cls, field: dict[str, Any], writeable: bool
    ) -> bool:
        """Return true if number is an appropriate platform for the field."""
        supported_types = ["u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64"]
        return field["type"] in supported_types and writeable

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

    async def _get_bytes_from_value(self, value: float) -> bytes:
        """Cast the value to bytes depending on whether the number is signed or unsigned."""
        if self._attr_native_min_value < 0:
            return round(value).to_bytes(length=self._size, signed=True)
        return round(value).to_bytes(length=self._size)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        erd_value = await self._data_source.erd_read(self._device_name, self._erd)
        if erd_value is not None:
            value_bytes = await self._get_bytes_from_value(value * (self._scale or 1))

            if self._bit_mask is not None:
                cur_field_bytes = await self.get_field_bytes(erd_value)
                value_bytes = (
                    int.from_bytes(cur_field_bytes)
                    | (int(value) << (self._bit_size - self._bit_offset))
                ).to_bytes()

            await self._data_source.erd_publish(
                self._device_name,
                self._erd,
                await self.set_field_bytes(erd_value, value_bytes),
            )

    @property
    def native_value(self) -> int | None:
        """Return value of the number."""
        if self._field_bytes is None:
            return None

        val = self._value_fn(self._field_bytes)

        if self._bit_mask is not None:
            shift = (self._size * 8) - self._bit_size - self._bit_offset
            val = (val & self._bit_mask) >> shift

        return (val / self._scale) if self._scale > 1 else val

    async def set_min(self, min_val: float) -> None:
        """Set the minimum value."""
        self._attr_native_min_value = min_val / self._scale
        self.async_schedule_update_ha_state(True)

    async def set_max(self, max_val: float) -> None:
        """Set the minimum value."""
        self._attr_native_max_value = max_val / self._scale
        self.async_schedule_update_ha_state(True)

    async def set_unit(self, unit: str) -> None:
        "Set the unit."
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_unit_of_measurement = unit
        self.async_schedule_update_ha_state(True)
