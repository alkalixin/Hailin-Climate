import asyncio
import json as JSON
import logging
from datetime import timedelta

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
USER_AGENT = "okhttp/3.8.0"
CONF_TEMP_STEP = 'temp_step'

AUTH_URL = "https://yunpan.hailin.com/user/v1/user/login"
HOUSE_URL = "https://yunpan.hailin.com/device/v1/device/house"
LIST_URL = "https://yunpan.hailin.com/device/v1/device/group/findUserGroup?house_id=%s&of_all=0"
CTRL_URL = "https://yunpan.hailin.com/device/api/device/operationDevice"

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

    # ??????????????????????????????????????????
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
        return list(set(self.modes))  # ??????

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
        self._house_id = None
        self._token = None
        self._token_type = 'bearer'

        # ???????????? - fan_mod(dev_type=14)
        # ?????????3
        # ?????????4
        # ?????????5
        # ?????????0
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
        # 2: ???????????????(dev_type=8)
        # 4: ???????????????(dev_type=8)
        # 7: ??????(dev_type=14)
        # 1: ??????(dev_type=14)
        # 5: ??????(dev_type=14)
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
            json = await self.get_list()
            if ('error' in json) and (json['error'] != '0'):
                json = await self.get_list()
            devs = []
            for group in json['data']:
                for dev in group['devicesGroupItems']:
                    if not isinstance(dev, dict):
                        raise TypeError(f"{json}")
                    device_json_object = JSON.loads(dev['device_json_object'])

                    support_fan_mode = device_json_object.get('dirty_fan_mod', False)  # ????????????
                    support_heat_mode = device_json_object.get('dirty_heat_mode', False)  # ????????????
                    support_cool_mode = device_json_object.get('dirty_temp_cool', False)  # ????????????

                    status_onoff = int(device_json_object.get('status_onoff', 0))  # ?????????1   ?????????0
                    status = int(device_json_object.get('status', 2))
                    mode = 'cool' if (status == 1 or status == 5) else 'heat'
                    hvac_mode = HVAC_MODE_OFF
                    if status_onoff == 1:
                        hvac_mode = self._status2hvac_mode[status]

                    dev_entity = {
                        "SUPPORT_FAN_MODE": support_fan_mode,
                        "SUPPORT_HEAT_MODE": support_heat_mode,
                        "SUPPORT_COOL_MODE": support_cool_mode,
                        'mode': mode,  # ????????????????????????????????????
                        ATTR_HVAC_MODE: hvac_mode,  # ??????????????? ?????????????????????????????????
                        ATTR_CURRENT_TEMPERATURE: float(device_json_object.get('dis_temp')[1:]),  # ????????????
                        ATTR_TEMPERATURE: float(device_json_object.get('temp_' + mode)[1:]),  # ????????????
                        ATTR_AVAILABLE: dev.get('is_enabled'),
                        ATTR_MAX_TEMP: float(device_json_object.get('temp_' + mode + '_default_max', 'c30.0')[1:]),
                        # ????????????
                        ATTR_MIN_TEMP: float(device_json_object.get('temp_' + mode + '_default_min', 'c10.0')[1:]),
                        # ????????????
                        ATTR_NAME: dev.get('dis_dev_name'),  # ????????????
                        ATTR_ID: dev.get('mac')  # ???mac????????????id
                    }

                    if support_fan_mode:
                        dev_entity[ATTR_FAN_MODE] = self._num2fan_modes[
                            int(device_json_object.get('fan_mod', 0))]  # ????????????

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
            # ???????????????heat cool fan_only off
            if prop == ATTR_HVAC_MODE:
                if value == HVAC_MODE_OFF:
                    data['operation'] = JSON.dumps({
                        'status_onoff': '0'
                    }).replace(" ", "")
                else:
                    # todo ???????????????????????????????????????????????????????????????
                    data['operation'] = JSON.dumps({
                        'status_onoff': '1',
                        'status': self._hvac_mode2status[value]
                    }).replace(" ", "")
            # ????????????
            elif prop == ATTR_TEMPERATURE:
                data['operation'] = JSON.dumps({
                    'heat_mode': 0,
                    'temp_' + self.devs[index]['mode']: 'c%s' % value
                }).replace(" ", "")
            # ????????????
            elif prop == ATTR_FAN_MODE:
                data['operation'] = JSON.dumps({
                    'fan_mod': str(self._fan_modes2num[value])
                }).replace(" ", "")
            else:
                return False
            json = await self.request(CTRL_URL, JSON.dumps(data))
            _LOGGER.debug("Control device: prop=%s, data=%s, json=%s", prop, JSON.dumps(data), json)
            if json == {}:
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
                   'Content-Type': 'application/json'}
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
        _LOGGER.debug('start login')
        data = {
            "clientId": 1,
            "client_secret": "d0404a5b1b5d6b6a6db049d441804188",
            "username": self._username,
            "password": self._password,
            "oauth_type": self._type,
        }
        async with await session.post(AUTH_URL, headers=headers, data=JSON.dumps(data)) as r:
            json = await r.json()
        if 'error' in json:
            _LOGGER.error('login fail: %s', json['error'])
            return None

        _LOGGER.debug("Get token: %s", json['access_token'])
        self._token = json['access_token']
        self._token_type = json['token_type']

    async def get_house_id(self):
        session = self._hass.helpers.aiohttp_client.async_get_clientsession()
        headers = {'User-Agent': USER_AGENT, 'Authorization': "%s %s" % (self._token_type, self._token)}
        async with await session.get(HOUSE_URL, headers=headers) as r:
            json = await r.json()
        if 'error' in json:
            _LOGGER.error('get house_id fail: %s', json['error'])
            return None
        self._house_id = json['id']

    async def get_list(self):
        """get all the devices."""
        if self._token is None:
            await self.login()
        if self._house_id is None:
            await self.get_house_id()
        list_url = LIST_URL % self._house_id
        session = self._hass.helpers.aiohttp_client.async_get_clientsession()
        headers = {'User-Agent': USER_AGENT, 'Authorization': "%s %s" % (self._token_type, self._token),
                   'Content-Type': 'application/json'}
        async with await session.get(list_url, headers=headers) as r:
            res = await r.json()
            return res
