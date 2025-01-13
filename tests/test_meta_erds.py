"""Test 'Meta' ERDs that provide info about other ERDs."""

from custom_components.geappliances.const import DISCOVERY, DOMAIN
from custom_components.geappliances.ha_compatibility.meta_erds import (
    enable_or_disable,
    set_allowables,
    set_max,
    set_min,
    set_unit,
)
import pytest
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .common import (
    given_integration_is_initialized,
    given_the_appliance_api_erd_defs_are,
    given_the_appliance_api_is,
    given_the_erd_is_set_to,
    mqtt_client_should_not_publish,
    when_the_erd_is_set_to,
)
from .test_data_source import the_device_should_not_support_erd
from .test_number import the_unit_should_be, when_the_number_is_set_to

from tests.test_select import when_the_select_is_set_to

APPLIANCE_API_JSON = """
{
    "common": {
        "versions": {
            "1": {
                "required": [
                    { "erd": "0x0001", "name": "Test Number", "length": 1 },
                    { "erd": "0x0002", "name": "Test Sensor", "length": 1 },
                    { "erd": "0x0003", "name": "Test Select", "length": 1 }
                ],
                "features": [
                    {
                        "mask": "0x00000001",
                        "name": "Primary",
                        "required": [
                            {"erd": "0x0004", "name": "Temp Min", "length": 1 },
                            {"erd": "0x0005", "name": "Temp Max", "length": 1 },
                            {"erd": "0x0006", "name": "Pressure Units", "length": 1 },
                            {"erd": "0x0007", "name": "Time Format", "length": 1 },
                            {"erd": "0x0008", "name": "Temp Supported", "length": 1 },
                            {"erd": "0x0009", "name": "Enum Allowables", "length": 1 }
                        ]
                    },
                    {
                        "mask": "0x00000002",
                        "name": "Reverse",
                        "required": [
                            {"erd": "0x000A", "name": "Test Reverse", "length": 1 }
                        ]
                    }
                ]
            }
        }
    },
    "featureApis": {}
}"""

APPLIANCE_API_DEFINITION_JSON = """
{
    "erds" :[
        {
            "name": "Test Number",
            "id": "0x0001",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Number",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Sensor",
            "id": "0x0002",
            "operations": ["read"],
            "data": [
                {
                    "name": "Test Sensor",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Select",
            "id": "0x0003",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Select",
                    "type": "enum",
                    "values": {
                        "0": "Zero",
                        "1": "One",
                        "255": "Max"
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Temp Min",
            "id": "0x0004",
            "operations": ["read"],
            "data": [
                {
                    "name": "Temp Min",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Temp Max",
            "id": "0x0005",
            "operations": ["read"],
            "data": [
                {
                    "name": "Temp Max",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Pressure Units",
            "id": "0x0006",
            "operations": ["read"],
            "data": [
                {
                    "name": "Pressure Units",
                    "type": "enum",
                    "values": {
                        "0": "Pa",
                        "1": "psi"
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Time Format",
            "id": "0x0007",
            "operations": ["read"],
            "data": [
                {
                    "name": "Time Format",
                    "type": "enum",
                    "values": {
                        "0": "12-hour",
                        "1": "24-hour"
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Temp Supported",
            "id": "0x0008",
            "operations": ["read"],
            "data": [
                {
                    "name": "Temp Supported",
                    "type": "bool",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Enum Allowables",
            "id": "0x0009",
            "operations": ["read"],
            "data": [
                {
                    "name": "EnumAllowables.Zero",
                    "type": "u8",
                    "bits": {
                        "offset": 0,
                        "size": 1
                    },
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "EnumAllowables.One",
                    "type": "u8",
                    "bits": {
                        "offset": 1,
                        "size": 1
                    },
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "EnumAllowables.Max",
                    "type": "u8",
                    "bits": {
                        "offset": 2,
                        "size": 1
                    },
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "EnumAllowables.Reserved",
                    "type": "u8",
                    "bits": {
                        "offset": 3,
                        "size": 5
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Reverse",
            "id": "0x000a",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Reverse",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        }
    ]
}"""

META_TABLE = {
    0x0004: {"Temp Min": (["number.test_number", "number.test_reverse"], set_min)},
    0x0005: {"Temp Max": (["number.test_number"], set_max)},
    0x0006: {"Pressure Units": (["number.test_number"], set_unit)},
    0x0008: {"Temp Supported": (["number.test_number"], enable_or_disable)},
    0x0009: {
        "EnumAllowables.Zero": (["select.test_select.Zero"], set_allowables),
        "EnumAllowables.One": (["select.test_select.One"], set_allowables),
        "EnumAllowables.Max": (["select.test_select.Max"], set_allowables),
    },
}


