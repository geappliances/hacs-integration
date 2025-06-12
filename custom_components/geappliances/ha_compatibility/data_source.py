"""Home Assistant compatibility class for storing and accessing GE Appliances data."""

from collections.abc import Awaitable, Callable
import json
import re
from typing import Any

from ..const import Erd
from .event import Event
from .mqtt_client import GeaMQTTClient

SUPPORTED_ERDS = "supported_erds"
UNSUPPORTED_ERDS = "unsupported_erds"
VALUE = "value"
EVENT = "event"


class DataSource:
    """Class to store GE Appliances data."""

    def __init__(
        self,
        appliance_api: str,
        appliance_api_erd_definitions: str,
        mqtt_client: GeaMQTTClient,
    ) -> None:
        """Initialize data source class."""
        self._data: dict[str, Any] = {}
        self._appliance_api: dict[str, Any] = json.loads(appliance_api)
        self._appliance_api_erd_definitions: list[dict[str, Any]] = json.loads(
            appliance_api_erd_definitions
        )["erds"]
        self._mqtt_client = mqtt_client

        self._create_status_pair_dict()

    def _create_status_pair_dict(self):
        """Create a mapping of status/request ERD pairs based on their names and data fields."""

        def strip_name_field(data):
            """Return a list of dicts with 'name' key removed from each dict."""
            return [{k: v for k, v in item.items() if k != "name"} for item in data]

        self._status_pair_dict = {}
        temp_dict = {}

        status_pair_mapping = {
            "status": re.compile(
                r"\bStatus\b|\bActual\b|\bState\b|\bCurrent\b", re.IGNORECASE
            ),
            "request": re.compile(
                r"\bRequest\b|\bRequested\b|\bDesired\b", re.IGNORECASE
            ),
        }

        for erd in self._appliance_api_erd_definitions:
            name = erd["name"]
            for key, pattern in status_pair_mapping.items():
                if pattern.search(name):
                    base_name = pattern.sub("", name)
                    base_name = re.sub(r"[^\w\s]", "", base_name)
                    base_name = re.sub(r"  ", " ", base_name).strip()
                    if base_name not in temp_dict:
                        temp_dict[base_name] = {}
                    temp_dict[base_name][key] = {
                        "id": erd["id"],
                        "data": erd.get("data", []),
                    }

        for base_name, pair in temp_dict.items():
            if "status" in pair and "request" in pair:
                status_data = strip_name_field(pair["status"]["data"])
                request_data = strip_name_field(pair["request"]["data"])
                if status_data == request_data:
                    self._status_pair_dict[pair["status"]["id"]] = {
                        "name": base_name,
                        "status": int(pair["status"]["id"], 16),
                        "request": int(pair["request"]["id"], 16),
                    }
                    self._status_pair_dict[pair["request"]["id"]] = {
                        "name": base_name,
                        "status": int(pair["status"]["id"], 16),
                        "request": int(pair["request"]["id"], 16),
                    }

    async def add_device(self, device_name: str, device_id: str) -> None:
        """Add a device to the data source. Does nothing if the device already exists in the data source."""
        if self._data.get(device_name) is None:
            self._data[device_name] = {
                "id": device_id,
                SUPPORTED_ERDS: {},
                UNSUPPORTED_ERDS: {},
            }

    async def get_device(self, device_name: str) -> dict[str, Any]:
        """Return the dict for the requested device or None if it doesn't exist."""
        return self._data[device_name]

    async def device_exists(self, device_name: str) -> bool:
        """Return true if the device is present in the data."""
        return device_name in self._data

    async def add_supported_erd_to_device(
        self, device_name: str, erd: Erd, value: bytes | None
    ) -> None:
        """Add the ERD to the specified device's list of supported ERDs."""
        if erd in self._data[device_name][UNSUPPORTED_ERDS]:
            await self.move_erd_to_supported(device_name, erd)
        else:
            self._data[device_name][SUPPORTED_ERDS][erd] = {
                VALUE: value,
                EVENT: Event(),
            }

    async def add_unsupported_erd_to_device(
        self, device_name: str, erd: Erd, value: bytes | None
    ) -> None:
        """Add the ERD to the device's list of unsupported ERDs."""
        if erd in self._data[device_name][SUPPORTED_ERDS]:
            await self.move_erd_to_unsupported(device_name, erd)
        else:
            self._data[device_name][UNSUPPORTED_ERDS][erd] = {
                VALUE: value,
                EVENT: Event(),
            }

    async def move_erd_to_supported(self, device_name: str, erd: Erd) -> None:
        """Move the given ERD to the supported list."""
        if erd not in self._data[device_name][SUPPORTED_ERDS]:
            self._data[device_name][SUPPORTED_ERDS][erd] = self._data[device_name][
                UNSUPPORTED_ERDS
            ].pop(erd)

    async def move_erd_to_unsupported(self, device_name: str, erd: Erd) -> None:
        """Move the given ERD to the unsupported list and set associated entities to STATE_UNKNOWN."""
        if erd not in self._data[device_name][UNSUPPORTED_ERDS]:
            self._data[device_name][UNSUPPORTED_ERDS][erd] = self._data[device_name][
                SUPPORTED_ERDS
            ].pop(erd)
            await self._data[device_name][UNSUPPORTED_ERDS][erd][EVENT].publish(None)

    async def move_all_erds_to_unsupported_for_api_erd(
        self, device_name: str, feature_type: str | None, version: str
    ) -> None:
        """Move all ERDs listed in the given appliance API manifest to the unsupported list."""
        appliance_api = (
            await self.get_common_appliance_api_version(version)
            if feature_type is None
            else await self.get_feature_api_version(feature_type, version)
        )
        if appliance_api is None:
            return

        for erd in appliance_api["required"]:
            erd_int = int(erd["erd"], base=16)
            if erd_int in self._data[device_name][SUPPORTED_ERDS]:
                await self.move_erd_to_unsupported(device_name, erd_int)

        for feature in appliance_api["features"]:
            for erd in feature["required"]:
                erd_int = int(erd["erd"], base=16)
                if erd_int in self._data[device_name][SUPPORTED_ERDS]:
                    await self.move_erd_to_unsupported(device_name, erd_int)

    async def erd_is_supported_by_device(self, device_name: str, erd: Erd) -> bool:
        """Return true if the ERD is in the device's ERD list."""
        return erd in self._data[device_name][SUPPORTED_ERDS]

    async def _get_erd_from_either_list(
        self, device_name: str, erd: Erd
    ) -> dict[str, Any]:
        """Return the given erd, raising a KeyError if it doesn't exist."""
        if erd in self._data[device_name][SUPPORTED_ERDS]:
            return self._data[device_name][SUPPORTED_ERDS][erd]

        return self._data[device_name][UNSUPPORTED_ERDS][erd]

    async def erd_read(self, device_name: str, erd: Erd) -> bytes:
        """Return the value of the specified ERD. Raises if the ERD is not present on the given device."""
        return (await self._get_erd_from_either_list(device_name, erd))[VALUE]

    async def erd_write(self, device_name: str, erd: Erd, value: bytes) -> None:
        """Write a value to a given ERD on a device."""
        if erd in self._data[device_name][SUPPORTED_ERDS]:
            self._data[device_name][SUPPORTED_ERDS][erd][VALUE] = value
            await self._data[device_name][SUPPORTED_ERDS][erd][EVENT].publish(value)
        else:
            self._data[device_name][UNSUPPORTED_ERDS][erd][VALUE] = value

    async def erd_publish(self, device_name: str, erd: Erd, value: bytes) -> None:
        """Write a value to a given ERD on a device and publish to MQTT."""
        if erd in self._data[device_name][SUPPORTED_ERDS]:
            if await self._mqtt_client.publish_erd(device_name, erd, value):
                await self.erd_write(device_name, erd, value)
        else:
            await self.erd_write(device_name, erd, value)

    async def erd_subscribe(
        self, device_name: str, erd: Erd, callback: Callable[[bytes], Awaitable[None]]
    ) -> None:
        """Add the callback to the ERD's callback list."""
        await (await self._get_erd_from_either_list(device_name, erd))[EVENT].subscribe(
            callback
        )

    async def erd_unsubscribe(
        self, device_name: str, erd: Erd, callback: Callable[[bytes], Awaitable[None]]
    ) -> None:
        """Remove the callback from the ERD's callback list."""
        await (await self._get_erd_from_either_list(device_name, erd))[
            EVENT
        ].unsubscribe(callback)

    async def _get_erd_or_none_from_either_list(
        self, device_name: str, erd: Erd
    ) -> dict[str, Any] | None:
        """Return the given erd if it is present in either list."""
        if erd in self._data[device_name][SUPPORTED_ERDS]:
            return self._data[device_name][SUPPORTED_ERDS][erd]

        return self._data[device_name][UNSUPPORTED_ERDS].get(erd)

    async def erd_has_subscribers(self, device_name: str, erd: Erd) -> bool:
        """Return true if the ERD has subscribers to its event."""
        erd_val = await self._get_erd_or_none_from_either_list(device_name, erd)
        if erd_val is not None:
            return await erd_val[EVENT].has_subscribers()

        return False

    async def get_common_appliance_api_version(
        self, version: str
    ) -> dict[str, Any] | None:
        """Return the dict for the requested common appliance API version, or None if it doesn't exist."""
        return self._appliance_api["common"]["versions"].get(version)

    async def get_feature_api_version(
        self, feature_type: str, version: str
    ) -> dict[str, Any] | None:
        """Return the dict for the requested feature appliance API version, or None if it doesn't exist."""
        feature_appliance_api = self._appliance_api["featureApis"].get(feature_type)
        if feature_appliance_api is None:
            return None

        return feature_appliance_api["versions"].get(version)

    async def get_erd_def(self, erd: Erd) -> dict[str, Any] | None:
        """Find an ERD's fields in the appliance API ERD definitions."""
        for erd_def in self._appliance_api_erd_definitions:
            if erd_def["id"] == f"{erd:#06x}":
                return erd_def

        return None

    async def get_entity_id_for_unique_id(
        self, device_name: str, erd: Erd, unique_id: str, unique_id_with_option: str
    ) -> str | None:
        """Return the entity ID of the entity associated with the given unique ID."""
        erd_val = await self._get_erd_or_none_from_either_list(device_name, erd)
        if erd_val is not None:
            return await erd_val[EVENT].get_subscriber_with_unique_id(
                unique_id, unique_id_with_option
            )

        return None

    async def get_erd_status_pair(self, erd: Erd) -> dict[str, Any] | None:
        """Return the status/request pair dict if the given ERD is part of a status/request pair, otherwise None."""
        return self._status_pair_dict.get(f"{erd:#06x}", None)
