"""Support for HaiLin Climate devices."""

import json as JSON
import logging

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ID, ATTR_NAME, ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .auth import HaiLinAuth
from .const import CTRL_URL, DOMAIN, LIST_URL

_LOGGER = logging.getLogger(__name__)

ATTR_AVAILABLE = "available"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HaiLin Climate platform."""
    _LOGGER.info("Setting up HaiLin Climate platform")

    hailin = hass.data[DOMAIN][config_entry.entry_id]

    if not hailin.devs:
        _LOGGER.error("No HaiLin devices available")
        return

    hailin.devices = [HaiLinClimate(hailin, index) for index in range(len(hailin.devs))]
    _LOGGER.debug("Created %d HaiLin climate entities", len(hailin.devices))

    for index, device in enumerate(hailin.devices):
        mac = hailin.devs[index].get("mac", hailin.devs[index].get("id", "Unknown"))
        _LOGGER.info(
            "Device %d: %s (MAC: %s, unique_id: %s)",
            index,
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
        initial_device = hailin.devs[index] if index < len(hailin.devs) else {}
        self._device_key = initial_device.get("mac", initial_device.get("id", index))
        self._device_name = initial_device.get("name", f"HaiLin {index}")
        self._last_known_device = dict(initial_device)
        self.mode_enum = {
            HVACMode.COOL: HVACAction.COOLING,
            HVACMode.HEAT: HVACAction.HEATING,
            HVACMode.FAN_ONLY: HVACAction.FAN,
            HVACMode.OFF: HVACAction.OFF,
        }

    def _resolve_device(self):
        """Resolve the latest device payload using a stable device key."""
        for index, device in enumerate(self._hailin.devs):
            if device.get("mac", device.get("id")) == self._device_key:
                self._index = index
                self._last_known_device = device
                return device

        return None

    def _get_device(self, include_last_known=True):
        """Return the current device payload or the last known payload."""
        device = self._resolve_device()
        if device is not None:
            return device

        if include_last_known and self._last_known_device:
            return self._last_known_device

        return None

    @property
    def unique_id(self):
        """Return the unique ID of the device."""
        return self._device_key

    @property
    def name(self):
        """Return the name of the device."""
        device = self._get_device()
        return device.get("name", self._device_name) if device else self._device_name

    @property
    def available(self):
        """Return True if entity is available."""
        device = self._resolve_device()
        return device.get(ATTR_AVAILABLE, False) if device else False

    @property
    def supported_features(self):
        """Return the list of supported features."""
        supports = 0
        hvac_mode = self.get_value(ATTR_HVAC_MODE, HVACMode.OFF)

        if hvac_mode != HVACMode.FAN_ONLY:
            supports = supports | ClimateEntityFeature.TARGET_TEMPERATURE

        if self.get_value("SUPPORT_FAN_MODE", False) and (
            hvac_mode == HVACMode.FAN_ONLY or hvac_mode == HVACMode.COOL
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
        return self.mode_enum.get(
            self.get_value(ATTR_HVAC_MODE, HVACMode.OFF),
            HVACAction.OFF,
        )

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        return self.get_value(ATTR_HVAC_MODE, HVACMode.OFF)

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

        if self.get_value("SUPPORT_FAN_MODE", False):
            modes.append(HVACMode.FAN_ONLY)
        if self.get_value("SUPPORT_COOL_MODE", False):
            modes.append(HVACMode.COOL)
        if self.get_value("SUPPORT_HEAT_MODE", False):
            modes.append(HVACMode.HEAT)

        return list(dict.fromkeys(modes))

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self.get_value(ATTR_FAN_MODE)

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        if self.get_value("SUPPORT_FAN_MODE", False):
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

    def get_value(self, prop, default=None):
        """Get property value from device data."""
        device = self._get_device()
        if device is None:
            return default

        return device.get(prop, default)

    async def set_value(self, prop, value):
        """Set property value on device."""
        _LOGGER.debug("Setting %s to %s", prop, value)
        await self._hailin.control(self._device_key, prop, value)


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

    def _set_cached_availability(self, available: bool) -> None:
        """Update availability for cached devices."""
        for device in self.devs:
            device[ATTR_AVAILABLE] = available

    @staticmethod
    def _device_key(device: dict):
        """Return the stable key for a device payload."""
        return device.get("mac", device.get("id"))

    def _find_device(self, device_ref):
        """Resolve a device payload using index or stable key."""
        if isinstance(device_ref, int):
            if 0 <= device_ref < len(self.devs):
                return device_ref, self.devs[device_ref]
            return None, None

        for index, device in enumerate(self.devs):
            if self._device_key(device) == device_ref:
                return index, device

        return None, None

    @staticmethod
    def _parse_temperature(raw_value, default: float) -> float:
        """Parse temperatures returned by HaiLin payloads."""
        try:
            text = str(raw_value)
            if text.startswith("c"):
                text = text[1:]
            return float(text)
        except (TypeError, ValueError):
            return default

    async def async_update(self, time):
        """Update device data."""
        _LOGGER.debug("Scheduled update triggered at %s", time)
        await self.update_data()

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
                if not await self.login():
                    self._set_cached_availability(False)
                    return False
            else:
                _LOGGER.debug("Token available, skipping login")

            if not self.houses:
                _LOGGER.info("No houses available, fetching house information")
                if not await self.get_houses():
                    self._set_cached_availability(False)
                    return False
            else:
                _LOGGER.debug("Houses available: %d houses", len(self.houses))

            _LOGGER.debug("Fetching device lists from all houses")
            if not await self.get_all_devices():
                self._set_cached_availability(False)
                return False

            _LOGGER.info(
                "HaiLin data update completed successfully. Found %d devices",
                len(self.devs),
            )
            return True

        except Exception as err:
            _LOGGER.error("Failed to update HaiLin data: %s", str(err))
            _LOGGER.debug("Exception type: %s", type(err).__name__)
            import traceback

            _LOGGER.debug("Full traceback: %s", traceback.format_exc())
            self._set_cached_availability(False)
            return False

    async def control(self, device_ref, prop, value):
        """Control device via server."""
        _LOGGER.info(
            "control method called: device_ref=%s, prop=%s, value=%s (type: %s)",
            device_ref,
            prop,
            value,
            type(value),
        )
        try:
            device_index, device = self._find_device(device_ref)
            if device is None:
                _LOGGER.error("Device not found for reference %s", device_ref)
                return False

            device_name = device.get("name", "Unknown")
            device_mac = device.get("mac")

            if not device_mac:
                _LOGGER.error("Device MAC not found for reference %s", device_ref)
                return False

            _LOGGER.debug("Device: %s (MAC: %s)", device_name, device_mac)

            data = {"mac": device_mac}

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
                    hvac_mode_to_status = {
                        HVACMode.HEAT: 7,
                        HVACMode.COOL: 1,
                        HVACMode.FAN_ONLY: 5,
                    }
                    status = hvac_mode_to_status.get(value, 1)
                    _LOGGER.info(
                        "Turning device ON with mode: %s (status: %d)", value, status
                    )
                    data["operation"] = JSON.dumps(
                        {"status_onoff": "1", "status": status}
                    ).replace(" ", "")

            elif prop == ATTR_TEMPERATURE:
                current_mode = device.get("mode", "heat")
                data["operation"] = JSON.dumps(
                    {"heat_mode": 0, "temp_" + current_mode: "c%s" % value}
                ).replace(" ", "")

            elif prop == ATTR_FAN_MODE:
                fan_modes_to_num = {
                    FAN_AUTO: 0,
                    FAN_LOW: 3,
                    FAN_MEDIUM: 4,
                    FAN_HIGH: 5,
                }
                fan_num = fan_modes_to_num.get(value, 0)
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

                self.devs[device_index][prop] = value
                self.devs[device_index][ATTR_AVAILABLE] = True
                _LOGGER.debug("Updated local device data")

                for device_entity in self.devices:
                    if device_entity.unique_id == device_mac:
                        device_entity.async_write_ha_state()
                        _LOGGER.debug(
                            "Notified entity %s of control update", device_entity.name
                        )
                        break

                return True

            _LOGGER.error(
                "Control request failed for device %s, result: %s",
                device_name,
                result,
            )
            return False

        except KeyError as err:
            _LOGGER.error("Key error happens: %s", str(err))
            return False
        except Exception as err:
            _LOGGER.error(
                "Failed to control device reference %s: %s", device_ref, str(err)
            )
            _LOGGER.debug("Exception type: %s", type(err).__name__)
            import traceback

            _LOGGER.debug("Full traceback: %s", traceback.format_exc())
            return False

    async def login(self, time=None):
        """Login to HaiLin service."""
        if time is not None:
            _LOGGER.debug("Scheduled login triggered at %s", time)

        _LOGGER.info("Attempting to login to HaiLin service")

        token = await self.auth.login(self.type, self.username, self.password)
        if not token:
            _LOGGER.error("Failed to login to HaiLin for user: %s", self.username)
            return False

        _LOGGER.info("Successfully logged in to HaiLin for user: %s", self.username)
        return True

    async def get_houses(self):
        """Get all houses."""
        _LOGGER.info("Fetching houses from HaiLin service")
        houses = await self.auth.get_houses()
        if not houses:
            _LOGGER.error("Failed to get houses from HaiLin service")
            return False

        self.houses = houses
        _LOGGER.info(
            "Successfully got %d houses from HaiLin service", len(self.houses)
        )
        for index, house in enumerate(self.houses):
            _LOGGER.debug(
                "House %d: %s (ID: %s)",
                index,
                house.get("name", "Unknown"),
                house.get("house_id", "Unknown"),
            )

        return True

    def _build_device_entity(
        self,
        device: dict,
        device_json_object: dict,
        house_id,
        house_name,
        group_id,
        group_name,
        outer_device_name: str,
    ) -> dict:
        """Build a normalized device payload from HaiLin API data."""
        support_fan_mode = (
            device_json_object.get("dirty_fan_mod", False)
            if self.support_fan is None
            else self.support_fan
        )
        support_heat_mode = (
            device_json_object.get("dirty_heat_mode", False)
            if self.support_heat is None
            else self.support_heat
        )
        support_cool_mode = (
            device_json_object.get("dirty_temp_cool", False)
            if self.support_cool is None
            else self.support_cool
        )

        status_onoff = int(device_json_object.get("status_onoff", 0))
        status = int(device_json_object.get("status", 2))
        mode = "cool" if support_cool_mode else "heat"

        status_to_hvac_mode = {
            2: HVACMode.HEAT,
            4: HVACMode.HEAT,
            7: HVACMode.HEAT,
            1: HVACMode.COOL,
            5: HVACMode.FAN_ONLY,
        }

        hvac_mode = HVACMode.OFF
        if status_onoff == 1:
            hvac_mode = status_to_hvac_mode.get(status, HVACMode.OFF)

        num_to_fan_mode = {
            3: FAN_LOW,
            4: FAN_MEDIUM,
            5: FAN_HIGH,
            0: FAN_AUTO,
        }

        dev_entity = dict(device)
        dev_entity.update(
            {
                "SUPPORT_FAN_MODE": support_fan_mode,
                "SUPPORT_HEAT_MODE": support_heat_mode,
                "SUPPORT_COOL_MODE": support_cool_mode,
                "mode": mode,
                ATTR_HVAC_MODE: hvac_mode,
                ATTR_CURRENT_TEMPERATURE: self._parse_temperature(
                    device_json_object.get("dis_temp", "c20.0"), 20.0
                ),
                ATTR_TEMPERATURE: self._parse_temperature(
                    device_json_object.get("temp_" + mode, "c22.0"), 22.0
                ),
                ATTR_AVAILABLE: device.get("is_enabled", False),
                ATTR_MAX_TEMP: self._parse_temperature(
                    device_json_object.get("temp_" + mode + "_default_max", "c30.0"),
                    30.0,
                ),
                ATTR_MIN_TEMP: self._parse_temperature(
                    device_json_object.get("temp_" + mode + "_default_min", "c10.0"),
                    10.0,
                ),
                ATTR_NAME: outer_device_name,
                ATTR_ID: device.get("mac"),
                "mac": device.get("mac"),
                "dis_dev_name": outer_device_name,
                "house_id": house_id,
                "house_name": house_name,
                "group_id": group_id,
                "group_name": group_name,
                "device_json_object": device.get("device_json_object", "{}"),
                "status_onoff": status_onoff,
                "status": status,
            }
        )

        if support_fan_mode:
            dev_entity[ATTR_FAN_MODE] = num_to_fan_mode.get(
                int(device_json_object.get("fan_mod", 0)),
                FAN_AUTO,
            )

        return dev_entity

    async def get_all_devices(self):
        """Get device lists from all houses."""
        _LOGGER.info("Fetching device lists from all houses")

        if not self.houses:
            _LOGGER.error("No houses available, cannot fetch device lists")
            return False

        previous_devices_by_house = {}
        for cached_device in self.devs:
            previous_devices_by_house.setdefault(cached_device.get("house_id"), []).append(
                dict(cached_device)
            )

        all_devices = []
        successful_house_ids = set()
        failed_house_ids = set()

        for house in self.houses:
            house_id = house.get("house_id")
            house_name = house.get("name", "Unknown")

            if not house_id:
                _LOGGER.error("House ID not available for house: %s", house_name)
                failed_house_ids.add(house_id)
                continue

            _LOGGER.debug(
                "Fetching devices for house: %s (ID: %s)", house_name, house_id
            )

            url = f"{LIST_URL}?house_id={house_id}&of_all=0"
            _LOGGER.debug("Device list URL: %s", url)

            result = await self.auth.request(url, method="GET")
            if result and "data" in result:
                successful_house_ids.add(house_id)
                groups = result["data"]
                _LOGGER.info(
                    "Successfully got %d groups from house: %s",
                    len(groups),
                    house_name,
                )

                for group in groups:
                    group_name = group.get("group_name", "Unknown")
                    group_id = group.get("group_id")
                    _LOGGER.debug("Processing group: %s (ID: %s)", group_name, group_id)

                    devices = group.get("devicesGroupItems")
                    if not devices:
                        _LOGGER.warning("No devices found in group: %s", group_name)
                        continue

                    _LOGGER.info(
                        "Found %d devices in group: %s", len(devices), group_name
                    )

                    for device in devices:
                        outer_device_name = device.get("dis_dev_name", "Unknown")
                        device_json = device.get("device_json_object", "{}")
                        try:
                            device_json_object = JSON.loads(device_json)
                            dev_entity = self._build_device_entity(
                                device,
                                device_json_object,
                                house_id,
                                house_name,
                                group_id,
                                group_name,
                                outer_device_name,
                            )
                            all_devices.append(dev_entity)
                        except (JSON.JSONDecodeError, TypeError, ValueError) as err:
                            _LOGGER.warning(
                                "Failed to parse device JSON for device %s: %s",
                                outer_device_name,
                                str(err),
                            )
                            fallback_device = dict(device)
                            fallback_device.update(
                                {
                                    "name": outer_device_name,
                                    ATTR_AVAILABLE: device.get("is_enabled", False),
                                    "house_id": house_id,
                                    "house_name": house_name,
                                    "group_id": group_id,
                                    "group_name": group_name,
                                }
                            )
                            all_devices.append(fallback_device)

                        _LOGGER.debug(
                            "Device: %s (ID: %s, MAC: %s, Group: %s, House: %s)",
                            device.get("name", outer_device_name),
                            device.get("id", "Unknown"),
                            device.get("mac", "Unknown"),
                            group_name,
                            house_name,
                        )
            else:
                failed_house_ids.add(house_id)
                _LOGGER.error("Failed to get device list from house: %s", house_name)
                if result:
                    _LOGGER.debug("Device list response (no data): %s", result)
                else:
                    _LOGGER.debug("No response received from device list request")

        for house in self.houses:
            house_id = house.get("house_id")
            house_name = house.get("name", "Unknown")
            if house_id not in failed_house_ids:
                continue

            cached_house_devices = previous_devices_by_house.get(house_id, [])
            if not cached_house_devices:
                continue

            _LOGGER.warning(
                "Keeping %d cached devices for house %s because refresh failed",
                len(cached_house_devices),
                house_name,
            )
            for cached_device in cached_house_devices:
                cached_device[ATTR_AVAILABLE] = False
                all_devices.append(cached_device)

        if not successful_house_ids:
            _LOGGER.warning(
                "Failed to refresh any house device list, keeping %d cached devices",
                len(self.devs),
            )
            return False

        if not all_devices and self.devs:
            _LOGGER.warning(
                "Device refresh returned no devices, keeping %d cached devices",
                len(self.devs),
            )
            return False

        self.devs = all_devices
        _LOGGER.info("Total devices found across all houses: %d", len(self.devs))

        for index, device in enumerate(self.devs):
            _LOGGER.debug(
                "Device %d: %s - HVAC Mode: %s, Current Temp: %s, Target Temp: %s, Available: %s",
                index,
                device.get("name", "Unknown"),
                device.get(ATTR_HVAC_MODE, "Unknown"),
                device.get(ATTR_CURRENT_TEMPERATURE, "Unknown"),
                device.get(ATTR_TEMPERATURE, "Unknown"),
                device.get(ATTR_AVAILABLE, "Unknown"),
            )

        return True
