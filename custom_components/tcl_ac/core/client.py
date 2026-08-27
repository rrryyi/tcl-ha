import asyncio
import base64
import json
import logging
import random
import ssl
import threading
import time
import uuid
from typing import List

import paho.mqtt.client as mqtt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util.ssl import client_context
from .device import TclDevice
from .event import EVENT_DEVICE_DATA_CHANGED, EVENT_GATEWAY_STATUS_CHANGED
from .event import fire_event
from ..ac.panel_config_fallback import get_fallback_attributes, merge_attributes

_LOGGER = logging.getLogger(__name__)

APP_ID = '55141607047147220'
APP_TENANT_ID = 'tcl'
APP_PLATFORM_ID = '16'
APP_SECRET = '48980a392dc2078cbda5b3035a084a7bcee34a69cace18baa715e61d790b01d4'
APP_THIRD_PARTY = 'wxed3f11c6ee178737'
APP_VERSION = '2.7.33'
APP_UUID = 'TCL+'
APP_PLATFORM_TYPE = 'MemberMiniProgram'
APP_ENCRYPT_VERSION = '2.0'

# iOS App 凭据 (登录用)
IOS_APP_ID = '28411606743791229'
IOS_APP_SECRET = '8f2538acdb620574bf334cd35114f7178c8e790bf216edb7ba749bd6f6d86b44'
IOS_TENANT_ID = 'TCLPLUS'
IOS_APP_VERSION = '2.6.1(1344)'
IOS_PLATFORM_TYPE = 'iOS'
IOS_STORE_UUID = 'TCL+'
IOS_USER_AGENT = 'TCLPlus/2.6.1 (iPhone; iOS 15.4.1; Scale/3.00)'
IOS_REPORT_STATE = '{"os":"iOS","osVersion":"15.4.1","appVersion":"2.6.1","deviceModel":"iPhone"}'

REFRESH_TOKEN_API = 'https://cn.account.tcl.com/auth/auth/refershToken'
LOGIN_API = 'https://cn.account.tcl.com/auth/auth/login'
QUICK_LOGIN_API = 'https://cn.account.tcl.com/auth/auth/quickLogin'
SMS_CAPTCHA_API = 'https://cn.account.tcl.com/captcha/captcha/new/smsCaptcha'
GET_USER_INFO_API = 'https://cn.account.tcl.com/user/user/getUserInfoByToken'
GET_DEVICES_API = 'https://io.zx.tcljd.com/v1/tclplus/weChat/user/user_devices'
GET_MQTT_CONFIG_API = 'https://io.zx.tcljd.com/v1/auth/service/loadBalance'
CONTROL_DEVICE_API = 'https://io.zx.tcljd.com/v1/control/property/{deviceId}'
DEVICE_STATUS_API = 'https://io.zx.tcljd.com/v1/thing/status'
GET_DIGITAL_MODEL_API = 'https://io.zx.tcljd.com/v1/tclplus/panel/rn-panel-config'
ELECTRICITY_SUMMARY_API = 'https://io.zx.tcljd.com/v1/ac/statistics/electricity/summary'


def random_str(length: int = 32) -> str:
    return ''.join(random.choice('abcdef1234567890') for _ in range(length))


class TokenInfo:

    def __init__(self, token: str, refresh_token: str):
        self._token = token
        self._refresh_token = refresh_token

    @property
    def token(self) -> str:
        return self._token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token


class TclClientException(Exception):
    pass


def get_token_exp(token: str):
    """解析 JWT 形式 accessToken 的 exp（过期时间戳）。非 JWT 返回 None。"""
    if not token or token.count('.') != 2:
        return None
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode('utf-8')).decode('utf-8'))
        exp = data.get('exp')
        return int(exp) if isinstance(exp, (int, float)) else None
    except Exception:
        return None


