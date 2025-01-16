"""Module to manage meta ERDs."""

import logging
import math
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..const import (
    ATTR_ALLOWABLE,
    ATTR_ENABLED,
    ATTR_MAX_VAL,
    ATTR_MIN_VAL,
    ATTR_UNIQUE_ID,
    ATTR_UNIT,
    DOMAIN,
    SERVICE_ENABLE_OR_DISABLE,
    SERVICE_SET_ALLOWABLES,
    SERVICE_SET_MAX,
    SERVICE_SET_MIN,
    SERVICE_SET_UNIT,
    Erd,
)
from .data_source import DataSource

_LOGGER = logging.getLogger(__name__)


async def set_min(
    hass: HomeAssistant,
    _data_source: DataSource,
    _meta_erd: Erd,
    min_val_bytes: bytes,
    entity_id: str,
    unique_id: str,
) -> None:
    """Set the min value for the number entity."""
    min_val = int.from_bytes(min_val_bytes)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_MIN,
        {ATTR_ENTITY_ID: entity_id, ATTR_UNIQUE_ID: unique_id, ATTR_MIN_VAL: min_val},
    )


async def set_max(
    hass: HomeAssistant,
    _data_source: DataSource,
    _meta_erd: Erd,
    max_val_bytes: bytes,
    entity_id: str,
    unique_id: str,
) -> None:
    """Set the max value for the number entity."""
    max_val = int.from_bytes(max_val_bytes)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_MAX,
        {ATTR_ENTITY_ID: entity_id, ATTR_UNIQUE_ID: unique_id, ATTR_MAX_VAL: max_val},
    )


async def set_unit(
    hass: HomeAssistant,
    data_source: DataSource,
    meta_erd: Erd,
    unit_selection_bytes: bytes,
    entity_id: str,
    unique_id: str,
) -> None:
    """Set the unit for the number entity."""
    unit_selection = int.from_bytes(unit_selection_bytes)
    unit = await data_source.get_erd_def(meta_erd)
    if unit is not None:
        unit = unit["data"][0]["values"][f"{unit_selection}"]
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_UNIT,
            {ATTR_ENTITY_ID: entity_id, ATTR_UNIQUE_ID: unique_id, ATTR_UNIT: unit},
        )


async def enable_or_disable(
    hass: HomeAssistant,
    _data_source: DataSource,
    _meta_erd: Erd,
    enabled_bytes: bytes,
    entity_id: str,
    unique_id: str,
) -> None:
    """Enable or disable the entity."""
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE_OR_DISABLE,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_UNIQUE_ID: unique_id,
            ATTR_ENABLED: enabled_bytes != b"\x00",
        },
    )


async def set_allowables(
    hass: HomeAssistant,
    _data_source: DataSource,
    _meta_erd: Erd,
    allowables_bytes: bytes,
    entity_id: str,
    unique_id: str,
) -> None:
    """Set the allowable options for the select entity."""
    split = unique_id.split(".")
    option = split[1]
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_ALLOWABLES,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_UNIQUE_ID: split[0],
            ATTR_ALLOWABLE: option,
            ATTR_ENABLED: (int.from_bytes(allowables_bytes) & 0xFF) != 0,
        },
    )


