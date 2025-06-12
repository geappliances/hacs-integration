"""Tests for GE Appliances ERD factory."""

import logging
from unittest.mock import MagicMock

from numpy import empty

from custom_components.geappliances.const import Erd
from custom_components.geappliances.erd_factory import ERDFactory
from custom_components.geappliances.ha_compatibility.data_source import DataSource
from custom_components.geappliances.ha_compatibility.meta_erds import MetaErdCoordinator
from custom_components.geappliances.ha_compatibility.mqtt_client import GeaMQTTClient
from custom_components.geappliances.ha_compatibility.registry_updater import (
    RegistryUpdater,
)
from custom_components.geappliances.models import (
    GeaBinarySensorConfig,
    GeaEntityConfig,
    GeaSwitchConfig,
)
import pytest

from homeassistant.const import Platform

from .doubles import MetaErdCoordinatorMock, MqttClientMock, RegistryUpdaterMock

DEVICE_NAME = "test"
APPLIANCE_API_JSON = """
{
    "common": {
        "versions": {
            "1": {
                "required": [
                    { "erd": "0x0001", "name": "Test", "length": 1 },
                    {"erd": "0x0002", "name": "Another Test", "length": 1 }
                ],
                "features": [
                    {
                        "mask": "0x00000001",
                        "name": "Primary",
                        "required": [
                            {"erd": "0x0003", "name": "Yet Another Test", "length": 1 }
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
                        { "erd": "0x0004", "name": "Multi Field Test", "length": 2 },
                        { "erd": "0x0005", "name": "Test Pair Request", "length": 1 },
                        { "erd": "0x0006", "name": "Test Pair Status", "length": 1 }
                    ],
                    "features": []
                }
            }
        }
    }
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
            "name": "Yet Another Test",
            "id": "0x0003",
            "operations": ["read"],
            "data": [
                {
                    "name": "Yet Another Test",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Multi Field Test",
            "id": "0x0004",
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
            "name": "Test Pair Request",
            "id": "0x0005",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Switch",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Pair Status",
            "id": "0x0006",
            "operations": ["read"],
            "data": [
                {
                    "name": "Test Switch",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        }
    ]
}"""


@pytest.fixture
def mqtt_client_mock() -> MqttClientMock:
    """Return a mock instance of GeaMQTTClient."""
    return MagicMock(GeaMQTTClient)


@pytest.fixture
def data_source(mqtt_client_mock) -> DataSource:
    """Create a data source using the module's appliance API."""
    return DataSource(
        APPLIANCE_API_JSON, APPLIANCE_API_DEFINTION_JSON, mqtt_client_mock
    )


@pytest.fixture
def registry_updater_mock() -> RegistryUpdaterMock:
    """Return a mock instance of RegistryUpdater."""
    return MagicMock(RegistryUpdater)


@pytest.fixture
def meta_erd_coordinator_mock() -> MetaErdCoordinatorMock:
    """Return a mock instance of RegistryUpdater."""
    return MagicMock(MetaErdCoordinator)


@pytest.fixture(autouse=True)
async def initialize(data_source) -> None:
    """Set up device for tests."""
    await data_source.add_device(DEVICE_NAME, "test_id")


@pytest.fixture(autouse=True)
def erd_factory(
    data_source, registry_updater_mock, meta_erd_coordinator_mock
) -> ERDFactory:
    """Create the ERDFactory to be tested."""
    return ERDFactory(registry_updater_mock, data_source, meta_erd_coordinator_mock)


