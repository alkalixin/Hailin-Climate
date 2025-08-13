"""The HaiLin Climate integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    CONF_TYPE,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_TEMP_STEP,
    CONF_SUPPORT_FAN,
    CONF_SUPPORT_COOL,
    CONF_SUPPORT_HEAT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .climate import HaiLinData

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

    # 创建数据管理器
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

    # 初始化数据
    _LOGGER.info("Initializing HaiLin data manager")
    await hailin.update_data()

    if not hailin.devs:
        _LOGGER.error(
            "No HaiLin devices found. Please check your account and device configuration."
        )
        return False

    _LOGGER.info("Found %d HaiLin devices", len(hailin.devs))
    for i, dev in enumerate(hailin.devs):
        _LOGGER.debug(
            "Device %d: %s (ID: %s)",
            i,
            dev.get("name", "Unknown"),
            dev.get("id", "Unknown"),
        )

    # 存储数据管理器到hass.data
    hass.data[DOMAIN][entry.entry_id] = hailin
    
    # 设置定时更新任务
    update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    _LOGGER.info("Setting up data update interval (%d seconds)", update_interval)
    async_track_time_interval(
        hass,
        hailin.async_update,
        timedelta(seconds=update_interval),
    )

    # 每隔3天定时重新登录
    _LOGGER.info("Setting up login refresh interval (3 days)")
    async_track_time_interval(hass, hailin.login, timedelta(days=3))
    
    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("HaiLin Climate integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # 清理数据管理器
        if entry.entry_id in hass.data[DOMAIN]:
            hailin = hass.data[DOMAIN][entry.entry_id]
            # 清理认证会话
            if hasattr(hailin, 'auth') and hasattr(hailin.auth, 'session') and hailin.auth.session:
                await hailin.auth.session.close()
            hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