class TclClient:

    def __init__(self, hass: HomeAssistant, accountId: str, token: str):
        self._account_id = accountId
        self._token = token
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._user_id = None
        # 预创建 SSLContext 对象
        self.ssl_context = None  # 初始化为 None

    @property
    def token(self):
        return self._token

    @property
    def session(self):
        return self._session

    @property
    def hass(self):
        return self._hass

    async def initialize(self):
        """异步初始化 SSLContext"""
        self.ssl_context = await self._create_ssl_context()

    async def _create_ssl_context(self):
        context = await self.hass.async_add_executor_job(ssl.create_default_context)
        return context

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        """
        刷新token
        :return:
        """
        api_url = REFRESH_TOKEN_API + '?appId=' + APP_ID + '&accountId=' + self._account_id + '&tenantId=' + APP_TENANT_ID + '&appSecret=' + APP_SECRET

        api_headers = {
            "Host": "cn.account.tcl.com",
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": "iOS",
            "TCL-Authorization": self._token,
            "token": self._token,
            "EncryptVersion": APP_ENCRYPT_VERSION,
            "t-app-version": APP_VERSION,
            "t-store-uuid": APP_UUID,
            "User-Agent": "TCLPlus/2.6.1 (iPhone; iOS 15.4.1; Scale/3.00)",
            "Encrypt": "false",
            "refreshToken": refresh_token
        }

        async with self._session.get(url=api_url, headers=api_headers) as response:
            token_info = await response.json()
            if 'accessToken' in token_info:
                return TokenInfo(
                    token_info['accessToken'],
                    token_info['refreshToken']
                )
            else:
                raise TclClientException('接口返回异常: ' + str(token_info))

    async def get_user_info(self) -> dict:
        """
        根据token获取用户信息
        :return:
        """
        api_url = GET_USER_INFO_API + '?appId=' + APP_ID + '&tenantId=' + APP_TENANT_ID + '&appSecret=' + APP_SECRET

        api_headers = {
            "Host": "cn.account.tcl.com",
            "TCL-Authorization": self._token,
            "xweb_xhr": "1",
            "t-app-version": APP_VERSION,
            "t-store-uuid": APP_UUID,
            "t-platform-type": APP_PLATFORM_TYPE,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13)XWEB/13639",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Referer": "https://servicewechat.com/wxed3f11c6ee178737/243/page-frame.html"
        }
        async with self._session.get(url=api_url, headers=api_headers) as response:
            content = await response.json(content_type=None)
            if 'FAILED' in content['status']:
                raise TclClientException('Error getting user info, error: {}'.format(content['failCause']))
            userinfo = content['data']
            return {
                'accountId': userinfo['accountId'],
                'mobile': userinfo['phone'],
                'username': userinfo['username']
            }

    def _get_io_headers(self, content_type: str = "application/x-www-form-urlencoded;charset=utf-8") -> dict:
        """获取 io.zx.tcljd.com 通用的请求头"""
        return {
            "Host": "io.zx.tcljd.com",
            "accessToken": self._token,
            "t-app-version": APP_VERSION,
            "t-store-uuid": APP_UUID,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13)XWEB/13639",
            "Content-Type": content_type,
            "xweb_xhr": "1",
            "miniGramSetup": "1",
            "t-platform-type": APP_PLATFORM_TYPE,
            "Referer": "https://servicewechat.com/wxed3f11c6ee178737/243/page-frame.html"
        }

    async def get_mqtt_config(self) -> List[TclDevice]:
        """
        获取MQTT配置
        """
        api_headers = self._get_io_headers()
        async with self._session.get(url=GET_MQTT_CONFIG_API, headers=api_headers) as response:
            content = await response.json(content_type=None)
            self._assert_response_successful(content)
            return content['data']

    async def get_devices(self) -> List[TclDevice]:
        """
        获取设备列表
        """
        api_headers = self._get_io_headers()
        async with self._session.get(url=GET_DEVICES_API, headers=api_headers) as response:
            content = await response.json(content_type=None)
            self._assert_response_successful(content)

            devices = []
            for raw in content['data']:
                _LOGGER.debug('Device Info: {}'.format(raw))
                device = TclDevice(self, raw)
                # 暂时只支持微信小程序可控制设备
                if device.is_control == "1":
                    await device.async_init()
                    devices.append(device)
                # 后续若需支持其他设备需要适配APP下载的设备的配置包.zip文件，若有需要可自行扩充
            return devices

    async def get_digital_model(self, productKey: str) -> list:
        """
        获取设备attributes
        :param deviceId:
        :return:
        """
        api_url = GET_DIGITAL_MODEL_API + '?productKey=' + productKey

        api_headers = self._get_io_headers()
        async with self._session.get(url=api_url, headers=api_headers) as response:
            content = await response.json(content_type=None)
            self._assert_response_successful(content)
            if 'pages' not in content['data'] or 'home' not in content['data']['pages']:
                _LOGGER.warning("Device {} get digital model fail. response: {}".format(
                    productKey,
                    json.dumps(content, ensure_ascii=False)
                ))
                return []

            return content['data']['pages']['home']

    async def get_digital_model_from_cache(self, device: TclDevice) -> list:
        """
        获取设备 attributes。
        有本地 fallback 时：先请求 API（主），再用 fallback 补充缺失属性（合并去重）。
        无本地 fallback 时：走 HA Storage 缓存 → API 远程获取 逻辑。
        :param device:
        :return:
        """
        local_attrs = get_fallback_attributes(device.product_key)

        # 有本地 fallback：API 为主 + fallback 合并，不使用缓存
        if local_attrs:
            try:
                api_attrs = await self.get_digital_model(device.product_key)
            except Exception as e:
                _LOGGER.warning(
                    "Device %s API request failed (%s), using local fallback only (%d attributes)",
                    device.id, e, len(local_attrs)
                )
                api_attrs = []

            merged = merge_attributes(api_attrs, device.product_key)
            _LOGGER.info(
                "Device %s (productKey=%s) merged: API=%d, fallback=%d, merged=%d",
                device.id, device.product_key,
                len(api_attrs) if api_attrs else 0,
                len(local_attrs),
                len(merged)
            )
            return merged

        # 无本地 fallback：走缓存 + API 逻辑
        store = Store(self._hass, 1, 'tcl_ac/device_{}.json'.format(device.id))
        cache = None
        try:
            cache = await store.async_load()
            if isinstance(cache, str):
                raise RuntimeError('cache is invalid')
        except Exception:
            _LOGGER.warning("Device {} cache is invalid".format(device.id))
            await store.async_remove()
            cache = None

        if cache:
            _LOGGER.info("Device {} get digital model from cache successful".format(device.id))
            return cache['attributes']

        _LOGGER.info("Device {} get digital model from cache fail, attempt to obtain remotely".format(device.id))
        attributes = await self.get_digital_model(device.product_key)
        await store.async_save({
            'device': {
                'name': device.name,
                'type': device.type,
                'product_key': device.product_key,
                'is_online': device.is_online,
                'is_control': device.is_control
            },
            'attributes': attributes
        })

        return attributes

    async def get_device_snapshot_data(self, deviceId: str) -> dict:
        """
        获取指定设备最新的属性数据
        :param deviceId:
        :return:
        """
        api_headers = self._get_io_headers("application/json;charset=UTF-8")

        api_body = {"deviceId": deviceId}
        async with self._session.post(url=DEVICE_STATUS_API, headers=api_headers, json=api_body) as response:
            content = await response.json(content_type=None)
            self._assert_response_successful(content)
            if 'status' not in content['data']:
                _LOGGER.warning("Device {} get digital snapshot data fail. response: {}".format(
                    deviceId,
                    json.dumps(content, ensure_ascii=False)
                ))
                return {}
            status = content['data']['status']
            # 兼容列表形态: [{identifier: ..., value: ...}] → {identifier: value}
            if isinstance(status, list):
                return {
                    str(item['identifier']): item.get('value')
                    for item in status
                    if isinstance(item, dict) and 'identifier' in item
                }
            if not isinstance(status, dict):
                _LOGGER.warning("Device {} snapshot status has unexpected shape: {}".format(
                    deviceId, type(status).__name__
                ))
                return {}
            return status

    async def listen_devices(self, targetDevices: List[TclDevice], signal: threading.Event):
        """
        监听设备数据变化（使用MQTT协议）
        """
        process_id = str(uuid.uuid4())
        self._hass.data['current_listen_devices_process_id'] = process_id
        mqtt_config = await self.get_mqtt_config()
        # MQTT配置
        MQTT_HOST = "iotws-prod.tcliot.com"
        MQTT_PORT = 443
        USER_ID = mqtt_config['userId']
        self._user_id = USER_ID
        ACCESS_TOKEN = self._token
        DEVICE_LIST = [{'deviceId': device.id, 'productKey': device.product_key} for device in targetDevices]

        # 生成clientId
        random_str = str(random.randint(1000, 9999))
        timestamp = str(int(time.time() * 1000))
        CLIENT_ID = f"{USER_ID}@miniprogram@{random_str}{timestamp}"

        # 创建MQTT客户端（兼容 paho-mqtt 1.x 与 2.x：
        # 2.x 的 Client() 要求 callback_api_version 参数，传入 VERSION1 保持旧回调签名）
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id=CLIENT_ID,
                clean_session=True,
                protocol=mqtt.MQTTv311,
                transport="websockets",
            )
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=CLIENT_ID,
                                 clean_session=True,
                                 protocol=mqtt.MQTTv311,
                                 transport="websockets")

        # 设置认证信息
        client.username_pw_set(username=USER_ID, password=ACCESS_TOKEN)

        # 设置TLS/SSL
        if self.ssl_context is None:
            await self.initialize()
        await self.hass.async_add_executor_job(
            client.tls_set_context,
            self.ssl_context
        )

        # 设置WebSocket路径和自动重连
        client.ws_set_options(path="/mqtt")
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        # 回调函数定义（保持不变）
        def on_connect(client, userdata, flags, rc):
            _LOGGER.info(f"MQTT连接结果: {rc}")
            if rc == 0:
                _LOGGER.info("成功连接到MQTT服务器")
                # 订阅所有设备的状态
                for device in DEVICE_LIST:
                    device_id = device['deviceId']
                    product_key = device['productKey']
                    # 订阅设备属性状态
                    property_topic = f"/sys/{product_key}/{device_id}/thing/event/property/post"
                    client.subscribe(property_topic, qos=1)
                    _LOGGER.debug(f"已订阅设备属性主题: {property_topic}")

                    # 订阅设备上下线状态
                    status_topic = f"/sys/{product_key}/{device_id}/thing/event/+"
                    client.subscribe(status_topic, qos=1)
                    _LOGGER.debug(f"已订阅设备状态主题: {status_topic}")

                fire_event(self._hass, EVENT_GATEWAY_STATUS_CHANGED, {
                    'status': True
                })

        def on_message(client, userdata,msg):
            _LOGGER.debug(f"收到消息 主题:{msg.topic} 内容:{msg.payload.decode()}")

            # 处理不同类型的消息
            try:
                payload = json.loads(msg.payload.decode())

                # 处理设备属性消息
                if "/thing/event/property/post" in msg.topic:
                    # 从主题中提取设备ID
                    parts = msg.topic.split('/')
                    if len(parts) >= 4:
                        device_id = parts[3]
                        # _LOGGER.debug(f"设备 {device_id} 属性更新: {payload}")

                        # 提取属性值
                        if "params" in payload:
                            attributes = {}
                            for key, value in payload["params"].items():
                                attributes[key] = value['value']

                            # 触发设备数据变化事件
                            fire_event(self._hass, EVENT_DEVICE_DATA_CHANGED, {
                                'deviceId': device_id,
                                'attributes': attributes
                            })

                # 处理设备事件消息
                elif "/thing/event/pushnotice" in msg.topic:
                    if "params" in payload and "value" in payload["params"]:
                        event_value = payload["params"]["value"]

                        # 处理设备上下线事件
                        if "status" in event_value:
                            device_id = event_value.get("deviceId", "未知设备")
                            status = event_value["status"]
                            _LOGGER.info(f"设备 {device_id} 状态变更: {status}")
            except json.JSONDecodeError:
                _LOGGER.error(f"消息格式错误: {msg.payload.decode()}")
            except Exception as e:
                _LOGGER.exception(f"处理消息时出错: {e}")

        def on_disconnect(client, userdata, rc):
            _LOGGER.info(f"断开连接，状态码: {rc}")
            if rc != 0:
                _LOGGER.warning("意外断开连接")
                if process_id == self._hass.data['current_listen_devices_process_id']:
                    fire_event(self._hass, EVENT_GATEWAY_STATUS_CHANGED, {
                        'status': False
                    })

        # 设置回调函数
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        try:
            # 连接MQTT服务器
            # connect 是阻塞调用（DNS+TCP+TLS握手），必须放线程池执行，否则会卡住事件循环
            _LOGGER.info("正在连接到MQTT服务器...")
            await self.hass.async_add_executor_job(
                client.connect, MQTT_HOST, MQTT_PORT, 30
            )

            # 开始网络循环
            client.loop_start()

            # 保持程序运行，直到收到停止信号
            while not signal.is_set():
                await asyncio.sleep(1)

        except Exception as e:
            _LOGGER.exception(f"MQTT连接发生错误: {e}")
        finally:
            # 清理资源
            client.loop_stop()
            client.disconnect()
            if process_id == self._hass.data['current_listen_devices_process_id']:
                fire_event(self._hass, EVENT_GATEWAY_STATUS_CHANGED, {
                    'status': False
                })
            else:
                _LOGGER.debug('process_id not match, skip...')

            _LOGGER.info('listen device stopped.')

    @staticmethod
    async def send_command(session, token, deviceId: str, attributes: dict):
        api_url = CONTROL_DEVICE_API.format(deviceId=deviceId)
        api_headers = {
            "Host": "io.zx.tcljd.com",
            "accessToken": token,
            "t-app-version": APP_VERSION,
            "t-store-uuid": APP_UUID,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13)XWEB/13639",
            "Content-Type": "application/json;charset=UTF-8",
            "xweb_xhr": "1",
            "miniGramSetup": "1",
            "t-platform-type": APP_PLATFORM_TYPE,
            "Referer": "https://servicewechat.com/wxed3f11c6ee178737/243/page-frame.html"
        }
        r = str(int(random.random() * 1e5))
        i = str(int(time.time() * 1000))
        params = []
        for key, value in attributes.items():
            attr = {}
            attr[str(key)] = value
            params.append(attr)
        api_body = {
            "msgId": f"miniprogram_{r}_{i}",
            "source": "miniprogram",
            "version": "3.0.0",
            "params": params
        }
        async with session.post(url=api_url, headers=api_headers, json=api_body) as response:
            content = await response.json(content_type=None)
            # 云端拒绝可能不带回 traceId，不能只依赖 traceId 判断成败
            code = content.get('code')
            if response.status != 200 or (code is not None and str(code) not in ('200', '0')):
                _LOGGER.warning(
                    "控制命令被云端拒绝: deviceId=%s, http=%s, params=%s, response=%s",
                    deviceId, response.status, params,
                    json.dumps(content, ensure_ascii=False)
                )
                raise TclClientException('接口返回异常: ' + str(content.get('message', content)))
            _LOGGER.debug(
                "控制命令已下发: deviceId=%s, params=%s, response=%s",
                deviceId, params, json.dumps(content, ensure_ascii=False)
            )

    # ============================================================
    # 登录方法 (iOS App 凭据 + RSA 加密)
    # ============================================================

    def _build_login_headers(self) -> dict:
        """构建登录请求头"""
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": IOS_PLATFORM_TYPE,
            "uid": "",
            "Accept": "*/*",
            "cid": str(uuid.uuid4()).upper(),
            "Accept-Language": "zh-Hans-CN;q=1, zh-Hant-CN;q=0.9, en-CN;q=0.8",
            "token": "",
            "EncryptVersion": "2.0",
            "t-app-version": IOS_APP_VERSION,
            "t-store-uuid": IOS_STORE_UUID,
            "Encrypt": "true",
            "User-Agent": IOS_USER_AGENT,
            "t-application-name": "",
        }

    async def login_by_password(self, phone: str, password: str) -> dict:
        """密码登录"""
        from .crypto import md5_hash, encrypt_url_params, encrypt_body

        device_id = str(uuid.uuid4()).upper()
        params = {
            "deviceId": device_id,
            "password": md5_hash(password),
            "channel": IOS_STORE_UUID,
            "tenantId": IOS_TENANT_ID,
            "appSecret": IOS_APP_SECRET,
            "username": phone,
            "appId": IOS_APP_ID,
            "reportState": IOS_REPORT_STATE,
        }

        url = f"{LOGIN_API}?{encrypt_url_params(params)}"
        body = encrypt_body(params)
        headers = self._build_login_headers()

        async with self._session.post(url=url, headers=headers, data=body) as resp:
            result = await resp.json(content_type=None)
            if 'accessToken' not in result:
                raise TclClientException('登录失败: ' + str(result.get('message', result)))
            return {
                'accountId': result['accountId'],
                'accessToken': result['accessToken'],
                'refreshToken': result['refreshToken'],
            }

    async def send_sms_captcha(self, phone: str) -> None:
        """发送短信验证码"""
        from .crypto import encrypt_url_params, generate_sign, generate_nonce

        import time as _time
        base_params = {
            "appId": IOS_APP_ID,
            "appSecret": IOS_APP_SECRET,
            "tenantId": IOS_TENANT_ID,
            "timestamp": str(int(_time.time() * 1000)),
            "nonce": generate_nonce(),
            "mobile": phone,
            "bType": "LOGIN",
        }
        base_params["sign"] = generate_sign(base_params)

        url = f"{SMS_CAPTCHA_API}?{encrypt_url_params(base_params)}"
        headers = self._build_login_headers()

        async with self._session.get(url=url, headers=headers) as resp:
            result = await resp.json(content_type=None)
            status = result.get('status', '')
            code = result.get('code')
            if status != 'SUCCESS' and code not in (1, 200, 0, '1', '200', '0'):
                raise TclClientException('短信发送失败: ' + str(result.get('message', result)))

    async def login_by_sms(self, phone: str, code: str) -> dict:
        """验证码登录 (quickLogin)"""
        from .crypto import encrypt_url_params, encrypt_body

        device_id = str(uuid.uuid4()).upper()
        params = {
            "deviceId": device_id,
            "bType": "LOGIN",
            "appSecret": IOS_APP_SECRET,
            "username": phone,
            "appId": IOS_APP_ID,
            "tenantId": IOS_TENANT_ID,
            "validCode": code,
            "reportState": IOS_REPORT_STATE,
        }

        url = f"{QUICK_LOGIN_API}?{encrypt_url_params(params)}"
        body = encrypt_body(params)
        headers = self._build_login_headers()

        async with self._session.post(url=url, headers=headers, data=body) as resp:
            result = await resp.json(content_type=None)
            if 'accessToken' not in result:
                raise TclClientException('登录失败: ' + str(result.get('message', result)))
            return {
                'accountId': result['accountId'],
                'accessToken': result['accessToken'],
                'refreshToken': result['refreshToken'],
            }

    async def get_electricity_summary(self, deviceId: str, product_key: str, time_type: int = 1) -> dict:
        """
        获取设备电量统计
        :param deviceId: 设备ID
        :param product_key: 设备 productKey (作为请求头)
        :param time_type: 时间类型 (1=周, 2=月, 3=年)
        :return: API 原始 data 字段，包含 ecoDetails 和 workModeDetails
        """
        api_url = ELECTRICITY_SUMMARY_API + '?timeType=' + str(time_type)
        api_headers = self._get_io_headers()
        api_headers['productKey'] = product_key
        api_headers['deviceId'] = deviceId
        if self._user_id:
            api_headers['userId'] = self._user_id
        async with self._session.get(url=api_url, headers=api_headers) as response:
            content = await response.json(content_type=None)
            self._assert_response_successful(content)
            return content.get('data', {})

    @staticmethod
    def _assert_response_successful(resp):
        if 'traceId' in resp and str(resp['code']) not in ('200', '0'):
            raise TclClientException('接口返回异常: ' + resp['message'])
