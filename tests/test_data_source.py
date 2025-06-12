"""Tests for GE Appliances data source."""

from collections.abc import Callable, Generator
import json
from typing import Any
from unittest.mock import MagicMock, patch

from custom_components.geappliances.const import Erd
from custom_components.geappliances.ha_compatibility.data_source import (
    UNSUPPORTED_ERDS,
    DataSource,
)
from custom_components.geappliances.ha_compatibility.mqtt_client import GeaMQTTClient
import pytest

from .doubles import MqttClientMock

COMMON_APPLIANCE_API_V1_JSON = """
{
    "required": [
        { "erd": "0x0001", "name": "Test", "length": 1 }
    ],
    "features": [
        {
            "mask": "0x00000001",
            "name": "Primary",
            "required": [
                { "erd": "0x0002", "name": "Another Test", "length": 1 }
            ]
        }
    ]
}"""

FEATURE_APPLIANCE_API_1_V1_JSON = """
{
    "required": [
        { "erd": "0x0003", "name": "Feature Test", "length": 1 }
    ],
    "features": [
        {
            "mask": "0x00000001",
            "name": "Primary",
            "required": [
                { "erd": "0x0004", "name": "Another Feature Test", "length": 1 }
            ]
        }
    ]
}"""

APPLIANCE_API_JSON = """
{
    "common": {
        "versions": {
            "1": {
                "required": [
                    { "erd": "0x0001", "name": "Test", "length": 1 }
                ],
                "features": [
                    {
                        "mask": "0x00000001",
                        "name": "Primary",
                        "required": [
                            { "erd": "0x0002", "name": "Another Test", "length": 1 }
                        ]
                    }
                ]
            }
        }
    },
    "featureApis": {
        "0": {
            "featureType": "0",
            "versions": {
                "1": {
                    "required": [
                        { "erd": "0x0003", "name": "Feature Test", "length": 1 }
                    ],
                    "features": [
                        {
                            "mask": "0x00000001",
                            "name": "Primary",
                            "required": [
                                { "erd": "0x0004", "name": "Another Feature Test", "length": 1 }
                            ]
                        }
                    ]
                }
            }
        },
        "1": {
            "featureType": "1",
            "versions": {
                "1": {
                    "required": [
                        { "erd": "0x0005", "name": "Multi Field Test", "length": 2 }
                    ],
                    "features": []
                }
            }
        },
        "2": {
            "featureType": "1",
            "versions": {
                "1": {
                    "required": [
                        { "erd": "0x0006", "name": "Test Request", "length": 1 },
                        { "erd": "0x0007", "name": "Test Status", "length": 1 },
                        { "erd": "0x0008", "name": "Test Two Requested", "length": 1 },
                        { "erd": "0x0009", "name": "Test Two Actual", "length": 1 },
                        { "erd": "0x000A", "name": "Test Three Desired", "length": 1 },
                        { "erd": "0x000B", "name": "Test Three State", "length": 1 }
                    ],
                    "features": []
                }
            }
        }
    }
}"""

ERD_1_DEFINITION_JSON = """
{
    "name": "Test",
    "id": "0x0001",
    "operations": ["read"],
    "data": [
        {
            "name": "Test",
            "type": "bool",
            "offset": 0,
            "size": 1
        }
    ]
}"""

APPLIANCE_API_DEFINTION_JSON = """
{
    "erds" :[
        {
            "name": "Test",
            "id": "0x0001",
            "operations": ["read"],
            "data": [
                {
                    "name": "Test",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Another Test",
            "id": "0x0002",
            "operations": ["read"],
            "data": [
                {
                    "name": "Another Test",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Feature Test",
            "id": "0x0003",
            "operations": ["read"],
            "data": [
                {
                    "name": "Feature Test",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Another Feature Test",
            "id": "0x0004",
            "operations": ["read"],
            "data": [
                {
                    "name": "Another Feature Test",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Multi Field Test",
            "id": "0x0005",
            "operations": ["read"],
            "data": [
                {
                    "name": "Field One",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Field Two",
                    "type": "bool",
                    "offset": 1,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Request",
            "id": "0x0006",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Request",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Status",
            "id": "0x0007",
            "operations": ["read"],
            "data": [
                {
                    "name": "Test Status",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Two Requested",
            "id": "0x0008",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Two",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Two Actual",
            "id": "0x0009",
            "operations": ["read"],
            "data": [
                {
                    "name": "Test Two",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Three Desired",
            "id": "0x000A",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Three",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Three State",
            "id": "0x000B",
            "operations": ["read"],
            "data": [
                {
                    "name": "Test Three",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        }
    ]
}"""

