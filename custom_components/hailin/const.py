"""Constants for the HaiLin Climate integration."""

DOMAIN = "hailin"

AUTH_URL = "https://yunpan.hailin.com/user/v1/user/login"
HOUSE_URL = "https://yunpan.hailin.com/device/v1/device/house"
LIST_URL = "https://yunpan.hailin.com/device/v1/device/group/findUserGroup"
CTRL_URL = "https://yunpan.hailin.com/device/api/device/operationDevice"

CONF_TYPE = "type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TEMP_STEP = "temp_step"
CONF_SUPPORT_FAN = "support_fan"
CONF_SUPPORT_COOL = "support_cool"
CONF_SUPPORT_HEAT = "support_heat"
CONF_UPDATE_INTERVAL = "update_interval"

# 登录类型选项
LOGIN_TYPE_EMAIL = "email"
LOGIN_TYPE_PHONE = "mobile"

# 默认轮询时间（秒）
DEFAULT_UPDATE_INTERVAL = 300  # 5分钟
