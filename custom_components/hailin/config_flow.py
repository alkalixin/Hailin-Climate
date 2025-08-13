"""Config flow for HaiLin Climate integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from .const import (
    DOMAIN, 
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL,
    CONF_TYPE,
    CONF_TEMP_STEP,
    CONF_SUPPORT_FAN,
    CONF_SUPPORT_COOL,
    CONF_SUPPORT_HEAT,
    LOGIN_TYPE_EMAIL,
    LOGIN_TYPE_PHONE,
)
from .auth import HaiLinAuth

_LOGGER = logging.getLogger(__name__)

class HaiLinConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HaiLin Climate."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # 验证登录信息
                await self._test_credentials(user_input)
                
                # 创建配置条目
                return self.async_create_entry(
                    title=f"HaiLin Climate ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TYPE): vol.In({
                        LOGIN_TYPE_PHONE: "手机号",
                        LOGIN_TYPE_EMAIL: "邮件",
                    }),
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_TEMP_STEP, default=0.5): float,
                    vol.Optional(CONF_SUPPORT_FAN, default=False): bool,
                    vol.Optional(CONF_SUPPORT_COOL, default=False): bool,
                    vol.Optional(CONF_SUPPORT_HEAT, default=True): bool,
                    vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=10, max=3600)
                    ),
                }
            ),
            errors=errors,
        )

    async def _test_credentials(self, user_input: dict[str, any]) -> None:
        """Test credentials by attempting to login and get houses."""
        _LOGGER.info("Starting HaiLin credentials validation")
        
        auth = HaiLinAuth(self.hass)
        token = await auth.login(
            user_input[CONF_TYPE],
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD]
        )
        
        if not token:
            _LOGGER.error("Failed to validate HaiLin credentials for user: %s", user_input[CONF_USERNAME])
            raise InvalidAuth()
        
        _LOGGER.info("Successfully validated HaiLin credentials for user: %s", user_input[CONF_USERNAME])
        
        # 获取房屋列表
        houses = await auth.get_houses()
        if not houses:
            _LOGGER.error("No houses found for user: %s", user_input[CONF_USERNAME])
            raise InvalidAuth()
        
        _LOGGER.info("Found %d houses for user: %s", len(houses), user_input[CONF_USERNAME])
        for i, house in enumerate(houses):
            _LOGGER.debug("House %d: %s (ID: %s)", i, house.get("name", "Unknown"), house.get("house_id", "Unknown"))


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
