"""The HaiLin Climate integration."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from .climate import HaiLinData
from .const import (
    CONF_PASSWORD,
    CONF_SUPPORT_COOL,
    CONF_SUPPORT_FAN,
    CONF_SUPPORT_HEAT,
    CONF_TEMP_STEP,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the HaiLin Climate component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HaiLin Climate from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config = entry.data
    _LOGGER.info("Setting up HaiLin Climate integration")
    _LOGGER.debug("Configuration: %s", {**config, "password": "***"})

    hailin = HaiLinData(
        hass,
        config[CONF_TYPE],
        config[CONF_USERNAME],
        config[CONF_PASSWORD],
        config.get(CONF_TEMP_STEP, 0.5),
        config.get(CONF_SUPPORT_FAN, False),
        config.get(CONF_SUPPORT_COOL, False),
        config.get(CONF_SUPPORT_HEAT, False),
    )

    _LOGGER.info("Initializing HaiLin data manager")
    await hailin.update_data()

    if not hailin.devs:
        _LOGGER.error(
            "No HaiLin devices found. Please check your account and device configuration."
        )
        return False

    _LOGGER.info("Found %d HaiLin devices", len(hailin.devs))
    for index, device in enumerate(hailin.devs):
        _LOGGER.debug(
            "Device %d: %s (ID: %s)",
            index,
            device.get("name", "Unknown"),
            device.get("id", "Unknown"),
        )

    hailin.unsub_listeners = []
    hass.data[DOMAIN][entry.entry_id] = hailin

    update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    _LOGGER.info("Setting up data update interval (%d seconds)", update_interval)
    hailin.unsub_listeners.append(
        async_track_time_interval(
            hass,
            hailin.async_update,
            timedelta(seconds=update_interval),
        )
    )

    _LOGGER.info("Setting up login refresh interval (3 days)")
    hailin.unsub_listeners.append(
        async_track_time_interval(hass, hailin.login, timedelta(days=3))
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("HaiLin Climate integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hailin = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if hailin is not None:
            for unsub in getattr(hailin, "unsub_listeners", []):
                unsub()
            hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok

    return False
