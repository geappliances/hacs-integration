"""Common values and helpers for tests."""

import json
from unittest.mock import patch

from custom_components.geappliances.const import DISCOVERY, DOMAIN, Erd
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM, UnitSystem

ERD_VALUE_TOPIC = "geappliances/test/erd/{}/value"
ERD_WRITE_TOPIC = "geappliances/test/erd/{}/write"


def config_entry_stub() -> MockConfigEntry:
    """Config entry version 1 fixture."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="test",
        data={
            "name": "test",
        },
        version=1,
    )


async def given_integration_is_initialized(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    unit_system: UnitSystem = US_CUSTOMARY_SYSTEM,
) -> None:
    """Test integration sets up discovery singleton."""
    with (
        patch(
            "custom_components.geappliances.get_appliance_api_json"
        ) as get_appliance_api_json,
        patch(
            "custom_components.geappliances.get_appliance_api_erd_defs_json"
        ) as get_appliance_api_erd_defs_json,
        patch(
            "custom_components.geappliances.get_meta_erds_json"
        ) as get_meta_erds_json,
    ):
        get_appliance_api_json.return_value = "{}"
        get_appliance_api_erd_defs_json.return_value = '{"erds": {}}'
        get_meta_erds_json.return_value = "{}"
        entry = config_entry_stub()
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        hass.config.units = unit_system
        given_the_special_erd_map_is({}, hass)


def given_the_appliance_api_is(appliance_api: str, hass: HomeAssistant) -> None:
    """Set the appliance API for the integration."""
    hass.data[DOMAIN][DISCOVERY]._data_source._appliance_api = json.loads(appliance_api)


def given_the_appliance_api_erd_defs_are(erd_defs: str, hass: HomeAssistant) -> None:
    """Set the appliance API ERDs definitions for the integration."""
    hass.data[DOMAIN][
        DISCOVERY
    ]._data_source._appliance_api_erd_definitions = json.loads(erd_defs)["erds"]


def given_the_status_pair_dict_is(status_pair_str: str, hass: HomeAssistant) -> None:
    """Set the status pair dictionary for the integration."""
    hass.data[DOMAIN][DISCOVERY]._data_source._status_pair_dict = json.loads(
        status_pair_str
    )


def given_the_special_erd_map_is(special_erd_map: dict, hass: HomeAssistant) -> None:
    """Set the special ERD map for the integration."""
    hass.data[DOMAIN][
        DISCOVERY
    ]._erd_factory._special_erd_coordinator._special_erds_map = special_erd_map


async def given_the_erd_is_set_to(erd: Erd, state: str, hass: HomeAssistant) -> None:
    """Fire MQTT message."""
    async_fire_mqtt_message(hass, ERD_VALUE_TOPIC.format(f"{erd:#06x}"), state)
    await hass.async_block_till_done()


async def when_the_erd_is_set_to(erd: Erd, state: str, hass: HomeAssistant) -> None:
    """Fire MQTT message."""
    await given_the_erd_is_set_to(erd, state, hass)


def the_mqtt_topic_value_should_be(
    erd: Erd, state: str, mqtt_mock: MqttMockHAClient
) -> None:
    """Check the ERD was published to MQTT."""
    mqtt_mock.async_publish.assert_called_with(
        ERD_WRITE_TOPIC.format(f"{erd:#06x}"), state.lower(), 0, False
    )


def mqtt_client_should_not_publish(mqtt_client_mock: MqttMockHAClient) -> None:
    """Assert MQTT has not published anything."""
    mqtt_client_mock.async_publish.assert_not_called()
