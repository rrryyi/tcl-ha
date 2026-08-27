from homeassistant.const import Platform

DOMAIN = 'tcl_ac'

SUPPORTED_PLATFORMS = [
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE
]

FILTER_TYPE_INCLUDE = 'include'
FILTER_TYPE_EXCLUDE = 'exclude'

# 登录方式
LOGIN_METHOD_TOKEN = 'token'
LOGIN_METHOD_PASSWORD = 'password'
LOGIN_METHOD_SMS = 'sms'