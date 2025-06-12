"""Test GE Appliances number."""

import pytest
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from homeassistant.components import number
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number.const import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import METRIC_SYSTEM

from .common import (
    given_integration_is_initialized,
    given_the_appliance_api_erd_defs_are,
    given_the_appliance_api_is,
    given_the_erd_is_set_to,
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
                        { "erd": "0x0003", "name": "Temperature Test", "length": 2 },
                        { "erd": "0x0005", "name": "Celsius Test", "length": 2 },
                        { "erd": "0x0006", "name": "Battery Test", "length": 1 },
                        { "erd": "0x0007", "name": "Energy Test", "length": 1 },
                        { "erd": "0x0008", "name": "Humidity Test", "length": 1 },
                        { "erd": "0x0009", "name": "Pressure Test", "length": 1 },
                        { "erd": "0x000a", "name": "Bitfield Test", "length": 1 },
                        { "erd": "0x0010", "name": "Gallons Test", "length": 1 },
                        { "erd": "0x0011", "name": "Fluid Ounces Test", "length": 1 },
                        { "erd": "0x0012", "name": "Pounds Test", "length": 1 },
                        { "erd": "0x0013", "name": "Current Test", "length": 1 },
                        { "erd": "0x0014", "name": "Seconds Test", "length": 1 },
                        { "erd": "0x0015", "name": "Minutes Test", "length": 1 },
                        { "erd": "0x0016", "name": "Hours Test", "length": 1 },
                        { "erd": "0x0017", "name": "Days Test", "length": 1 },
                        { "erd": "0x0018", "name": "Power Test", "length": 1 },
                        { "erd": "0x0019", "name": "Voltage Test", "length": 1 },
                        { "erd": "0x0020", "name": "Frequency Test", "length": 1 },
                        { "erd": "0x0021", "name": "Scale Factor Test", "length": 8 },
                        { "erd": "0x0022", "name": "Scale Factor Description Test", "length": 1 },
                        { "erd": "0x00023", "name": "Test Pair Status", "length": 1 },
                        { "erd": "0x00024", "name": "Test Pair Request", "length": 1 }
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
                    "type": "u8",
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
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Field Two",
                    "type": "u8",
                    "offset": 1,
                    "size": 1
                }
            ]
        },
        {
            "name": "Temperature Test",
            "id": "0x0003",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Temperature Test",
                    "type": "i16",
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
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Celsius Test",
            "id": "0x0005",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Temperature (C) Test",
                    "type": "i16",
                    "offset": 0,
                    "size": 2
                }
            ]
        },
        {
            "name": "Battery Test",
            "id": "0x0006",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Battery Level",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Energy Test",
            "id": "0x0007",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Energy (kWh)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Humidity Test",
            "id": "0x0008",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Humidity Test",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Pressure Test",
            "id": "0x0009",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Pressure (in Pa)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Bitfield Test",
            "id": "0x000a",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Field One",
                    "type": "u8",
                    "bits": {
                        "offset": 0,
                        "size": 4
                    },
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Field Two",
                    "type": "u8",
                    "bits": {
                        "offset": 4,
                        "size": 4
                    },
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Gallons Test",
            "id": "0x0010",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "gallons Test",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Fluid Ounces Test",
            "id": "0x0011",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Fluid Ounces (oz)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Pounds Test",
            "id": "0x0012",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Pounds (lbs)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Current Test",
            "id": "0x0013",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Current (mA)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Seconds Test",
            "id": "0x0014",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Duration (seconds)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Minutes Test",
            "id": "0x0015",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Duration (minutes)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Hours Test",
            "id": "0x0016",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Duration (hours)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Days Test",
            "id": "0x0017",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Duration (days)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Power Test",
            "id": "0x0018",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Power (Watts)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Voltage Test",
            "id": "0x0019",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Voltage Test",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Frequency Test",
            "id": "0x0020",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Frequency (Hz)",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Scale Factor Test",
            "id": "0x0021",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Field 1 x10",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                },
                {
                    "name": "Field 2 x 10",
                    "type": "u8",
                    "offset": 1,
                    "size": 1
                },
                {
                    "name": "Field 3 x100",
                    "type": "u8",
                    "offset": 2,
                    "size": 1
                },
                {
                    "name": "Field 4 x 100",
                    "type": "u8",
                    "offset": 3,
                    "size": 1
                },
                {
                    "name": "Field 5 x1000",
                    "type": "u16",
                    "offset": 4,
                    "size": 2
                },
                {
                    "name": "Field 6 x 1000",
                    "type": "u16",
                    "offset": 6,
                    "size": 2
                }
            ]
        },
        {
            "name": "Scale Factor Description Test",
            "id": "0x0022",
            "operations": ["read", "write"],
            "description": "Test ERD with x 10 scale factor",
            "data": [
                {
                    "name": "Scaled By 10",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        },
        {
            "name": "Test Pair Status",
            "id": "0x0023",
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
            "name": "Test Pair Request",
            "id": "0x0024",
            "operations": ["read", "write"],
            "data": [
                {
                    "name": "Test Number",
                    "type": "u8",
                    "offset": 0,
                    "size": 1
                }
            ]
        }
    ]
}"""

STATUS_PAIR_DICT = """
{
    "0x0023": {
        "name": "Test Pair",
        "status": 35,
        "request": 36
    },
    "0x0024": {
        "name": "Test Pair",
        "status": 35,
        "request": 36
    }
}
"""


@pytest.fixture(autouse=True)
async def initialize(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, request: pytest.FixtureRequest
) -> None:
    """Set up for all tests."""
    if "metric" in request.keywords:
        await given_integration_is_initialized(hass, mqtt_mock, METRIC_SYSTEM)
    else:
        await given_integration_is_initialized(hass, mqtt_mock)
    given_the_appliance_api_is(APPLIANCE_API_JSON, hass)
    given_the_appliance_api_erd_defs_are(APPLIANCE_API_DEFINTION_JSON, hass)
    given_the_status_pair_dict_is(STATUS_PAIR_DICT, hass)
    await given_the_erd_is_set_to(0x0092, "0000 0001 0000 0001", hass)
    await given_the_erd_is_set_to(0x0093, "0000 0001 0000 0000", hass)


async def when_the_number_is_set_to(
    name: str, value: float, hass: HomeAssistant
) -> None:
    """Set the number value."""
    data = {ATTR_ENTITY_ID: name, ATTR_VALUE: value}
    await hass.services.async_call(
        number.DOMAIN, SERVICE_SET_VALUE, data, blocking=True
    )


def the_number_value_should_be(name: str, state: str, hass: HomeAssistant) -> None:
    """Assert the value of the number."""
    if (entity := hass.states.get(name)) is not None:
        assert entity.state == state
    else:
        pytest.fail(f"Could not find number {name}")


class TestNumber:
    """Hold number tests."""

    async def test_updates_state(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number updates state."""
        await when_the_erd_is_set_to(0x0001, "00", hass)
        the_number_value_should_be("number.test_test", "0", hass)

        await when_the_erd_is_set_to(0x0001, "01", hass)
        the_number_value_should_be("number.test_test", "1", hass)

    async def test_gets_correct_byte(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number only updates based on the associated byte."""
        await when_the_erd_is_set_to(0x0002, "FF00", hass)
        the_number_value_should_be("number.multi_field_test_field_one", "255", hass)
        the_number_value_should_be("number.multi_field_test_field_two", "0", hass)

        await when_the_erd_is_set_to(0x0002, "010F", hass)
        the_number_value_should_be("number.multi_field_test_field_one", "1", hass)
        the_number_value_should_be("number.multi_field_test_field_two", "15", hass)

    async def test_sets_correct_byte(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number only updates the associated byte."""
        await given_the_erd_is_set_to(0x0002, "0000", hass)
        await when_the_number_is_set_to(
            "number.multi_field_test_field_one", 255.0, hass
        )
        the_mqtt_topic_value_should_be(0x0002, "FF00", mqtt_mock)
        the_number_value_should_be("number.multi_field_test_field_one", "255", hass)
        the_number_value_should_be("number.multi_field_test_field_two", "0", hass)

        await when_the_number_is_set_to(
            "number.multi_field_test_field_two", 100.0, hass
        )
        the_number_value_should_be("number.multi_field_test_field_one", "255", hass)
        the_number_value_should_be("number.multi_field_test_field_two", "100", hass)

    async def test_reads_from_bitfields(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number retrieves values from bitfields correctly."""
        await when_the_erd_is_set_to(0x000A, "F0", hass)
        the_number_value_should_be("number.bitfield_test_field_one", "15", hass)
        the_number_value_should_be("number.bitfield_test_field_two", "0", hass)

        await when_the_erd_is_set_to(0x000A, "0F", hass)
        the_number_value_should_be("number.bitfield_test_field_one", "0", hass)
        the_number_value_should_be("number.bitfield_test_field_two", "15", hass)

    async def test_writes_to_bitfields(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number writes values to bitfields correctly."""
        await given_the_erd_is_set_to(0x000A, "00", hass)

        await when_the_number_is_set_to("number.bitfield_test_field_one", 15, hass)
        the_number_value_should_be("number.bitfield_test_field_one", "15", hass)
        the_number_value_should_be("number.bitfield_test_field_two", "0", hass)

        await when_the_number_is_set_to("number.bitfield_test_field_two", 7, hass)
        the_number_value_should_be("number.bitfield_test_field_one", "15", hass)
        the_number_value_should_be("number.bitfield_test_field_two", "7", hass)

    async def test_shows_unknown_when_unsupported(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number shows STATE_UNKNOWN when the associated ERD is no longer supported."""
        await when_the_erd_is_set_to(0x0092, "0000 0001 0000 0000", hass)
        the_number_value_should_be(
            "number.removal_test_removal_test", STATE_UNKNOWN, hass
        )

    async def test_reads_correct_scaled_value(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number shows the correct scaled value."""
        """64 -> 100, 07D0 -> 2000"""
        await when_the_erd_is_set_to(0x0021, "64 64 64 64 07D0 07D0", hass)

        the_number_value_should_be("number.scale_factor_test_field_1", "10.0", hass)
        the_number_value_should_be("number.scale_factor_test_field_2", "10.0", hass)
        the_number_value_should_be("number.scale_factor_test_field_3", "1.0", hass)
        the_number_value_should_be("number.scale_factor_test_field_4", "1.0", hass)
        the_number_value_should_be("number.scale_factor_test_field_5", "2.0", hass)
        the_number_value_should_be("number.scale_factor_test_field_6", "2.0", hass)

    async def test_sets_correct_scaled_value(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets the correct scaled value."""
        await given_the_erd_is_set_to(0x0021, "00 00 00 00 0000 0000", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_1", 10, hass)
        the_number_value_should_be("number.scale_factor_test_field_1", "10.0", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_2", 10, hass)
        the_number_value_should_be("number.scale_factor_test_field_2", "10.0", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_3", 1, hass)
        the_number_value_should_be("number.scale_factor_test_field_3", "1.0", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_4", 1, hass)
        the_number_value_should_be("number.scale_factor_test_field_4", "1.0", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_5", 1, hass)
        the_number_value_should_be("number.scale_factor_test_field_5", "1.0", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_6", 1, hass)
        the_number_value_should_be("number.scale_factor_test_field_6", "1.0", hass)

    async def test_sets_erd_with_correct_scaled_value(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test setting ERD with the correct scaled value."""
        await given_the_erd_is_set_to(0x0021, "00 00 00 00 0000 0000", hass)
        await when_the_number_is_set_to("number.scale_factor_test_field_1", 25.5, hass)
        the_mqtt_topic_value_should_be(0x0021, "FF00000000000000", mqtt_mock)
        the_number_value_should_be("number.scale_factor_test_field_1", "25.5", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_3", 2.55, hass)
        the_mqtt_topic_value_should_be(0x0021, "FF00FF0000000000", mqtt_mock)
        the_number_value_should_be("number.scale_factor_test_field_3", "2.55", hass)

        await when_the_number_is_set_to("number.scale_factor_test_field_5", 0.255, hass)
        the_mqtt_topic_value_should_be(0x0021, "FF00FF0000FF0000", mqtt_mock)
        the_number_value_should_be("number.scale_factor_test_field_5", "0.255", hass)

    async def test_sets_erd_with_correct_scaled_value_description(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test setting ERD with the correct scaled value description."""
        await given_the_erd_is_set_to(0x0022, "FF", hass)
        the_number_value_should_be(
            "number.scale_factor_description_test_scaled_by_10", "25.5", hass
        )

        await when_the_number_is_set_to(
            "number.scale_factor_description_test_scaled_by_10", 20.0, hass
        )
        the_number_value_should_be(
            "number.scale_factor_description_test_scaled_by_10", "20.0", hass
        )

    async def test_publishes_to_request_erd_and_does_not_update_paired_number(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test paired number, when set, updates the request ERD, but not the status ERD or number itself."""
        await when_the_erd_is_set_to(0x0023, "00", hass)
        await when_the_erd_is_set_to(0x0024, "00", hass)
        the_number_value_should_be("number.test_pair_test_number", "0", hass)

        await when_the_number_is_set_to("number.test_pair_test_number", 255.0, hass)
        the_mqtt_topic_value_should_be(0x0024, "FF", mqtt_mock)
        the_number_value_should_be("number.test_pair_test_number", "0", hass)

        await when_the_number_is_set_to("number.test_pair_test_number", 0, hass)
        the_mqtt_topic_value_should_be(0x0024, "00", mqtt_mock)
        the_number_value_should_be("number.test_pair_test_number", "0", hass)

    async def test_status_erd_updates_paired_number(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number updates paired number on status ERD update."""
        await when_the_erd_is_set_to(0x0023, "00", hass)
        await when_the_erd_is_set_to(0x0024, "00", hass)
        the_number_value_should_be("number.test_pair_test_number", "0", hass)

        await when_the_erd_is_set_to(0x0023, "FF", hass)
        the_number_value_should_be("number.test_pair_test_number", "255", hass)


def the_device_class_should_be(
    name: str, device_class: NumberDeviceClass, hass: HomeAssistant
) -> None:
    """Assert that the device class is correct for the entity."""
    if (entity := hass.states.get(name)) is not None:
        assert entity.attributes.get("device_class") == device_class
    else:
        pytest.fail(f"Could not find number {name}")


def the_unit_should_be(name: str, unit: str, hass: HomeAssistant) -> None:
    """Assert that the unit of measurement is correct for the entity."""
    if (entity := hass.states.get(name)) is not None:
        assert entity.attributes.get("unit_of_measurement") == unit
    else:
        pytest.fail(f"Could not find number {name}")


class TestNumberDeviceClasses:
    """Hold tests for number device classes."""

    async def test_fahrenheit_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for Fahrenheit temperatures correctly."""
        the_device_class_should_be(
            "number.temperature_test_temperature_test",
            NumberDeviceClass.TEMPERATURE,
            hass,
        )
        the_unit_should_be("number.temperature_test_temperature_test", "°F", hass)

    @pytest.mark.metric
    async def test_celsius_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for Celsius temperatures correctly."""
        the_device_class_should_be(
            "number.celsius_test_temperature_c_test",
            NumberDeviceClass.TEMPERATURE,
            hass,
        )
        the_unit_should_be("number.celsius_test_temperature_C_test", "°C", hass)

    async def test_battery_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for battery percentage correctly."""
        the_device_class_should_be(
            "number.battery_test_battery_level", NumberDeviceClass.BATTERY, hass
        )
        the_unit_should_be("number.battery_test_battery_level", "%", hass)

    async def test_energy_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for energy usage correctly."""
        the_device_class_should_be(
            "number.energy_test_energy_kWh", NumberDeviceClass.ENERGY, hass
        )
        the_unit_should_be("number.energy_test_energy_kWh", "kWh", hass)

    async def test_humidity_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for humidity correctly."""
        the_device_class_should_be(
            "number.humidity_test_humidity_test", NumberDeviceClass.HUMIDITY, hass
        )
        the_unit_should_be("number.humidity_test_humidity_test", "%", hass)

    async def test_pressure_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for pressure correctly."""
        the_device_class_should_be(
            "number.pressure_test_pressure_in_pa", NumberDeviceClass.PRESSURE, hass
        )
        the_unit_should_be("number.pressure_test_pressure_in_pa", "Pa", hass)

    async def test_gallons_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for volume in gallons correctly."""
        the_device_class_should_be(
            "number.gallons_test_gallons_test", NumberDeviceClass.VOLUME_STORAGE, hass
        )
        the_unit_should_be("number.gallons_test_gallons_test", "gal", hass)

    async def test_fluid_ounces_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for volume in fluid ounces correctly."""
        the_device_class_should_be(
            "number.fluid_ounces_test_fluid_ounces_oz",
            NumberDeviceClass.VOLUME_STORAGE,
            hass,
        )
        the_unit_should_be("number.fluid_ounces_test_fluid_ounces_oz", "fl. oz.", hass)

    async def test_pounds_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for weight in pounds correctly."""
        the_device_class_should_be(
            "number.pounds_test_pounds_lbs", NumberDeviceClass.WEIGHT, hass
        )
        the_unit_should_be("number.pounds_test_pounds_lbs", "lb", hass)

    async def test_current_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for current in mA correctly."""
        the_device_class_should_be(
            "number.current_test_current_mA", NumberDeviceClass.CURRENT, hass
        )
        the_unit_should_be("number.current_test_current_mA", "mA", hass)

    async def test_seconds_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for duration in seconds correctly."""
        the_device_class_should_be(
            "number.seconds_test_duration_seconds", NumberDeviceClass.DURATION, hass
        )
        the_unit_should_be("number.seconds_test_duration_seconds", "s", hass)

    async def test_minutes_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for duration in minutes correctly."""
        the_device_class_should_be(
            "number.minutes_test_duration_minutes", NumberDeviceClass.DURATION, hass
        )
        the_unit_should_be("number.minutes_test_duration_minutes", "min", hass)

    async def test_hours_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for duration in hours correctly."""
        the_device_class_should_be(
            "number.hours_test_duration_hours", NumberDeviceClass.DURATION, hass
        )
        the_unit_should_be("number.hours_test_duration_hours", "h", hass)

    async def test_days_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for duration in days correctly."""
        the_device_class_should_be(
            "number.days_test_duration_days", NumberDeviceClass.DURATION, hass
        )
        the_unit_should_be("number.days_test_duration_days", "d", hass)

    async def test_power_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for power in watts correctly."""
        the_device_class_should_be(
            "number.power_test_power_watts", NumberDeviceClass.POWER, hass
        )
        the_unit_should_be("number.power_test_power_watts", "W", hass)

    async def test_voltage_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for voltage correctly."""
        the_device_class_should_be(
            "number.voltage_test_voltage_test", NumberDeviceClass.VOLTAGE, hass
        )
        the_unit_should_be("number.voltage_test_voltage_test", "V", hass)

    async def test_frequency_class_and_unit(
        self, hass: HomeAssistant, mqtt_mock: MqttMockHAClient
    ) -> None:
        """Test number sets device class and unit for frequency in Hz correctly."""
        the_device_class_should_be(
            "number.frequency_test_frequency_hz", NumberDeviceClass.FREQUENCY, hass
        )
        the_unit_should_be("number.frequency_test_frequency_hz", "Hz", hass)