@pytest.fixture
def capture_errors(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Capture all logged errors in a test."""
    caplog.set_level(logging.ERROR)
    return caplog


async def when_configs_are_created_for_erd(
    erd: Erd, erd_factory: ERDFactory
) -> list[GeaEntityConfig]:
    """Create the configs for the specified erd."""
    return await erd_factory.get_entity_configs(erd, DEVICE_NAME)


async def when_configs_are_created_for_appliance_api(
    data_source: DataSource,
    erd_factory: ERDFactory,
) -> None:
    """Create the configs for the common appliance API."""
    if (
        erd_list := await data_source.get_common_appliance_api_version("1")
    ) is not None:
        erd_list = erd_list["required"]
        await erd_factory.set_up_erds(erd_list, DEVICE_NAME)


def get_configs_for_erd(
    erd: Erd, data_source: DataSource
) -> list[GeaBinarySensorConfig]:
    """Return the correct config for the given ERD."""
    configs = [
        [],  # Skip one since we don't have an ERD 0
        [
            GeaBinarySensorConfig(
                "test_0001_Test",
                "test_id",
                DEVICE_NAME,
                "Test: Test",
                Platform.BINARY_SENSOR,
                data_source,
                0x0001,
                None,
                0,
                1,
                0xFF,
            )
        ],
        [
            GeaBinarySensorConfig(
                "test_0002_Another_Test",
                "test_id",
                DEVICE_NAME,
                "Another Test: Another Test",
                Platform.BINARY_SENSOR,
                data_source,
                0x0002,
                None,
                0,
                1,
                0xFF,
            )
        ],
        [
            GeaBinarySensorConfig(
                "test_0003_Yet_Another_Test",
                "test_id",
                DEVICE_NAME,
                "Yet Another Test: Yet Another Test",
                Platform.BINARY_SENSOR,
                data_source,
                0x0003,
                None,
                0,
                1,
                0xFF,
            )
        ],
        [
            GeaBinarySensorConfig(
                "test_0004_Field_One",
                "test_id",
                DEVICE_NAME,
                "Multi Field Test: Field One",
                Platform.BINARY_SENSOR,
                data_source,
                0x0004,
                None,
                0,
                1,
                0xFF,
            ),
            GeaBinarySensorConfig(
                "test_0004_Field_Two",
                "test_id",
                DEVICE_NAME,
                "Multi Field Test: Field Two",
                Platform.BINARY_SENSOR,
                data_source,
                0x0004,
                None,
                1,
                1,
                0xFF,
            ),
        ],
        [
            GeaSwitchConfig(
                "test_0005_Test_Switch",
                "test_id",
                DEVICE_NAME,
                "Test Pair: Test Switch",
                Platform.SWITCH,
                data_source,
                0x0005,
                0x0006,
                0,
                1,
                0xFF,
            )
        ],
        [],  # Should be empty since 0x0006 is a status ERD
    ]

    return configs[erd]


async def the_configs_should_be_correct_for_erd(
    erd: Erd, config_list: list[GeaEntityConfig], data_source: DataSource
) -> None:
    """Assert that the created config list matches the expected list."""
    expected_list = get_configs_for_erd(erd, data_source)
    assert config_list == expected_list


async def the_configs_should_be_correct_for_appliance_api(
    registry_updater_mock: RegistryUpdaterMock, data_source: DataSource
) -> None:
    """Assert that the created config list matches the expected list."""
    if (
        erd_list := await data_source.get_common_appliance_api_version("1")
    ) is not None:
        erd_list = [int(erd["erd"], base=16) for erd in erd_list["required"]]

        expected_lists = [get_configs_for_erd(erd, data_source) for erd in erd_list]

        for config_list in expected_lists:
            for config in config_list:
                registry_updater_mock.add_entity_to_device.assert_any_call(
                    config, DEVICE_NAME
                )


def the_error_log_should_be(msg: str, caplog: pytest.LogCaptureFixture) -> None:
    """Assert that the given message is the only logged error."""
    assert caplog.record_tuples == [
        (
            "custom_components.geappliances.erd_factory",
            logging.ERROR,
            msg,
        )
    ]


class TestERDFactory:
    """Hold ERD factory tests."""

    async def test_creates_config_for_erd_with_single_field(
        self, data_source, erd_factory
    ) -> None:
        """Test factory correctly creates config for an ERD with one field."""

        config_list = await when_configs_are_created_for_erd(0x0003, erd_factory)
        await the_configs_should_be_correct_for_erd(0x0003, config_list, data_source)

    async def test_creates_config_for_erd_with_multiple_fields(
        self, data_source, erd_factory
    ) -> None:
        """Test factory correctly creates config for an ERD with multiple fields."""

        config_list = await when_configs_are_created_for_erd(0x0004, erd_factory)
        await the_configs_should_be_correct_for_erd(0x0004, config_list, data_source)

    async def test_creates_configs_for_appliance_api(
        self, data_source, registry_updater_mock, erd_factory
    ) -> None:
        """Test factory correctly creates configs for a list of ERDs in the appliance API."""

        await when_configs_are_created_for_appliance_api(data_source, erd_factory)
        await the_configs_should_be_correct_for_appliance_api(
            registry_updater_mock, data_source
        )

    async def test_logs_error_for_bad_erd(self, erd_factory, capture_errors) -> None:
        """Test factory logs an error when attempting to create configs for a non-existent ERD."""

        await when_configs_are_created_for_erd(0x0010, erd_factory)
        the_error_log_should_be("Could not find ERD 0x0010", capture_errors)

    async def test_creates_config_for_paired_erd(
        self, data_source, erd_factory
    ) -> None:
        """Test factory correctly creates config for a paired ERD."""

        config_list = await when_configs_are_created_for_erd(0x0005, erd_factory)
        empty_list = await when_configs_are_created_for_erd(0x0006, erd_factory)
        await the_configs_should_be_correct_for_erd(0x0005, config_list, data_source)
        await the_configs_should_be_correct_for_erd(0x0006, empty_list, data_source)
