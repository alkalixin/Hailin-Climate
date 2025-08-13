"""Support for HaiLin Climate devices."""

import json as JSON
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
    ATTR_CURRENT_TEMPERATURE,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACAction,
    HVACMode,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ID,
    ATTR_NAME,
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CTRL_URL,
    DOMAIN,
    LIST_URL,
)
from .auth import HaiLinAuth

_LOGGER = logging.getLogger(__name__)

ATTR_AVAILABLE = "available"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HaiLin Climate platform."""
    _LOGGER.info("Setting up HaiLin Climate platform")
    
    # 从hass.data获取已初始化的数据管理器
    hailin = hass.data[DOMAIN][config_entry.entry_id]
    
    if not hailin.devs:
        _LOGGER.error("No HaiLin devices available")
        return

    # 创建气候实体
    hailin.devices = [HaiLinClimate(hailin, index) for index in range(len(hailin.devs))]
    _LOGGER.debug("Created %d HaiLin climate entities", len(hailin.devices))

    # 显示每个设备的MAC地址和entity_id信息
    for i, device in enumerate(hailin.devices):
        mac = hailin.devs[i].get("mac", hailin.devs[i].get("id", "Unknown"))
        _LOGGER.info(
            "Device %d: %s (MAC: %s, unique_id: %s)",
            i,
            device.name,
            mac,
            device.unique_id,
        )

    async_add_entities(hailin.devices)

    _LOGGER.info("HaiLin Climate platform setup completed successfully")


class HaiLinClimate(ClimateEntity):
    """Representation of a HaiLin climate device."""

    def __init__(self, hailin, index):
        """Initialize the climate device."""
        self._index = index
        self._hailin = hailin
        self.modeEnum = {
            HVACMode.COOL: HVACAction.COOLING,
            HVACMode.HEAT: HVACAction.HEATING,
            HVACMode.FAN_ONLY: HVACAction.FAN,
            HVACMode.OFF: HVACAction.OFF,
        }

    @property
    def unique_id(self):
        """Return the unique ID of the device."""
        mac = self._hailin.devs[self._index].get(
            "mac", self._hailin.devs[self._index].get("id", self._index)
        )
        return mac

    @property
    def name(self):
        """Return the name of the device."""
        return self._hailin.devs[self._index].get("name", f"HaiLin {self._index}")

    @property
    def available(self):
        """Return True if entity is available."""
        return self._hailin.devs[self._index].get(ATTR_AVAILABLE, False)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        supports = 0
        if self.get_value(ATTR_HVAC_MODE) != HVACMode.FAN_ONLY:
            supports = supports | ClimateEntityFeature.TARGET_TEMPERATURE
        if self.get_value("SUPPORT_FAN_MODE") and (
            self.get_value(ATTR_HVAC_MODE) == HVACMode.FAN_ONLY
            or self.get_value(ATTR_HVAC_MODE) == HVACMode.COOL
        ):
            supports = supports | ClimateEntityFeature.FAN_MODE
        return supports

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._hailin.temp_step

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.get_value(ATTR_CURRENT_TEMPERATURE)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.get_value(ATTR_TEMPERATURE)

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        return self.get_value("hvac_action")

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        return self.get_value(ATTR_HVAC_MODE)

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self.get_value(ATTR_MIN_TEMP)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self.get_value(ATTR_MAX_TEMP)

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes."""
        modes = [HVACMode.OFF]

        # 根据设备的实际支持情况返回可用模式
        support_fan = self.get_value("SUPPORT_FAN_MODE")
        support_cool = self.get_value("SUPPORT_COOL_MODE")
        support_heat = self.get_value("SUPPORT_HEAT_MODE")

        if support_fan:
            modes.append(HVACMode.FAN_ONLY)
        if support_cool:
            modes.append(HVACMode.COOL)
        if support_heat:
            modes.append(HVACMode.HEAT)

        return list(set(modes))  # 去重

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self.get_value(ATTR_FAN_MODE)

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        if self.get_value("SUPPORT_FAN_MODE"):
            return [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
        return []

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        _LOGGER.info("async_set_temperature called with kwargs: %s", kwargs)
        if ATTR_TEMPERATURE in kwargs:
            _LOGGER.info("Setting target temperature to: %s", kwargs[ATTR_TEMPERATURE])
            await self.set_value(ATTR_TEMPERATURE, kwargs[ATTR_TEMPERATURE])
        else:
            _LOGGER.warning("ATTR_TEMPERATURE not found in kwargs: %s", kwargs)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.info("Setting HVAC mode: %s", hvac_mode)
        await self.set_value(ATTR_HVAC_MODE, hvac_mode)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        await self.set_value(ATTR_FAN_MODE, fan_mode)

    def get_value(self, prop):
        """Get property value from device data."""
        return self._hailin.devs[self._index].get(prop)

    async def set_value(self, prop, value):
        """Set property value on device."""
        _LOGGER.debug("Setting %s to %s", prop, value)
        await self._hailin.control(self._index, prop, value)


class HaiLinData:
    """Get the latest data and update the states."""

    def __init__(
        self,
        hass,
        type,
        username,
        password,
        temp_step,
        support_fan,
        support_cool,
        support_heat,
    ):
        """Initialize the data object."""
        self.hass = hass
        self.type = type
        self.username = username
        self.password = password
        self.temp_step = temp_step
        self.support_fan = support_fan
        self.support_cool = support_cool
        self.support_heat = support_heat

        self.auth = HaiLinAuth(hass)
        self.houses = []
        self.devs = []
        self.devices = []

    async def async_update(self, time):
        """Update device data."""
        _LOGGER.debug("Scheduled update triggered at %s", time)
        await self.update_data()

        # 通知所有实体状态已更新
        for device in self.devices:
            if hasattr(device, "async_write_ha_state"):
                device.async_write_ha_state()
                _LOGGER.debug("Notified entity %s of state update", device.name)

    async def update_data(self):
        """Update device data."""
        _LOGGER.debug("Starting HaiLin data update")
        try:
            if not self.auth.get_token():
                _LOGGER.info("No token available, attempting login")
                await self.login()
            else:
                _LOGGER.debug("Token available, skipping login")

            if not self.houses:
                _LOGGER.info("No houses available, fetching house information")
                await self.get_houses()
            else:
                _LOGGER.debug("Houses available: %d houses", len(self.houses))

            _LOGGER.debug("Fetching device lists from all houses")
            await self.get_all_devices()

            _LOGGER.info(
                "HaiLin data update completed successfully. Found %d devices",
                len(self.devs),
            )

        except Exception as e:
            _LOGGER.error("Failed to update HaiLin data: %s", str(e))
            _LOGGER.debug("Exception type: %s", type(e).__name__)
            import traceback

            _LOGGER.debug("Full traceback: %s", traceback.format_exc())

    async def control(self, index, prop, value):
        """Control device via server."""
        _LOGGER.info(
            "control method called: index=%d, prop=%s, value=%s (type: %s)",
            index,
            prop,
            value,
            type(value),
        )
        try:
            device = self.devs[index]
            device_name = device.get("name", "Unknown")
            device_mac = device.get("mac")

            if not device_mac:
                _LOGGER.error("Device MAC not found for index %d", index)
                return False

            _LOGGER.debug("Device: %s (MAC: %s)", device_name, device_mac)

            data = {"mac": device_mac}

            # 切换模式：heat cool fan_only off
            if prop == ATTR_HVAC_MODE:
                _LOGGER.debug(
                    "Processing HVAC mode control: value=%s, type=%s",
                    value,
                    type(value),
                )
                if value == HVACMode.OFF:
                    _LOGGER.info("Turning device OFF")
                    data["operation"] = JSON.dumps({"status_onoff": "0"}).replace(
                        " ", ""
                    )
                else:
                    # 根据不同的HVAC模式设置对应的status值
                    hvac_mode2status = {
                        HVACMode.HEAT: 7,
                        HVACMode.COOL: 1,
                        HVACMode.FAN_ONLY: 5,
                    }
                    status = hvac_mode2status.get(value, 1)
                    _LOGGER.info(
                        "Turning device ON with mode: %s (status: %d)", value, status
                    )
                    data["operation"] = JSON.dumps(
                        {"status_onoff": "1", "status": status}
                    ).replace(" ", "")

            # 切换温度
            elif prop == ATTR_TEMPERATURE:
                # 获取当前模式，默认为heat
                current_mode = device.get("mode", "heat")
                data["operation"] = JSON.dumps(
                    {"heat_mode": 0, "temp_" + current_mode: "c%s" % value}
                ).replace(" ", "")

            # 切换风速
            elif prop == ATTR_FAN_MODE:
                fan_modes2num = {
                    FAN_AUTO: 0,
                    FAN_LOW: 3,
                    FAN_MEDIUM: 4,
                    FAN_HIGH: 5,
                }
                fan_num = fan_modes2num.get(value, 0)
                data["operation"] = JSON.dumps({"fan_mod": str(fan_num)}).replace(
                    " ", ""
                )

            else:
                _LOGGER.warning("Unsupported property: %s", prop)
                return False

            _LOGGER.debug("Sending control request: %s", data)
            result = await self.auth.request(CTRL_URL, JSON.dumps(data))

            _LOGGER.debug(
                "Control device: prop=%s, data=%s, result=%s",
                prop,
                JSON.dumps(data),
                result,
            )

            if result == {}:
                _LOGGER.info(
                    "Successfully controlled device %s: %s = %s",
                    device_name,
                    prop,
                    value,
                )
                # 更新本地数据
                self.devs[index][prop] = value
                _LOGGER.debug("Updated local device data")

                # 通知对应的实体状态已更新
                if index < len(self.devices):
                    device_entity = self.devices[index]
                    if hasattr(device_entity, "async_write_ha_state"):
                        device_entity.async_write_ha_state()
                        _LOGGER.debug(
                            "Notified entity %s of control update", device_entity.name
                        )

                return True
            else:
                _LOGGER.error(
                    "Control request failed for device %s, result: %s",
                    device_name,
                    result,
                )
                return False

        except KeyError as e:
            _LOGGER.error("Key Error happens: %s", str(e))
            return False
        except Exception as e:
            _LOGGER.error("Failed to control device index %d: %s", index, str(e))
            _LOGGER.debug("Exception type: %s", type(e).__name__)
            import traceback

            _LOGGER.debug("Full traceback: %s", traceback.format_exc())
            return False



    async def login(self):
        """Login to HaiLin service."""
        _LOGGER.info("Attempting to login to HaiLin service")

        token = await self.auth.login(self.type, self.username, self.password)

        if not token:
            _LOGGER.error("Failed to login to HaiLin for user: %s", self.username)
        else:
            _LOGGER.info("Successfully logged in to HaiLin for user: %s", self.username)

    async def get_houses(self):
        """Get all houses."""
        _LOGGER.info("Fetching houses from HaiLin service")
        self.houses = await self.auth.get_houses()

        if self.houses:
            _LOGGER.info(
                "Successfully got %d houses from HaiLin service", len(self.houses)
            )
            for i, house in enumerate(self.houses):
                _LOGGER.debug(
                    "House %d: %s (ID: %s)",
                    i,
                    house.get("name", "Unknown"),
                    house.get("house_id", "Unknown"),
                )
        else:
            _LOGGER.error("Failed to get houses from HaiLin service")

    async def get_all_devices(self):
        """Get device lists from all houses."""
        _LOGGER.info("Fetching device lists from all houses")

        if not self.houses:
            _LOGGER.error("No houses available, cannot fetch device lists")
            return

        all_devices = []

        for house in self.houses:
            house_id = house.get("house_id")
            house_name = house.get("name", "Unknown")

            if not house_id:
                _LOGGER.error("House ID not available for house: %s", house_name)
                continue

            _LOGGER.debug(
                "Fetching devices for house: %s (ID: %s)", house_name, house_id
            )

            # 构建带查询参数的URL
            url = f"{LIST_URL}?house_id={house_id}&of_all=0"
            _LOGGER.debug("Device list URL: %s", url)

            result = await self.auth.request(url, method="GET")

            if result and "data" in result:
                groups = result["data"]
                _LOGGER.info(
                    "Successfully got %d groups from house: %s", len(groups), house_name
                )

                for group in groups:
                    group_name = group.get("group_name", "Unknown")
                    group_id = group.get("group_id")
                    _LOGGER.debug("Processing group: %s (ID: %s)", group_name, group_id)

                    if "devicesGroupItems" in group:
                        devices = group["devicesGroupItems"]
                        _LOGGER.info(
                            "Found %d devices in group: %s", len(devices), group_name
                        )

                        # 为每个设备添加房屋和组信息
                        for device in devices:
                            # 保存外层的设备名称
                            outer_device_name = device.get("dis_dev_name", "Unknown")

                            # 解析设备JSON对象
                            device_json = device.get("device_json_object", "{}")
                            try:
                                device_json_object = JSON.loads(device_json)

                                # 根据原版逻辑处理设备支持的功能
                                support_fan_mode = (
                                    device_json_object.get("dirty_fan_mod", False)
                                    if (self.support_fan is None)
                                    else self.support_fan
                                )  # 支持送风
                                support_heat_mode = (
                                    device_json_object.get("dirty_heat_mode", False)
                                    if (self.support_heat is None)
                                    else self.support_heat
                                )  # 支持加热
                                support_cool_mode = (
                                    device_json_object.get("dirty_temp_cool", False)
                                    if (self.support_cool is None)
                                    else self.support_cool
                                )  # 支持制冷

                                status_onoff = int(
                                    device_json_object.get("status_onoff", 0)
                                )  # 开机：1   关机：0
                                status = int(device_json_object.get("status", 2))
                                mode = "cool" if support_cool_mode else "heat"

                                # HVAC模式映射
                                # status
                                # 2: 地暖加热中(dev_type=8)
                                # 4: 地暖未加热(dev_type=8)
                                # 7: 地暖(dev_type=14 || 8)
                                # 1: 制冷(dev_type=14)
                                # 5: 通风(dev_type=14)
                                _status2hvac_mode = {
                                    2: HVACMode.HEAT,
                                    4: HVACMode.HEAT,
                                    7: HVACMode.HEAT,
                                    1: HVACMode.COOL,
                                    5: HVACMode.FAN_ONLY,
                                }

                                hvac_mode = HVACMode.OFF
                                if status_onoff == 1:
                                    hvac_mode = _status2hvac_mode.get(
                                        status, HVACMode.OFF
                                    )

                                # 风扇模式映射
                                _num2fan_modes = {
                                    3: FAN_LOW,
                                    4: FAN_MEDIUM,
                                    5: FAN_HIGH,
                                    0: FAN_AUTO,
                                }

                                # 构建完整的设备实体数据
                                dev_entity = {
                                    "SUPPORT_FAN_MODE": support_fan_mode,
                                    "SUPPORT_HEAT_MODE": support_heat_mode,
                                    "SUPPORT_COOL_MODE": support_cool_mode,
                                    "mode": mode,  # 用于组装发起请求时的字段
                                    ATTR_HVAC_MODE: hvac_mode,  # 当前模式： 加热、制冷、吹风、关机
                                    ATTR_CURRENT_TEMPERATURE: float(
                                        device_json_object.get("dis_temp", "c20.0")[1:]
                                    ),  # 当前温度
                                    ATTR_TEMPERATURE: float(
                                        device_json_object.get("temp_" + mode, "c22.0")[
                                            1:
                                        ]
                                    ),  # 设定温度
                                    ATTR_AVAILABLE: device.get("is_enabled"),
                                    ATTR_MAX_TEMP: float(
                                        device_json_object.get(
                                            "temp_" + mode + "_default_max", "c30.0"
                                        )[1:]
                                    ),  # 最高温度
                                    ATTR_MIN_TEMP: float(
                                        device_json_object.get(
                                            "temp_" + mode + "_default_min", "c10.0"
                                        )[1:]
                                    ),  # 最低温度
                                    ATTR_NAME: outer_device_name,  # 设备名称
                                    ATTR_ID: device.get("mac"),  # 用mac地址当做id
                                    "mac": device.get("mac"),  # MAC地址
                                    "dis_dev_name": outer_device_name,  # 设备显示名称
                                    # 添加房屋和组信息
                                    "house_id": house_id,
                                    "house_name": house_name,
                                    "group_id": group_id,
                                    "group_name": group_name,
                                    # 原始设备数据
                                    "device_json_object": device_json,
                                    "status_onoff": status_onoff,
                                    "status": status,
                                }

                                if support_fan_mode:
                                    dev_entity["fan_mode"] = _num2fan_modes.get(
                                        int(device_json_object.get("fan_mod", 0)),
                                        "auto",
                                    )  # 风扇速度

                                # 合并原始设备信息
                                dev_entity.update(device)

                                all_devices.append(dev_entity)

                            except (JSON.JSONDecodeError, Exception) as e:
                                _LOGGER.warning(
                                    "Failed to parse device JSON for device %s: %s",
                                    outer_device_name,
                                    str(e),
                                )
                                # 如果解析失败，至少保留基本信息
                                device["name"] = outer_device_name
                                device["available"] = device.get("is_enabled")
                                device["house_id"] = house_id
                                device["house_name"] = house_name
                                device["group_id"] = group_id
                                device["group_name"] = group_name
                                all_devices.append(device)

                            _LOGGER.debug(
                                "Device: %s (ID: %s, MAC: %s, Group: %s, House: %s)",
                                device.get("name", "Unknown"),
                                device.get("id", "Unknown"),
                                device.get("mac", "Unknown"),
                                group_name,
                                house_name,
                            )
                    else:
                        _LOGGER.warning("No devices found in group: %s", group_name)
            else:
                _LOGGER.error("Failed to get device list from house: %s", house_name)
                if result:
                    _LOGGER.debug("Device list response (no data): %s", result)
                else:
                    _LOGGER.debug("No response received from device list request")

        self.devs = all_devices
        _LOGGER.info("Total devices found across all houses: %d", len(self.devs))

        # 记录每个设备的当前状态
        for i, dev in enumerate(self.devs):
            _LOGGER.debug(
                "Device %d: %s - HVAC Mode: %s, Current Temp: %s, Target Temp: %s, Available: %s",
                i,
                dev.get("name", "Unknown"),
                dev.get("hvac_mode", "Unknown"),
                dev.get("current_temperature", "Unknown"),
                dev.get("target_temperature", "Unknown"),
                dev.get("available", "Unknown"),
            )
