"""Test GE Appliances time."""

from datetime import time

from custom_components.geappliances.const import CONF_DEVICE_ID
from custom_components.geappliances.ha_compatibility.data_source import DataSource
from custom_components.geappliances.models import GeaTimeConfig
import pytest
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from homeassistant.components import time as time_platform
from homeassistant.components.time.const import SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TIME, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .common import (
    given_integration_is_initialized,
    given_the_appliance_api_erd_defs_are,
    given_the_appliance_api_is,
    given_the_special_erd_map_is,
    when_the_erd_is_set_to,
)

pytestmark = pytest.mark.parametrize("expected_lingering_timers", [True])

APPLIANCE_API_JSON = """
{
    "common": {
        "versions": {
            "1": {
                "required": [
                    { "erd": "0x0001", "name": "Time Test", "length": 3 }
                ],
                "features": [
                    {
                        "mask": "0x00000001",
                        "name": "Primary",
                        "required": [
                            { "erd": "0x0002", "name": "Read Only Test", "length": 3 }
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
                        { "erd": "0x0003", "name": "Removal Test", "length": 3 }
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
            "name": "Time Test",
            "id": "0x0001",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Hours",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Minutes",
                    "type": "u8",
                    "offset": 1,
                    "size": 1
                },
                {
                    "name": "Seconds",
                    "type": "u8",
                    "offset": 2,
                    "size": 1
                }
            ]
        },
        {
            "name": "Read Only Test",
            "id": "0x0002",
            "operations": ["read"],
            "data": [
                {
                    "name": "Hours",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Minutes",
                    "type": "u8",
                    "offset": 1,
                    "size": 1
                },
                {
                    "name": "Seconds",
                    "type": "u8",
                    "offset": 2,
                    "size": 1
                }
            ]
        },
        {
            "name": "Removal Test",
            "id": "0x0003",
            "operations": ["read"],
            "data": [
                {
                    "name": "Hours",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Minutes",
                    "type": "u8",
                    "offset": 1,
                    "size": 1
                },
                {
                    "name": "Seconds",
                    "type": "u8",
                    "offset": 2,
                    "size": 1
                }
            ]
        }
    ]
}"""


async def build_time_test_config(
    device_name: str, data_source: DataSource
) -> list[GeaTimeConfig]:
    """Build config for time test."""
    return [
        GeaTimeConfig(
            f"{device_name}_0001_Test_Time",
            (await data_source.get_device(device_name))[CONF_DEVICE_ID],
            device_name,
            "Time Test: Time Test",
            "time",
            data_source,
            0x0001,
            None,
            0,
            3,
            False,
        )
    ]


async def build_read_only_time_test_config(
    device_name: str, data_source: DataSource
) -> list[GeaTimeConfig]:
    """Build config for read-only time test."""
    return [
        GeaTimeConfig(
            f"{device_name}_0002_Read_Only_Test",
            (await data_source.get_device(device_name))[CONF_DEVICE_ID],
            device_name,
            "Read Only Test: Read Only Test",
            "time",
            data_source,
            0x0002,
            None,
            0,
            3,
            True,
        )
    ]


async def build_time_removal_test_config(
    device_name: str, data_source: DataSource
) -> list[GeaTimeConfig]:
    """Build config for time test."""
    return [
        GeaTimeConfig(
            f"{device_name}_0003_Removal_Test",
            (await data_source.get_device(device_name))[CONF_DEVICE_ID],
            device_name,
            "Removal Test: Removal Test",
            "time",
            data_source,
            0x0003,
            None,
            0,
            3,
            False,
        )
    ]


_SPECIAL_ERDS = {
    0x0001: build_time_test_config,
    0x0002: build_read_only_time_test_config,
    0x0003: build_time_removal_test_config,
}


@pytest.fixture(autouse=True)
async def initialize(hass: HomeAssistant, mqtt_mock: MqttMockHAClient) -> None:
    """Set up for all tests."""
    await given_integration_is_initialized(hass, mqtt_mock)
    given_the_appliance_api_is(APPLIANCE_API_JSON, hass)
    given_the_appliance_api_erd_defs_are(APPLIANCE_API_DEFINTION_JSON, hass)
    given_the_special_erd_map_is(_SPECIAL_ERDS, hass)
    await when_the_erd_is_set_to(0x0092, "0000 0001 0000 0001", hass)
    await when_the_erd_is_set_to(0x0093, "0000 0001 0000 0000", hass)


async def when_the_time_is_set_to(name: str, value: time, hass: HomeAssistant) -> None:
    """Set the time value."""
    data = {ATTR_ENTITY_ID: name, ATTR_TIME: value}
    await hass.services.async_call(
        time_platform.DOMAIN, SERVICE_SET_VALUE, data, blocking=True
    )


def the_time_value_should_be(name: str, state: str, hass: HomeAssistant) -> None:
    """Assert the value of the time input."""
    if (entity := hass.states.get(name)) is not None:
        assert entity.state == state
    else:
        pytest.fail(f"Could not find time {name}")


class TestTime:
    """Hold time input tests."""

    async def test_updates_state(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test time input updates state."""
        await when_the_erd_is_set_to(0x0001, "000000", hass)
        the_time_value_should_be("time.time_test_time_test", "00:00:00", hass)

        await when_the_erd_is_set_to(0x0001, "010101", hass)
        the_time_value_should_be("time.time_test_time_test", "01:01:01", hass)

    async def test_sets_erd(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test time input updates ERD."""
        await when_the_erd_is_set_to(0x0001, "000000", hass)
        the_time_value_should_be("time.time_test_time_test", "00:00:00", hass)

        await when_the_time_is_set_to("time.time_test_time_test", time(1, 1, 1), hass)
        the_time_value_should_be("time.time_test_time_test", "01:01:01", hass)

    async def test_read_only(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test read-only time inputs do not update from user input."""
        await when_the_erd_is_set_to(0x0002, "000000", hass)
        the_time_value_should_be("time.read_only_test_read_only_test", "00:00:00", hass)

        await when_the_time_is_set_to(
            "time.read_only_test_read_only_test", time(1, 1, 1), hass
        )
        the_time_value_should_be("time.read_only_test_read_only_test", "00:00:00", hass)

    async def test_shows_unknown_when_unsupported(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test time shows STATE_UNKNOWN when the associated ERD is no longer supported."""
        await when_the_erd_is_set_to(0x0003, "000000", hass)
        await when_the_erd_is_set_to(0x0093, "0000 0001 0000 0000", hass)
        the_time_value_should_be("time.removal_test_removal_test", STATE_UNKNOWN, hass)
