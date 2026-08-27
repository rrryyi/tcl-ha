import logging
from abc import ABC, abstractmethod

from homeassistant.const import Platform
from homeassistant.core import Event
from homeassistant.helpers.entity import DeviceInfo, Entity

from . import DOMAIN
from .core.attribute import TclAttribute
from .core.client import TclClient, TclClientException
from .core.device import TclDevice
from .core.event import EVENT_DEVICE_DATA_CHANGED, EVENT_GATEWAY_STATUS_CHANGED, EVENT_DEVICE_CONTROL
from .core.event import listen_event, fire_event
from .core import rules
import asyncio

_LOGGER = logging.getLogger(__name__)


class TclAbstractEntity(Entity, ABC):
    _device: TclDevice
    _client: TclClient
    _attribute: TclAttribute

    def __init__(self, device: TclDevice, attribute: TclAttribute):
        self._attr_unique_id = '{}.{}_{}'.format(DOMAIN, device.id, attribute.key).lower()
        # entity_id 使用正确的平台域（switch/select/number/sensor/climate），
        # 避免旧版使用 tcl.xxx 非法域被 HA 纠正后产生不一致。
        self.entity_id = '{}.{}_{}'.format(attribute.platform.value, device.id, attribute.key).lower()
        self._attr_should_poll = False

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id.lower())},
            name=device.name,
            manufacturer='TCL',
            model=device.product_key
        )

        self._attr_name = attribute.display_name
        for key, value in attribute.options.items():
            setattr(self, '_attr_' + key, value)

        self._device = device
        self._client = device.client
        self._attribute = attribute
        # 保存当前设备下所有attribute的数据
        self._attributes_data = {}
        # 取消监听回调
        self._listen_cancel = []
        # 可用性来源：网关连接状态 + App 面板禁用规则（climate 实体不受禁用规则约束，需保持可控）
        self._gateway_ok = True
        self._rule_disabled = False
        self._check_disable_rules = attribute.platform != Platform.CLIMATE

    def _send_command(self, attributes):
        """
        发送控制命令。
        会按 TCL App 面板的联动规则附带额外属性（如切模式时清理 ECO/睡眠/电辅热），
        且只附带当前设备物模型中存在的属性，避免下发设备不认识的参数。
        """
        merged = dict(attributes)
        allowed_keys = {attr.key for attr in self._device.attributes}
        linked = rules.linked_attributes(attributes, self._device.attribute_snapshot_data)
        for key, value in linked.items():
            if key in allowed_keys and key not in merged:
                merged[key] = value
        if len(merged) != len(attributes):
            _LOGGER.debug('entity [%s] command %s expanded by link rules to %s',
                          self._attr_unique_id, attributes, merged)

        fire_event(self.hass, EVENT_DEVICE_CONTROL, {
            'entityId': self.entity_id,
            'deviceId': self._device.id,
            'attributes': merged
        })

    def _apply_availability(self):
        self._attr_available = self._gateway_ok and not self._rule_disabled

    @abstractmethod
    def _update_value(self):
        pass

    async def async_added_to_hass(self) -> None:
        # 监听状态
        def status_callback(event):
            self._gateway_ok = bool(event.data['status'])
            self._apply_availability()
            self.schedule_update_ha_state()

        self._listen_cancel.append(listen_event(self.hass, EVENT_GATEWAY_STATUS_CHANGED, status_callback))

        # 监听数据变化事件
        def data_callback(event):
            if event.data['deviceId'] == self._device.id:
                self._attributes_data = event.data['attributes']
                device_data = self._device.attribute_snapshot_data
                for key, value in event.data['attributes'].items():
                    device_data[str(key)] = value
                self._device.update_attribute_snapshot_data(device_data)
            self._refresh_rule_state()
            self._update_value()
            self.schedule_update_ha_state()

        self._listen_cancel.append(listen_event(self.hass, EVENT_DEVICE_DATA_CHANGED, data_callback))
        # 填充快照值
        data_callback(Event('', data={
            'deviceId': self._device.id,
            'attributes': self._device.attribute_snapshot_data
        }))

        # 监听事件总线来的控制命令
        async def control_callback(e):
            #每个实体都会注册该事件，目前根据entityId进行判断防治多次操作
            if self.entity_id == e.data['entityId']:
                try:
                    await self._client.send_command(
                        self._client.session, self._client.token,
                        e.data['deviceId'], e.data['attributes']
                    )
                except TclClientException as ex:
                    _LOGGER.warning('entity [%s] 控制命令发送失败: %s (attributes=%s)',
                                    self.entity_id, ex, e.data['attributes'])
                    return
                # 直接刷新属性状状
                device_data = self._device.attribute_snapshot_data
                for key, value in e.data['attributes'].items():
                    device_data[str(key)] = value
                self._attributes_data = device_data
                self._refresh_rule_state()
                self._update_value()
                self.schedule_update_ha_state()
        self._listen_cancel.append(listen_event(self.hass, EVENT_DEVICE_CONTROL, control_callback))

    def _refresh_rule_state(self):
        """根据面板禁用规则刷新实体的可用性（模拟 App 在特定工况下置灰控件）"""
        if self._check_disable_rules:
            self._rule_disabled = rules.is_disabled(
                self._attribute.key, self._device.attribute_snapshot_data
            )
        self._apply_availability()

    async def async_will_remove_from_hass(self) -> None:
        for cancel in self._listen_cancel:
            cancel()
