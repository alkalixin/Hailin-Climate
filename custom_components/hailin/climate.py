import asyncio
import json as JSON
import logging
from datetime import timedelta
from urllib.parse import urlencode

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE, ATTR_HVAC_MODE, \
    HVAC_MODE_HEAT, HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_FAN_ONLY, CURRENT_HVAC_HEAT, CURRENT_HVAC_OFF, \
    CURRENT_HVAC_COOL, CURRENT_HVAC_FAN, ATTR_CURRENT_TEMPERATURE, ATTR_MAX_TEMP, ATTR_MIN_TEMP, ATTR_FAN_MODE, \
    FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH, \
    SUPPORT_FAN_MODE
from homeassistant.const import ATTR_ID, ATTR_NAME, CONF_USERNAME, CONF_TYPE, CONF_PASSWORD, CONF_SCAN_INTERVAL, \
    ATTR_TEMPERATURE
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import STORAGE_DIR

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hailin"
USER_AGENT = "Hailin/4.2.0 (iPhone; iOS 15.2; Scale/3.00)"
CONF_TEMP_STEP = 'temp_step'

AUTH_URL = "http://yunpan.hailin.com:8080/hailin/oauth/token?client_id=hailin_client&client_secret=hailin_client_secret&grant_type=password&oauth_type=%s&password=%s&username=%s"
LIST_URL = "http://yunpan.hailin.com:8080/hailin/api/page/home"
CTRL_URL = "http://yunpan.hailin.com:8080/hailin/api/device/operationDevice"

DEFAULT_NAME = 'Hailin'
ATTR_AVAILABLE = 'available'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TYPE): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=timedelta(seconds=300)): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_TEMP_STEP, default=0.5): cv.positive_float
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hailin = HailinData(hass, config[CONF_TYPE], config[CONF_USERNAME], config[CONF_PASSWORD], config[CONF_TEMP_STEP])
    await hailin.update_data()
    if not hailin.devs:
        _LOGGER.error("No sensors added.")
        return

    hailin.devices = [HailinClimate(hailin, index) for index in range(len(hailin.devs))]
    _LOGGER.debug('hailin devices: %s', hailin.devices)
    async_add_entities(hailin.devices)

    # 根据配置中的实际定时更新状态
    async_track_time_interval(hass, hailin.async_update, config.get(CONF_SCAN_INTERVAL))


