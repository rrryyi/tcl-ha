import asyncio
import logging
import threading
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, SUPPORTED_PLATFORMS, FILTER_TYPE_EXCLUDE, FILTER_TYPE_INCLUDE
from .core.attribute import TclAttribute
from .core.client import TclClient, EVENT_DEVICE_DATA_CHANGED, TclClientException, TokenInfo, get_token_exp
from .core.config import AccountConfig, DeviceFilterConfig, EntityFilterConfig
from .core.device import TclDevice
from typing import List
from .core.event import fire_event
_LOGGER = logging.getLogger(__name__)

# token 剩余有效期低于该秒数时提前刷新，避免用到过期才失败
TOKEN_REFRESH_MARGIN = 1800


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {
        'devices': [],
        'signals': []
    })

    await try_update_token(hass, entry)
    # 定时更新token
    token_signal = threading.Event()
    hass.async_create_background_task(token_updater(hass, entry, token_signal), 'tcl-token-updater')
    hass.data[DOMAIN]['signals'].append(token_signal)

    account_cfg = AccountConfig(hass, entry)
    client = TclClient(hass, account_cfg.account_id, account_cfg.token)
    devices = await client.get_devices()
    _LOGGER.debug('共获取到{}个设备'.format(len(devices)))

    hass.data[DOMAIN]['devices'] = devices

    # 监听设备数据
    device_signal = threading.Event()
    hass.async_create_background_task(client.listen_devices(devices, device_signal), 'tcl-device-data')
    hass.data[DOMAIN]['signals'].append(device_signal)
    #轮训获取数据,已废弃
    # device_updater_signal = threading.Event()
    # hass.async_create_background_task(data_updater(hass,account_cfg,client,devices,device_updater_signal), 'tcl-device-data-updater')
    # hass.data[DOMAIN]['signals'].append(device_updater_signal)

    await hass.config_entries.async_forward_entry_setups(entry, SUPPORTED_PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    return True

# async def data_updater(hass: HomeAssistant,config: AccountConfig,client: TclClient,targetDevices: List[TclDevice], signal: threading.Event):
#     """
#     每5分钟刷新一次空调数据
#     :param hass:
#     :param entry:
#     :param signal:
#     :return:
#     """
#     while not signal.is_set():
#         refresh_data_time=config.refresh_data_time
#         if refresh_data_time>0:
#             for device in targetDevices:
#                 device_id = device.id
#                 newdata=await client.get_device_snapshot_data(device_id)
#                 # 触发设备数据变化事件
#                 fire_event(hass, EVENT_DEVICE_DATA_CHANGED, {
#                     'deviceId': device_id,
#                     'attributes': newdata
#                 })
#         refresh_data_time if refresh_data_time > 1 else 1
#         await asyncio.sleep(refresh_data_time*60)

async def token_updater(hass: HomeAssistant, entry: ConfigEntry, signal: threading.Event):
    """
    每1小时检查一次token有效性，若token刷新则重载集成
    """
    while not signal.is_set():
        try:
            if await try_update_token(hass, entry):
                _LOGGER.info('token refreshed, reload integration...')
                await hass.config_entries.async_reload(entry.entry_id)
                break
            else:
                _LOGGER.debug('token is valid')
        except TclClientException as e:
            _LOGGER.warning('Token刷新失败，请在集成设置中重新配置账号: %s', e)

        await asyncio.sleep(3600)


async def try_update_token(hass: HomeAssistant, entry: ConfigEntry):
    """
    尝试刷新token，刷新成功返回True
    """
    cfg = AccountConfig(hass, entry)
    client = TclClient(hass, cfg.account_id, cfg.token)

    # 优先用 JWT 自带的过期时间判断，剩余有效期充足则无需请求
    exp = get_token_exp(cfg.token)
    if exp is not None and exp - time.time() > TOKEN_REFRESH_MARGIN:
        return False

    # 解析不出过期时间（非 JWT token）时，退回用 get_user_info 探测有效性
    if exp is None:
        try:
            await client.get_user_info()
            return False
        except TclClientException:
            pass  # token无效，尝试刷新

    token_info = await client.refresh_token(cfg.refresh_token)
    cfg.token = token_info.token
    cfg.refresh_token = token_info.refresh_token
    cfg.expires_at = get_token_exp(token_info.token) or 0
    cfg.save()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    for platform in SUPPORTED_PLATFORMS:
        if not await hass.config_entries.async_forward_entry_unload(entry, platform):
            return False

    for signal in hass.data[DOMAIN]['signals']:
        signal.set()

    del hass.data[DOMAIN]

    return True


async def entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.debug('reload tcl integration...')
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(hass: HomeAssistant, config: ConfigEntry, device: DeviceEntry) -> bool:
    device_id = list(device.identifiers)[0][1]

    _LOGGER.info('Device [{}] removing...'.format(device_id))

    for dev in hass.data[DOMAIN]['devices']:
        if dev.id.lower() == device_id:
            target_device = dev
            break
    else:
        _LOGGER.error('Device [{}] not found'.format(device_id))
        return False

    cfg = DeviceFilterConfig(hass, config)
    if cfg.filter_type == FILTER_TYPE_EXCLUDE:
        cfg.add_device(target_device.id)
    else:
        cfg.remove_device(target_device.id)

    cfg.save()

    _LOGGER.info('Device [{}] removed'.format(device_id))

    return True


async def async_register_entity(hass: HomeAssistant, entry: ConfigEntry, async_add_entities, platform, setup) -> None:
    entities = []
    for device in hass.data[DOMAIN]['devices']:
        if DeviceFilterConfig.is_skip(hass, entry, device.id):
            continue

        for attribute in device.attributes:
            if attribute.platform != platform:
                continue

            if EntityFilterConfig.is_skip(hass, entry, device.id, attribute.key):
                continue

            entities.append(setup(device, attribute))

    async_add_entities(entities)