STATUS_PAIR_DICT = """
{
    "0x0006": {
        "name": "Test",
        "request": 6,
        "status": 7
    },
    "0x0007": {
        "name": "Test",
        "request": 6,
        "status": 7
    },
    "0x0008": {
        "name": "Test Two",
        "request": 8,
        "status": 9
    },
    "0x0009": {
        "name": "Test Two",
        "request": 8,
        "status": 9
    },
    "0x000A": {
        "name": "Test Three",
        "request": 10,
        "status": 11
    },
    "0x000B": {
        "name": "Test Three",
        "request": 10,
        "status": 11
    }
}
"""


@pytest.fixture
def mqtt_client_mock() -> MqttClientMock:
    """Return a mock instance of GeaMQTTClient."""
    return MagicMock(GeaMQTTClient)


@pytest.fixture
def data_source(mqtt_client_mock) -> DataSource:
    """Return an initialized DataSource instance."""
    return DataSource(
        APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
    )


async def must_be_called(*args: Any, **kwargs: Any) -> None:
    """Fail the test if not called."""


@pytest.fixture
def must_be_called_mock() -> Generator[MagicMock]:
    """Create must_be_called_mock."""
    with patch(__name__ + ".must_be_called") as called_mock:
        yield called_mock
        called_mock.assert_called()


async def given_a_device_is_added(device_name: str, data_source: DataSource) -> None:
    """Add a device to the data source."""
    await data_source.add_device(device_name, f"{device_name}_01")