class MetaErdCoordinator:
    """Class to manage meta ERDs and apply transforms."""

    def __init__(self, data_source: DataSource, hass: HomeAssistant) -> None:
        """Create the meta ERD coordinator."""
        self._entity_registry = er.async_get(hass)
        self._hass = hass
        self._data_source = data_source
        self._transform_table = _TRANSFORM_TABLE
        self._create_entities_to_meta_erds_dict()

    def _create_entities_to_meta_erds_dict(self) -> None:
        self._entities_to_meta_erds = {
            entity_id: meta_erd
            for meta_erd, row_dict in self._transform_table.items()
            for transform_row in row_dict.values()
            for entity_id in transform_row["fields"]
        }

    async def is_meta_erd(self, erd: Erd) -> bool:
        """Return true if the given ERD is a meta ERD."""
        return erd in self._transform_table

    async def apply_transforms_for_meta_erd(
        self, device_name: str, meta_erd: Erd
    ) -> None:
        """Apply transforms for the given meta ERD. Will raise KeyError if meta_erd is not a meta ERD."""
        for meta_field, transform_row in self._transform_table[meta_erd].items():
            field_bytes = await self.get_bytes_for_field(
                device_name, meta_erd, meta_field
            )
            if field_bytes is not None:
                for target_entity, offset in zip(
                    transform_row["fields"], transform_row["offsets"]
                ):
                    split = target_entity.split("_", 2)

                    await transform_row["func"](
                        self._hass,
                        self._data_source,
                        meta_erd,
                        field_bytes,
                        await self._data_source.get_entity_id_for_field(
                            device_name, int(split[1], base=16), offset
                        ),
                        target_entity.format(device_name),
                    )

    async def apply_transforms_to_entity(
        self, device_name: str, entity_id: str
    ) -> None:
        """Check if any meta ERDs have transforms for the given entity and apply them."""
        meta_erd = self._entities_to_meta_erds.get(entity_id)

        if meta_erd is not None:
            await self.apply_transforms_for_meta_erd(device_name, meta_erd)

    async def get_bytes_for_field(
        self, device_name: str, erd: Erd, field: str
    ) -> bytes | None:
        """Return the bytes associated with the given field."""
        try:
            erd_bytes = await self._data_source.erd_read(device_name, erd)
        except KeyError:  # If the meta ERD has not been added to the device yet, erd_read will raise a KeyError.
            return None  # This is fine because the transform will be applied when the meta ERD is added.

        if erd_bytes is None:
            return None

        erd_def = await self._data_source.get_erd_def(erd)
        if erd_def is None:
            _LOGGER.error(
                "Could not find ERD definition for meta ERD %s", f"{erd:#06x}"
            )
            return None

        for field_item in erd_def["data"]:
            if field_item["name"] == field:
                field_def = field_item

                field_bytes = erd_bytes[
                    field_def["offset"] : field_def["offset"] + field_def["size"]
                ]

        if field_bytes is not None:
            if "bits" in field_def:
                field_bytes = await self._get_bits_from_bytes(field_def, field_bytes)

        return field_bytes

    async def _get_bits_from_bytes(self, field_def: dict, field_bytes: bytes) -> bytes:
        """Return the bits from the bitfield for the specified ERD field."""
        offset = field_def["bits"]["offset"]
        size = field_def["bits"]["size"]

        byte = field_bytes[math.floor(offset / 8)]
        mask = (1 << size) - 1  # Mask for the lowest `size` bytes
        mask = mask << (8 - offset - size)  # Move mask to match offset
        masked = byte & mask

        return masked.to_bytes()


_TRANSFORM_TABLE: dict[Erd, dict[str, dict[str, Any]]] = {
    0x0007: {
        "Temperature Display Units": {
            "fields": ["number.target_cooling_temperature"],
            "offsets": [],
            "func": set_unit,
        }
    },
    0x4040: {
        "Available Modes.Hybrid": {
            "fields": ["select.mode.Hybrid"],
            "offsets": [],
            "func": set_allowables,
        },
        "Available Modes.Standard electric": {
            "fields": ["select.mode.Standard electric"],
            "offsets": [],
            "func": set_allowables,
        },
        "Available Modes.E-heat": {
            "fields": ["select.mode.E-heat"],
            "offsets": [],
            "func": set_allowables,
        },
        "Available Modes.HiDemand": {
            "fields": ["select.mode.HiDemand"],
            "offsets": [],
            "func": set_allowables,
        },
        "Available Modes.Vacation": {
            "fields": ["select.mode.Vacation"],
            "offsets": [],
            "func": set_allowables,
        },
    },
    0x4047: {
        "Minimum setpoint": {
            "fields": ["{}_4024_Temperature"],
            "offsets": [],
            "func": set_min,
        },
        "Maximum setpoint": {
            "fields": ["number.temperature"],
            "offsets": [],
            "func": set_max,
        },
    },
    0x214E: {
        "Eco Option Is In Client Writable State": {
            "fields": ["select.eco_option_status"],
            "offsets": [],
            "func": enable_or_disable,
        },
    },
}
