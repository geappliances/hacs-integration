"""Test GE Appliances select."""

import pytest
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from homeassistant.components import select
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .common import (
    given_integration_is_initialized,
    given_the_appliance_api_erd_defs_are,
    given_the_appliance_api_is,
    given_the_status_pair_dict_is,
    the_mqtt_topic_value_should_be,
    when_the_erd_is_set_to,
)

pytestmark = pytest.mark.parametrize("expected_lingering_timers", [True])

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
                            {"erd": "0x0004", "name": "Removal Test", "length": 1 }
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
                        { "erd": "0x0002", "name": "Multi Field Test", "length": 2 },
                        { "erd": "0x0003", "name": "Bigger Enum Test", "length": 2 },
                        { "erd": "0x0005", "name": "Test Pair Status", "length": 1 },
                        { "erd": "0x0006", "name": "Test Pair Request", "length": 1 }
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
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test",
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
            "name": "Multi Field Test",
            "id": "0x0002",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Field One",
                    "type": "enum",
                    "offset": 0,
                    "values": {
                        "0": "Zero",
                        "1": "One",
                        "255": "Max One"
                    },
                    "size": 1
                },
                {
                    "name": "Field Two",
                    "type": "enum",
                    "values": {
                        "0": "Zero",
                        "1": "One",
                        "255": "Max Two"
                    },
                    "offset": 1,
                    "size": 1
                }
            ]
        },
        {
            "name": "Bigger Enum Test",
            "id": "0x0003",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Enum",
                    "type": "enum",
                    "values": {
                        "0": "Zero",
                        "1": "One",
                        "65535": "Max"
                    },
                    "offset": 0,
                    "size": 2
                }
            ]
        },
        {
            "name": "Removal Test",
            "id": "0x0004",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Removal Test",
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
            "name": "Test Pair Status",
            "id": "0x0005",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Select",
                    "type": "enum",
                    "values": {
                        "0": "Off",
                        "1": "On"
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Pair Request",
            "id": "0x0006",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Select",
                    "type": "enum",
                    "values": {
                        "0": "Off",
                        "1": "On"
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        }
    ]
}"""

STATUS_PAIR_DICT = """
{
    "0x0005": {
        "name": "Test Pair",
        "status": 5,
        "request": 6
    },
    "0x0006": {
        "name": "Test Pair",
        "status": 5,
        "request": 6
    }
}
"""


@pytest.fixture(autouse=True)
async def initialize(hass: HomeAssistant, mqtt_mock: MqttMockHAClient) -> None:
    """Set up for all tests."""
    await given_integration_is_initialized(hass, mqtt_mock)
    given_the_appliance_api_is(APPLIANCE_API_JSON, hass)
    given_the_appliance_api_erd_defs_are(APPLIANCE_API_DEFINTION_JSON, hass)
    given_the_status_pair_dict_is(STATUS_PAIR_DICT, hass)
    await when_the_erd_is_set_to(0x0092, "0000 0001 0000 0001", hass)
    await when_the_erd_is_set_to(0x0093, "0000 0001 0000 0000", hass)


async def when_the_select_is_set_to(
    name: str, option: str, hass: HomeAssistant
) -> None:
    """Set the select value."""
    data = {ATTR_ENTITY_ID: name, select.ATTR_OPTION: option}
    await hass.services.async_call(
        select.DOMAIN, select.SERVICE_SELECT_OPTION, data, blocking=True
    )


def the_select_value_should_be(name: str, state: str, hass: HomeAssistant) -> None:
    """Assert the value of the select."""
    if (entity := hass.states.get(name)) is not None:
        assert entity.state == state
    else:
        pytest.fail(f"Could not find select {name}")


class TestSelect:
    """Hold select tests."""

    async def test_updates_state(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test select updates state."""
        await when_the_erd_is_set_to(0x0001, "00", hass)
        the_select_value_should_be("select.test_test", "Zero", hass)

        await when_the_erd_is_set_to(0x0001, "01", hass)
        the_select_value_should_be("select.test_test", "One", hass)

    async def test_gets_correct_byte(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test select only updates based on the associated byte."""
        await when_the_erd_is_set_to(0x0002, "FF00", hass)
        the_select_value_should_be("select.multi_field_test_field_one", "Max One", hass)
        the_select_value_should_be("select.multi_field_test_field_two", "Zero", hass)

        await when_the_erd_is_set_to(0x0002, "01FF", hass)
        the_select_value_should_be("select.multi_field_test_field_one", "One", hass)
        the_select_value_should_be("select.multi_field_test_field_two", "Max Two", hass)

    async def test_sets_correct_byte(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test select only updates the associated byte."""
        await when_the_erd_is_set_to(0x0002, "0000", hass)
        await when_the_select_is_set_to(
            "select.multi_field_test_field_one", "Max One", hass
        )
        the_mqtt_topic_value_should_be(0x0002, "FF00", mqtt_mock)
        the_select_value_should_be("select.multi_field_test_field_one", "Max One", hass)
        the_select_value_should_be("select.multi_field_test_field_two", "Zero", hass)

        await when_the_select_is_set_to(
            "select.multi_field_test_field_two", "One", hass
        )
        the_mqtt_topic_value_should_be(0x0002, "FF01", mqtt_mock)
        the_select_value_should_be("select.multi_field_test_field_one", "Max One", hass)
        the_select_value_should_be("select.multi_field_test_field_two", "One", hass)

    async def test_bigger_enum(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test select sets and displays multi-byte enums correctly."""
        await when_the_erd_is_set_to(0x0003, "0000", hass)
        the_select_value_should_be("select.bigger_enum_test_enum", "Zero", hass)

        await when_the_erd_is_set_to(0x0003, "0001", hass)
        the_select_value_should_be("select.bigger_enum_test_enum", "One", hass)

        await when_the_select_is_set_to("select.bigger_enum_test_enum", "Max", hass)
        the_mqtt_topic_value_should_be(0x0003, "FFFF", mqtt_mock)
        the_select_value_should_be("select.bigger_enum_test_enum", "Max", hass)

    async def test_shows_unknown_when_unsupported(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test select shows STATE_UNKNOWN when the associated ERD is no longer supported."""
        await when_the_erd_is_set_to(0x0092, "0000 0001 0000 0000", hass)
        the_select_value_should_be(
            "select.removal_test_removal_test", STATE_UNKNOWN, hass
        )

    async def test_publishes_to_request_erd_and_does_not_update_paired_select(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test paired select, when set, updates the request ERD, but not the status ERD or select itself."""
        await when_the_erd_is_set_to(0x0005, "00", hass)
        await when_the_erd_is_set_to(0x0006, "00", hass)
        the_select_value_should_be("select.test_pair_test_select", "Off", hass)

        await when_the_select_is_set_to("select.test_pair_test_select", "On", hass)
        the_mqtt_topic_value_should_be(0x0006, "01", mqtt_mock)
        the_select_value_should_be("select.test_pair_test_select", "Off", hass)

        await when_the_select_is_set_to("select.test_pair_test_select", "Off", hass)
        the_mqtt_topic_value_should_be(0x0006, "00", mqtt_mock)
        the_select_value_should_be("select.test_pair_test_select", "Off", hass)

    async def test_status_erd_updates_paired_select(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test select updates paired select on status ERD update."""
        await when_the_erd_is_set_to(0x0005, "00", hass)
        await when_the_erd_is_set_to(0x0006, "00", hass)
        the_select_value_should_be("select.test_pair_test_select", "Off", hass)

        await when_the_erd_is_set_to(0x0005, "01", hass)
        the_select_value_should_be("select.test_pair_test_select", "On", hass)