class HailinClimate(ClimateEntity):
    """Representation of a Hailin climate device."""

    def __init__(self, hailin, index):
        """Initialize the climate device."""
        self._index = index
        self._hailin = hailin
        self.modeEnum = {
            HVAC_MODE_COOL: CURRENT_HVAC_COOL,
            HVAC_MODE_HEAT: CURRENT_HVAC_HEAT,
            HVAC_MODE_FAN_ONLY: CURRENT_HVAC_FAN,
            HVAC_MODE_OFF: CURRENT_HVAC_OFF
        }
        self.modes = [HVAC_MODE_OFF]

    @property
    def unique_id(self):
        from homeassistant.util import slugify
        return self.__class__.__name__.lower() + '.' + slugify(self.name)

    @property
    def name(self):
        """Return the name of the climate device."""
        return self.get_value(ATTR_NAME)

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self.get_value(ATTR_AVAILABLE)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        supports = 0
        if self.get_value(ATTR_HVAC_MODE) != HVAC_MODE_FAN_ONLY:
            supports = supports | SUPPORT_TARGET_TEMPERATURE
        if self.get_value("SUPPORT_FAN_MODE") and (
                self.get_value(ATTR_HVAC_MODE) == HVAC_MODE_FAN_ONLY or self.get_value(
            ATTR_HVAC_MODE) == HVAC_MODE_COOL):
            supports = supports | SUPPORT_FAN_MODE
        return supports

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._hailin._hass.config.units.temperature_unit

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
        """Return current operation ie. heat, cool, idle."""
        return self.modeEnum[self.hvac_mode]

    @property
    def hvac_mode(self):
        """Return hvac target hvac state."""
        return self.get_value(ATTR_HVAC_MODE)

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        if self.get_value("SUPPORT_FAN_MODE"):
            self.modes.append(HVAC_MODE_FAN_ONLY)
        if self.get_value("SUPPORT_HEAT_MODE"):
            self.modes.append(HVAC_MODE_HEAT)
        if self.get_value("SUPPORT_COOL_MODE"):
            self.modes.append(HVAC_MODE_COOL)
        return list(set(self.modes))  # 去重

    @property
    def fan_mode(self):
        """Return preset mode."""
        return self.get_value(ATTR_FAN_MODE)

    @property
    def fan_modes(self):
        """Return preset modes."""
        return [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    @property
    def should_poll(self):  # pylint: disable=no-self-use
        """No polling needed."""
        return False

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.set_value(ATTR_TEMPERATURE, temperature)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        await self.set_value(ATTR_HVAC_MODE, hvac_mode)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        await self.set_value(ATTR_FAN_MODE, fan_mode)

    def get_value(self, prop):
        """Get property value"""
        devs = self._hailin.devs
        if devs and self._index < len(devs):
            return devs[self._index][prop]
        return None

    async def set_value(self, prop, value):
        """Set property value"""
        if await self._hailin.control(self._index, prop, value):
            await self.async_update_ha_state()


class HailinData():
    """Class for handling the data retrieval."""

    def __init__(self, hass, type, username, password, temp_step):
        """Initialize the data object."""
        self._hass = hass
        self._type = type
        self._username = username.replace('@', '%40')
        self._password = password
        self.temp_step = temp_step
        self._token_path = hass.config.path(STORAGE_DIR, DOMAIN)
        self.devs = None
        self._token_type = 'bearer'

        # 风速相关 - fan_mod(dev_type=14)
        # 低速：3
        # 中速：4
        # 高速：5
        # 自动：0
        self._num2fan_modes = {
            3: FAN_LOW,
            4: FAN_MEDIUM,
            5: FAN_HIGH,
            0: FAN_AUTO,
        }
        self._fan_modes2num = {
            FAN_LOW: 3,
            FAN_MEDIUM: 4,
            FAN_HIGH: 5,
            FAN_AUTO: 0,
        }

        # status
        # 2: 地暖加热中(dev_type=8)
        # 4: 地暖未加热(dev_type=8)
        # 7: 地暖(dev_type=14)
        # 1: 制冷(dev_type=14)
        # 5: 通风(dev_type=14)
        self._status2hvac_mode = {
            2: HVAC_MODE_HEAT,
            4: HVAC_MODE_HEAT,
            7: HVAC_MODE_HEAT,
            1: HVAC_MODE_COOL,
            5: HVAC_MODE_FAN_ONLY
        }

        self._hvac_mode2status = {
            HVAC_MODE_HEAT: 7,
            HVAC_MODE_COOL: 1,
            HVAC_MODE_FAN_ONLY: 5
        }

        try:
            with open(self._token_path) as file:
                self._token = file.read()
                _LOGGER.debug("Load token: %s", self._token_path)
        except Exception:
            self._token = None

    async def async_update(self, time):
        """Update online data and update ha state."""
        old_devs = self.devs
        await self.update_data()

        tasks = []
        index = 0
        for device in self.devices:
            if not old_devs or not self.devs or old_devs[index] != self.devs[index]:
                _LOGGER.debug('%s: => %s', device.name, device.state)
                tasks.append(device.async_update_ha_state())

        if tasks:
            await asyncio.wait(tasks, loop=self._hass.loop)

    async def update_data(self):
        """Update online data."""
        try:
            json = await self.request(LIST_URL, {})
            if ('error' in json) and (json['error'] != '0'):
                _LOGGER.debug("Reset token: error=%s", json['error'])
                self._token = None
                json = await self.request(LIST_URL, {})
            devs = []
            list = json['data']['devices']
            for dev in list:
                if not isinstance(dev, dict):
                    raise TypeError(f"{json}")
                device_json_object = JSON.loads(dev['device_json_object'])

                support_fan_mode = device_json_object.get('dirty_fan_mod', False)  # 支持送风
                support_heat_mode = device_json_object.get('dirty_heat_mode', False)  # 支持加热
                support_cool_mode = device_json_object.get('dirty_temp_cool', False)  # 支持制冷

                status_onoff = int(device_json_object.get('status_onoff', 0))  # 开机：1   关机：0
                status = int(device_json_object.get('status', 2))
                mode = 'cool' if (status == 1 or status == 5) else 'heat'
                hvac_mode = HVAC_MODE_OFF
                if status_onoff == 1:
                    hvac_mode = self._status2hvac_mode[status]

                dev_entity = {
                    "SUPPORT_FAN_MODE": support_fan_mode,
                    "SUPPORT_HEAT_MODE": support_heat_mode,
                    "SUPPORT_COOL_MODE": support_cool_mode,
                    'mode': mode,  # 用于组装发起请求时的字段
                    ATTR_HVAC_MODE: hvac_mode,  # 当前模式： 加热、制冷、吹风、关机
                    ATTR_CURRENT_TEMPERATURE: float(device_json_object.get('dis_temp')[1:]),  # 当前温度
                    ATTR_TEMPERATURE: float(device_json_object.get('temp_' + mode)[1:]),  # 设定温度
                    ATTR_AVAILABLE: dev.get('is_enabled'),
                    ATTR_MAX_TEMP: float(device_json_object.get('temp_' + mode + '_default_max', 'c30.0')[1:]),  # 最高温度
                    ATTR_MIN_TEMP: float(device_json_object.get('temp_' + mode + '_default_min', 'c10.0')[1:]),  # 最低温度
                    ATTR_NAME: dev.get('dis_dev_name'),  # 设备名称
                    ATTR_ID: dev.get('mac')  # 用mac地址当做id
                }

                if support_fan_mode:
                    dev_entity[ATTR_FAN_MODE] = self._num2fan_modes[int(device_json_object.get('fan_mod', 0))]  # 风扇速度

                devs.append(dev_entity)
            self.devs = devs
            _LOGGER.debug("List device: devs=%s", self.devs)
        except Exception:
            import traceback
            _LOGGER.error(traceback.format_exc())

    async def control(self, index, prop, value):
        """Control device via server."""
        data = {
            "mac": self.devs[index][ATTR_ID]
        }
        try:
            # 切换模式：heat cool fan_only off
            if prop == ATTR_HVAC_MODE:
                if value == HVAC_MODE_OFF:
                    data['operation'] = JSON.dumps({
                        'status_onoff': '0'
                    }).replace(" ", "")
                else:
                    # todo 这里最好需要根据不同的设备发出不同的请求。
                    data['operation'] = JSON.dumps({
                        'status_onoff': '1',
                        'status': self._hvac_mode2status[value]
                    }).replace(" ", "")
            # 切换温度
            elif prop == ATTR_TEMPERATURE:
                data['operation'] = JSON.dumps({
                    'heat_mode': 0,
                    'temp_' + self.devs[index]['mode']: 'c%s' % value
                }).replace(" ", "")
            # 切换风速
            elif prop == ATTR_FAN_MODE:
                data['operation'] = JSON.dumps({
                    'fan_mod': str(self._fan_modes2num[value])
                }).replace(" ", "")
            else:
                return False
            data = urlencode(data)
            json = await self.request(CTRL_URL, data)
            _LOGGER.debug("Control device: prop=%s, data=%s, json=%s", prop, JSON.dumps(data), json)
            if json['code'] == 200:
                self.devs[index][prop] = value
                return True
            return False
        except Exception:
            import traceback
            _LOGGER.error('Exception: %s', traceback.format_exc())
            return False

    async def request(self, url, data):
        """Request from server."""
        session = self._hass.helpers.aiohttp_client.async_get_clientsession()
        if self._token is None:
            await self.login()

        headers = {'User-Agent': USER_AGENT, 'Authorization': "%s %s" % (self._token_type, self._token),
                   'Content-Type': 'application/x-www-form-urlencoded'}
        _LOGGER.debug("Hailin URL: %s; data: %s", url, JSON.dumps(data))
        async with await session.post(url, headers=headers, data=data) as r:
            _LOGGER.debug("Hailin response: %s", await r.text())
            res = await r.json()
            _LOGGER.debug('Hailin request resonse: %s', res)
            return res

    async def login(self):
        """Request from server."""
        session = self._hass.helpers.aiohttp_client.async_get_clientsession()

        headers = {'User-Agent': USER_AGENT}
        auth_url = AUTH_URL % (self._type, self._password, self._username)
        _LOGGER.debug('start login')
        async with await session.get(auth_url, headers=headers) as r:
            json = await r.json()
        if 'error' in json:
            _LOGGER.error('login fail: %s', json['error'])
            return None

        _LOGGER.debug("Get token: %s", json['access_token'])
        self._token = json['access_token']
        self._token_type = json['token_type']
        with open(self._token_path, 'w') as file:
            file.write(self._token)