async def given_a_supported_erd_is_added(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Add a supported ERD to the given device."""
    await data_source.add_supported_erd_to_device(device_name, erd, None)


async def given_an_unsupported_erd_is_added(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Add an unsupported ERD to the data source."""
    await data_source.add_unsupported_erd_to_device(device_name, erd, None)


async def given_erd_is_set_to(
    erd: Erd, value: bytes, device_name: str, data_source: DataSource
) -> None:
    """Set the given ERD to the desired state."""
    await data_source.erd_write(device_name, erd, value)


async def given_function_is_subscribed_to_erd(
    fn: Callable, erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Subscribe the function to the ERD."""
    await data_source.erd_subscribe(device_name, erd, fn)


async def given_function_is_unsubscribed_from_erd(
    fn: Callable, erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Unsubscribe the function from the ERD."""
    await data_source.erd_unsubscribe(device_name, erd, fn)


async def when_a_device_is_added(device_name: str, data_source: DataSource) -> None:
    """Add a device to the data source."""
    await given_a_device_is_added(device_name, data_source)


async def when_a_supported_erd_is_added(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Add a supported ERD to the data source."""
    await given_a_supported_erd_is_added(erd, device_name, data_source)


async def when_an_unsupported_erd_is_added(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Add an unsupported ERD to the data source."""
    await given_an_unsupported_erd_is_added(erd, device_name, data_source)


async def when_erd_is_published_with_value(
    erd: Erd, value: bytes, device_name: str, data_source: DataSource
) -> None:
    """Set the given ERD to the desired state."""
    await data_source.erd_publish(device_name, erd, value)


async def when_erd_is_set_to(
    erd: Erd, value: bytes, device_name: str, data_source: DataSource
) -> None:
    """Set the given ERD to the desired state."""
    await given_erd_is_set_to(erd, value, device_name, data_source)


async def when_the_erds_are_moved_to_unsupported_for_common_api(
    device_name: str, data_source: DataSource
) -> None:
    """Move all ERDs for the common appliance API to the unsupported list."""
    await data_source.move_all_erds_to_unsupported_for_api_erd(device_name, None, "1")


async def when_the_erds_are_moved_to_unsupported_for_feature_api(
    device_name: str, feature_type: str, data_source: DataSource
) -> None:
    """Move all ERDs for the given feature API to the unsupported list."""
    await data_source.move_all_erds_to_unsupported_for_api_erd(
        device_name, feature_type, "1"
    )


def the_device_dict_should_be_empty(data_source: DataSource) -> None:
    """Assert the device dictionary is empty."""
    assert data_source._data == {}


def the_appliance_api_should_be(appliance_api: str, data_source: DataSource) -> None:
    """Assert the appliance API is correct."""
    assert data_source._appliance_api == json.loads(appliance_api)


def the_appliance_api_erd_defs_should_be(
    appliance_api_erd_defs: str, data_source: DataSource
) -> None:
    """Assert the appliance API is correct."""
    assert (
        data_source._appliance_api_erd_definitions
        == json.loads(appliance_api_erd_defs)["erds"]
    )


def the_status_pair_dict_should_be(
    data_source: DataSource, status_pair_str: str
) -> None:
    """Assert the status pair dictionary contains the given ERD and status pair."""
    assert data_source._status_pair_dict == json.loads(status_pair_str)


def the_device_should_exist(device_name: str, data_source: DataSource) -> None:
    """Assert the given device exists in the data source."""
    assert data_source._data.get(device_name) is not None


async def the_device_should_support_erd(
    device_name: str, erd: Erd, data_source: DataSource
) -> None:
    """Assert that the device supports the given ERD."""
    assert await data_source.erd_is_supported_by_device(device_name, erd)


async def the_device_should_not_support_erd(
    device_name: str, erd: Erd, data_source: DataSource
) -> None:
    """Assert that the device does not support the given ERD but has it listed."""
    assert not await data_source.erd_is_supported_by_device(device_name, erd)
    assert data_source._data[device_name][UNSUPPORTED_ERDS].get(erd) is not None


async def adding_erd_should_raise_error(
    device_name: str, erd: Erd, data_source: DataSource
) -> None:
    """Assert that adding the given ERD raises an error."""
    try:
        await data_source.add_supported_erd_to_device(device_name, erd, None)
    except KeyError:
        return

    pytest.fail(
        f"Adding ERD {erd:#06x} to device '{device_name}' did not raise KeyError"
    )


async def the_erd_should_be(
    erd: Erd, value: bytes, device_name: str, data_source: DataSource
) -> None:
    """Assert that the ERD has the given value."""
    assert (await data_source.erd_read(device_name, erd)) == value


async def reading_from_erd_should_raise_error(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Assert that reading from the given ERD raises an error."""
    try:
        await data_source.erd_read(device_name, erd)
    except KeyError:
        return

    pytest.fail(
        f"Reading from ERD {erd:#06x} on device '{device_name}' did not raise KeyError"
    )


async def writing_to_erd_should_raise_error(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Assert that writing to the given ERD raises an error."""
    try:
        await data_source.erd_write(device_name, erd, b"")
    except KeyError:
        return

    pytest.fail(
        f"Reading from ERD {erd:#06x} on device '{device_name}' did not raise KeyError"
    )


def mqtt_should_publish(
    erd: Erd, value: bytes, device_name: str, mqtt_client_mock: MqttClientMock
) -> None:
    """Assert MQTT published a given ERD."""
    mqtt_client_mock.publish_erd.assert_called_with(device_name, erd, value)


def mqtt_should_not_publish(mqtt_client_mock: MqttClientMock) -> None:
    """Assert MQTT has not published anything."""
    mqtt_client_mock.publish_erd.assert_not_called()


async def publishing_erd_should_raise_error(
    erd: Erd, device_name: str, data_source: DataSource
) -> None:
    """Assert that publishing the given ERD raises an error."""
    try:
        await data_source.erd_publish(device_name, erd, b"")
    except KeyError:
        return

    pytest.fail(
        f"Publishing ERD {erd:#06x} on device '{device_name}' did not raise KeyError"
    )


def must_be_called_should_have_been_called(must_be_called_mock: MagicMock) -> None:
    """Assert must_be_called was called."""
    must_be_called_mock.assert_called()


def fail_when_called(*args: Any, **kwargs: Any) -> None:
    """Fail the test when called."""
    pytest.fail("fail_when_called was called")


def nothing_should_happen() -> None:
    """Do nothing."""


async def the_common_appliance_api_version_should_be(
    version: str, version_json: str, data_source: DataSource
) -> None:
    """Assert that the common appliance API JSON for the given version is correct."""
    assert await data_source.get_common_appliance_api_version(version) == json.loads(
        version_json
    )


async def the_feature_appliance_api_version_should_be(
    feature_type: str, version: str, version_json: str, data_source: DataSource
) -> None:
    """Assert that the feature appliance API JSON for the given version is correct."""
    assert await data_source.get_feature_api_version(
        feature_type, version
    ) == json.loads(version_json)


async def the_erd_def_should_be(
    erd: Erd, definition_json: str, data_source: DataSource
) -> None:
    """Assert that the ERD definition JSON for the given ERD is correct."""
    assert await data_source.get_erd_def(erd) == json.loads(definition_json)


class TestDataSource:
    """Hold data source tests."""

    async def test_empty_when_initialized(self, mqtt_client_mock) -> None:
        """Test data source creates empty dictionary on init."""
        data_source = DataSource(
            APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
        )
        the_device_dict_should_be_empty(data_source)

    async def test_parses_appliance_api_on_init(self, mqtt_client_mock) -> None:
        """Test data source parses the appliance API JSON on init."""
        data_source = DataSource(
            APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
        )
        the_appliance_api_should_be(APPLIANCE_API_JSON, data_source)
        the_appliance_api_erd_defs_should_be(APPLIANCE_API_DEFINTION_JSON, data_source)

    async def test_parses_status_pair_dict_on_init(self, mqtt_client_mock) -> None:
        """Test data source parses the status pair dictionary on init."""
        data_source = DataSource(
            APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
        )
        the_status_pair_dict_should_be(data_source, STATUS_PAIR_DICT)

    async def test_retrieves_status_pair_for_erd(self, mqtt_client_mock) -> None:
        """Test data source retrieves the status pair for a given ERD."""
        data_source = DataSource(
            APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
        )
        status_pair = await data_source.get_erd_status_pair(0x0006)
        assert status_pair == {
            "name": "Test",
            "request": 6,
            "status": 7,
        }
        status_pair = await data_source.get_erd_status_pair(0x0007)
        assert status_pair == {
            "name": "Test",
            "request": 6,
            "status": 7,
        }

    async def test_adds_device(self, data_source) -> None:
        """Test data source adds a device to the data."""
        await given_a_device_is_added("test", data_source)
        the_device_should_exist("test", data_source)

    async def test_adding_same_device_twice_does_nothing(self, data_source) -> None:
        """Test data source does nothing when adding the same device twice."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0001, "test", data_source)

        await when_a_device_is_added("test", data_source)
        await the_device_should_support_erd("test", 0x0001, data_source)

    async def test_raises_when_adding_erd_to_nonexistent_device(
        self, data_source
    ) -> None:
        """Test data source raises error when trying to add an ERD to a nonexistent device."""
        await adding_erd_should_raise_error("test", 0x0001, data_source)

    async def test_add_unsupported_erd(self, data_source) -> None:
        """Test data source adds unsupported ERD."""
        await given_a_device_is_added("test", data_source)
        await when_a_supported_erd_is_added(0x0001, "test", data_source)
        await the_device_should_support_erd("test", 0x0001, data_source)

    async def test_adds_supported_erd(self, data_source) -> None:
        """Test data source adds supported ERD."""
        await given_a_device_is_added("test", data_source)
        await when_an_unsupported_erd_is_added(0x0001, "test", data_source)
        await the_device_should_not_support_erd("test", 0x0001, data_source)

    async def test_writes_and_reads_from_erd(self, data_source) -> None:
        """Test data source correctly reads and writes to/from ERD."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0001, "test", data_source)
        await given_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)
        await given_an_unsupported_erd_is_added(0x0002, "test", data_source)
        await given_erd_is_set_to(0x0002, bytes.fromhex("00"), "test", data_source)

        await the_erd_should_be(0x0001, bytes.fromhex("01"), "test", data_source)
        await the_erd_should_be(0x0002, bytes.fromhex("00"), "test", data_source)

    async def test_raises_when_reading_from_nonexistent_erd(self, data_source) -> None:
        """Test data source raises error when trying to read from a nonexistent ERD."""
        await given_a_device_is_added("test", data_source)
        await reading_from_erd_should_raise_error(0x0001, "test", data_source)

    async def test_raises_when_writing_to_nonexistent_erd(self, data_source) -> None:
        """Test data source raises error when trying to write to a nonexistent ERD."""
        await given_a_device_is_added("test", data_source)
        await writing_to_erd_should_raise_error(0x0001, "test", data_source)

    async def test_transitions_erd_from_unsupported_to_supported(
        self, data_source
    ) -> None:
        """Test data source retains ERD state when moving from unsupported to supported."""
        await given_a_device_is_added("test", data_source)
        await given_an_unsupported_erd_is_added(0x0001, "test", data_source)
        await given_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)

        await when_a_supported_erd_is_added(0x0001, "test", data_source)
        await the_erd_should_be(0x0001, bytes.fromhex("01"), "test", data_source)

    async def test_transitions_erd_from_supported_to_unsupported(
        self, data_source
    ) -> None:
        """Test data source retains ERD state when moving from supported to unsupported."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0001, "test", data_source)
        await given_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)

        await when_an_unsupported_erd_is_added(0x0001, "test", data_source)
        await the_device_should_not_support_erd("test", 0x0001, data_source)
        await the_erd_should_be(0x0001, bytes.fromhex("01"), "test", data_source)

    async def test_transitions_common_api_erds_from_supported_to_unsupported(
        self, data_source
    ) -> None:
        """Test data source retains ERD states when moving all ERDs for the common appliance API from supported to unsupported."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0001, "test", data_source)
        await given_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)
        await given_a_supported_erd_is_added(0x0002, "test", data_source)
        await given_erd_is_set_to(0x0002, bytes.fromhex("01"), "test", data_source)

        await when_the_erds_are_moved_to_unsupported_for_common_api("test", data_source)
        await the_device_should_not_support_erd("test", 0x0001, data_source)
        await the_erd_should_be(0x0001, bytes.fromhex("01"), "test", data_source)
        await the_device_should_not_support_erd("test", 0x0002, data_source)
        await the_erd_should_be(0x0002, bytes.fromhex("01"), "test", data_source)

    async def test_transitions_feature_api_erds_from_supported_to_unsupported(
        self, data_source
    ) -> None:
        """Test data source retains ERD states when moving all ERDs for a feature appliance API from supported to unsupported."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0003, "test", data_source)
        await given_erd_is_set_to(0x0003, bytes.fromhex("01"), "test", data_source)
        await given_a_supported_erd_is_added(0x0004, "test", data_source)
        await given_erd_is_set_to(0x0004, bytes.fromhex("01"), "test", data_source)

        await when_the_erds_are_moved_to_unsupported_for_feature_api(
            "test", "0", data_source
        )
        await the_device_should_not_support_erd("test", 0x0003, data_source)
        await the_erd_should_be(0x0003, bytes.fromhex("01"), "test", data_source)
        await the_device_should_not_support_erd("test", 0x0004, data_source)
        await the_erd_should_be(0x0004, bytes.fromhex("01"), "test", data_source)

    async def test_does_not_move_erds_for_bad_appliance_api(self, data_source) -> None:
        """Test data source does not move any ERDs when a bad appliance API number is given."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0003, "test", data_source)
        await given_erd_is_set_to(0x0003, bytes.fromhex("01"), "test", data_source)
        await given_a_supported_erd_is_added(0x0004, "test", data_source)
        await given_erd_is_set_to(0x0004, bytes.fromhex("01"), "test", data_source)

        await when_the_erds_are_moved_to_unsupported_for_feature_api(
            "test", "2", data_source
        )
        nothing_should_happen()

        await the_device_should_support_erd("test", 0x0003, data_source)
        await the_device_should_support_erd("test", 0x0004, data_source)

    async def test_publishes_erd(self, mqtt_client_mock) -> None:
        """Test data source successfully publishes an ERD to MQTT."""
        data_source = DataSource(
            APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
        )
        await given_a_device_is_added("test", data_source)
        await when_a_supported_erd_is_added(0x0001, "test", data_source)

        await when_erd_is_published_with_value(
            0x0001, bytes.fromhex("01"), "test", data_source
        )
        mqtt_should_publish(0x0001, bytes.fromhex("01"), "test", mqtt_client_mock)
        await the_erd_should_be(0x0001, bytes.fromhex("01"), "test", data_source)

    async def test_only_publishes_supported_erd(self, mqtt_client_mock) -> None:
        """Test data source only publishes a supported ERD to MQTT."""
        data_source = DataSource(
            APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
        )
        await given_a_device_is_added("test", data_source)
        await given_an_unsupported_erd_is_added(0x0001, "test", data_source)

        await when_erd_is_published_with_value(
            0x0001, bytes.fromhex("01"), "test", data_source
        )
        mqtt_should_not_publish(mqtt_client_mock)
        await the_erd_should_be(0x0001, bytes.fromhex("01"), "test", data_source)

    async def test_raises_when_publishing_nonexistent_erd(self, data_source) -> None:
        """Test data source raises error when trying to publish a nonexistent ERD."""
        await given_a_device_is_added("test", data_source)
        await publishing_erd_should_raise_error(0x0001, "test", data_source)

    async def test_calls_subscribers(self, data_source, must_be_called_mock) -> None:
        """Test data source calls all subscribers on the subscription list."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0001, "test", data_source)
        await given_function_is_subscribed_to_erd(
            must_be_called_mock, 0x0001, "test", data_source
        )

        await when_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)

    async def test_only_calls_subscribers_for_supported_erd(self, data_source) -> None:
        """Test data source only calls subscribers for supported ERDs."""
        await given_a_device_is_added("test", data_source)
        await given_an_unsupported_erd_is_added(0x0001, "test", data_source)
        await given_function_is_subscribed_to_erd(
            fail_when_called, 0x0001, "test", data_source
        )

        await when_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)
        nothing_should_happen()

    async def test_unsubscribes(self, data_source) -> None:
        """Test data source does not call a subscriber that's been removed."""
        await given_a_device_is_added("test", data_source)
        await given_a_supported_erd_is_added(0x0001, "test", data_source)
        await given_function_is_subscribed_to_erd(
            fail_when_called, 0x0001, "test", data_source
        )
        await given_function_is_unsubscribed_from_erd(
            fail_when_called, 0x0001, "test", data_source
        )

        await when_erd_is_set_to(0x0001, bytes.fromhex("01"), "test", data_source)
        nothing_should_happen()

    async def test_get_common_appliance_api_version(self, data_source) -> None:
        """Test data source returns correct JSON for given common appliance API version."""
        await the_common_appliance_api_version_should_be(
            "1", COMMON_APPLIANCE_API_V1_JSON, data_source
        )

    async def test_get_feature_appliance_api_version(self, data_source) -> None:
        """Test data source returns correct JSON for given feature appliance API version."""
        await the_feature_appliance_api_version_should_be(
            "0", "1", FEATURE_APPLIANCE_API_1_V1_JSON, data_source
        )

    async def test_get_erd_definition(self, data_source) -> None:
        """Test data source returns correct definition JSON for given ERD."""
        await the_erd_def_should_be(0x0001, ERD_1_DEFINITION_JSON, data_source)
