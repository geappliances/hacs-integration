"""Class to set up ERDs in memory and create entities for them."""

import logging
from typing import Any

from custom_components.geappliances.ha_compatibility.meta_erds import MetaErdCoordinator
from custom_components.geappliances.ha_compatibility.special_erds import (
    SpecialErdCoordinator,
)

from .config_factory import ConfigFactory
from .const import Erd
from .ha_compatibility.data_source import DataSource
from .ha_compatibility.registry_updater import RegistryUpdater
from .models import GeaEntityConfig

_LOGGER = logging.getLogger(__name__)


class ERDFactory:
    """Class to set up ERDs as they are discovered."""

    def __init__(
        self,
        registry_updater: RegistryUpdater,
        data_source: DataSource,
        meta_erd_coordinator: MetaErdCoordinator,
    ) -> None:
        """Store references to registry updater and data source."""
        self._registry_updater = registry_updater
        self._data_source = data_source
        self._config_factory = ConfigFactory(data_source)
        self._meta_erd_coordinator = meta_erd_coordinator
        self._special_erd_coordinator = SpecialErdCoordinator(
            data_source, self._config_factory
        )

    async def get_entity_configs(
        self, erd: Erd, device_name: str
    ) -> list[GeaEntityConfig]:
        """Generate an entity configuration based on the ERD and appliance type."""
        config_list = []
        if (erd_def := await self._data_source.get_erd_def(erd)) is not None:
            status_pair = await self._data_source.get_erd_status_pair(erd)
            if status_pair is None or status_pair["request"] == erd:
                config_list = [
                    await self._config_factory.build_config(
                        device_name,
                        erd,
                        status_pair["name"] if status_pair else erd_def["name"],
                        erd_def.get("description", ""),
                        field,
                        "write" in erd_def["operations"],
                    )
                    for field in erd_def["data"]
                ]
        else:
            _LOGGER.error("Could not find ERD %s", f"{erd:#06x}")

        return config_list

    async def set_up_erds(
        self, erd_api_list: list[dict[str, Any]], device_name: str
    ) -> None:
        """Set up all ERDs in the list so entities know how to interact with them."""
        for erd in erd_api_list:
            erd_int = int(erd["erd"], base=16)
            status_pair = await self._data_source.get_erd_status_pair(erd_int)
            if status_pair:
                if not await self._data_source.erd_has_subscribers(
                    device_name, status_pair["request"]
                ):
                    await self._data_source.add_supported_erd_to_device(
                        device_name, status_pair["request"], None
                    )
                if not await self._data_source.erd_has_subscribers(
                    device_name, status_pair["status"]
                ):
                    await self._data_source.add_supported_erd_to_device(
                        device_name, status_pair["status"], None
                    )
            else:
                await self._data_source.add_supported_erd_to_device(
                    device_name, erd_int, None
                )
            if not await self._data_source.erd_has_subscribers(device_name, erd_int):
                if await self._special_erd_coordinator.is_special_erd(erd_int):
                    entity_configs = (
                        await self._special_erd_coordinator.build_config_for_erd(
                            device_name,
                            erd_int,
                        )
                    )
                else:
                    entity_configs = await self.get_entity_configs(erd_int, device_name)

                for config in entity_configs:
                    await self._registry_updater.add_entity_to_device(
                        config, device_name
                    )
                    await self._meta_erd_coordinator.apply_transforms_to_entity(
                        device_name,
                        await self._get_entity_unique_id_for_config(config, erd_int),
                    )

    async def _get_entity_unique_id_for_config(
        self, config: GeaEntityConfig, erd: Erd
    ) -> str:
        """Return the Home Assistant entity name for the given config."""
        split = config.unique_identifier.split("_", 2)
        return "{}_" + split[1] + "_" + split[2]