@pytest.fixture(autouse=True)
async def initialize(hass: HomeAssistant, mqtt_mock: MqttMockHAClient) -> None:
    """Set up for all tests."""
    await given_integration_is_initialized(hass, mqtt_mock)
    given_the_appliance_api_is(APPLIANCE_API_JSON, hass)
    given_the_appliance_api_erd_defs_are(APPLIANCE_API_DEFINITION_JSON, hass)
    given_the_meta_erds_are_set_to(hass, META_TABLE)
    await given_the_erd_is_set_to(0x0092, "0000 0001 0000 0001", hass)
    mqtt_mock.reset_mock()


def given_the_meta_erds_are_set_to(hass: HomeAssistant, table: dict) -> None:
    """Set the meta ERDs to the given table."""
    coordinator = hass.data[DOMAIN][DISCOVERY]._meta_erd_coordinator
    coordinator._transform_table = table
    coordinator._create_entities_to_meta_erds_dict()


async def setting_the_number_should_raise_error(
    name: str, value: float, hass: HomeAssistant
) -> None:
    """Assert that attempting to set the number's value raises an error."""
    with pytest.raises(ServiceValidationError):
        await when_the_number_is_set_to(name, value, hass)


def the_entity_value_should_be(name: str, state: str, hass: HomeAssistant) -> None:
    """Assert the value of the entity."""
    if (entity := hass.states.get(name)) is not None:
        assert entity.state == state
    else:
        pytest.fail(f"Could not find entity {name}")


async def setting_the_select_should_raise_error(
    name: str, option: str, hass: HomeAssistant
) -> None:
    """Assert that attempting to set the select's value raises an error."""
    with pytest.raises(ServiceValidationError):
        await when_the_select_is_set_to(name, option, hass)


class TestMetaErds:
    """Hold the meta ERD tests."""

    async def test_number_min_is_set_by_erd(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test the ERD is not published when attempting to write a value below the min."""
        await given_the_erd_is_set_to(0x0001, "00", hass)
        await given_the_erd_is_set_to(0x0004, "F0", hass)

        await setting_the_number_should_raise_error("number.test_number", 1.0, hass)
        mqtt_client_should_not_publish(mqtt_mock)
        the_entity_value_should_be("number.test_number", "0", hass)

    async def test_number_max_is_set_by_erd(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test the ERD is not published when attempting to write a value above the max."""
        await given_the_erd_is_set_to(0x0001, "00", hass)
        await given_the_erd_is_set_to(0x0005, "08", hass)

        await setting_the_number_should_raise_error("number.test_number", 10.0, hass)
        mqtt_client_should_not_publish(mqtt_mock)
        the_entity_value_should_be("number.test_number", "0", hass)

    async def test_number_units_are_set_by_erd(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test the number unit is set by the associated ERD."""
        await given_the_erd_is_set_to(0x0001, "00", hass)
        await given_the_erd_is_set_to(0x0006, "01", hass)

        the_unit_should_be("number.test_number", "psi", hass)

    async def test_entity_is_disabled_by_erd(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test the entity is disabled by the associated ERD."""
        await given_the_erd_is_set_to(0x0001, "00", hass)
        await given_the_erd_is_set_to(0x0008, "00", hass)

        await the_device_should_not_support_erd(
            "test", 0x0001, hass.data[DOMAIN][DISCOVERY]._data_source
        )
        the_entity_value_should_be("number.test_number", STATE_UNKNOWN, hass)

    async def test_allowables_are_set_by_erd(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test the allowables are set by the associated ERD."""
        await given_the_erd_is_set_to(0x0003, "00", hass)
        await given_the_erd_is_set_to(0x0009, "80", hass)

        await setting_the_select_should_raise_error("select.test_select", "One", hass)
        mqtt_client_should_not_publish(mqtt_mock)
        the_entity_value_should_be("select.test_select", "Zero", hass)

    async def test_applies_changes_when_meta_erd_is_first(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test the options set by the meta ERD is still applied if Home Assistant learns about the target ERD afterwards."""
        await given_the_erd_is_set_to(0x0004, "F0", hass)
        await when_the_erd_is_set_to(0x0092, "0000 0001 0000 0002", hass)

        await setting_the_number_should_raise_error("number.test_reverse", 1.0, hass)
        mqtt_client_should_not_publish(mqtt_mock)
        the_entity_value_should_be("number.test_reverse", STATE_UNKNOWN, hass)
