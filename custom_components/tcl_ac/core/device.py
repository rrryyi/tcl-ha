import json
import logging
from typing import List

from .attribute import TclAttribute, V1SpecAttributeParser

_LOGGER = logging.getLogger(__name__)


class TclDevice:
    _raw_data: dict
    _attributes: List[TclAttribute]
    _attribute_snapshot_data: dict

    def __init__(self, client, raw: dict):
        self._client = client
        self._raw_data = raw
        self._attributes = []
        self._attribute_snapshot_data = {}

    @property
    def id(self):
        return self._raw_data['deviceId']

    @property
    def name(self):
        return self._raw_data['nickName'] if 'nickName' in self._raw_data else self.id

    @property
    def type(self):
        return self._raw_data['category'] if 'category' in self._raw_data else None

    @property
    def product_key(self):
        return self._raw_data['productKey'] if 'productKey' in self._raw_data else None

    @property
    def is_online(self):
        return self._raw_data['isOnline'] if 'isOnline' in self._raw_data else None

    @property
    def is_control(self):
        return self._raw_data['weChatControl']

    @property
    def attributes(self) -> List[TclAttribute]:
        return self._attributes

    @property
    def attribute_snapshot_data(self) -> dict:
        return self._attribute_snapshot_data

    @property
    def client(self):
        return self._client

    def update_attribute_snapshot_data(self, new_data: dict):
        # 可以在这里添加数据验证逻辑
        self._attribute_snapshot_data = new_data

    def _inline_property_values(self) -> dict:
        """从 user_devices 响应内联的 identifiers 列表提取 {identifier: value}。
        快照接口返回不完整时，这里是传感器初始值的主要来源。"""
        values = {}
        for item in self._raw_data.get('identifiers') or []:
            if isinstance(item, dict) and item.get('identifier') is not None:
                values[str(item['identifier'])] = item.get('value')
        if values:
            _LOGGER.info(
                'Device %s got %d inline property values from user_devices',
                self.id, len(values)
            )
        return values

    async def async_init(self):
        # 解析Attribute
        # noinspection PyBroadException
        try:
            parser = V1SpecAttributeParser()
            attributes = await self._client.get_digital_model_from_cache(self)

            _LOGGER.info(
                'Device %s (productKey=%s) got %d raw attributes',
                self.id, self.product_key, len(attributes) if attributes else 0
            )

            seen_keys = set()
            for item in (attributes or []):
                try:
                    attr = parser.parse_attribute(item)
                    if attr:
                        # 云端物模型可能对同一 identifier 重复返回，只保留第一个
                        if attr.key in seen_keys:
                            _LOGGER.warning(
                                'Device %s duplicate attribute %s skipped',
                                self.id, attr.key
                            )
                            continue
                        seen_keys.add(attr.key)
                        self._attributes.append(attr)
                        _LOGGER.info(
                            'Device %s parsed: key=%s -> platform=%s',
                            self.id, attr.key, attr.platform
                        )
                    else:
                        _LOGGER.warning(
                            'Device %s attribute %s (type=%s) returned None',
                            self.id, item.get('identifier'), item.get('type')
                        )
                except Exception:
                    _LOGGER.exception(
                        "Tcl device %s attribute %s parsing error occurred",
                        self.id, item.get('name', item.get('identifier', 'unknown'))
                    )

            # 快照 = user_devices 内联值 + thing/status 接口结果（后者存在时覆盖同名键）
            snapshot_data = dict(self._inline_property_values())
            status_data = await self._client.get_device_snapshot_data(self.id)
            if isinstance(status_data, dict):
                snapshot_data.update(status_data)
            _LOGGER.debug(
                'device %s snapshot data fetch successful. data: %s',
                self.id,
                json.dumps(snapshot_data)
            )
            self._attribute_snapshot_data = snapshot_data

            # 物模型是按产品系列定义的，可能包含本机型实际不上报的属性（如 ambientLight）。
            # 以初始快照（内联 identifiers ∪ thing/status）为准过滤，
            # 与 TCL App 只显示实际会上报的属性一致，避免产生永远"未知"的实体。
            reported_keys = set(snapshot_data.keys())
            if reported_keys:
                kept = [a for a in self._attributes if a.key in reported_keys]
                dropped = [a.key for a in self._attributes if a.key not in reported_keys]
                if dropped:
                    _LOGGER.info(
                        'Device %s dropped %d attributes not reported by device: %s',
                        self.id, len(dropped), ', '.join(sorted(dropped))
                    )
                    self._attributes = kept

            self._dedupe_display_names()
        except Exception:
            _LOGGER.exception('Tcl device %s init failed', self.id)

    def _dedupe_display_names(self):
        """物模型的 title 不保证唯一（如新风三个属性都叫"新风"）。
        同一平台下显示名冲突时，附加 identifier 后缀以便区分。"""
        groups = {}
        for attr in self._attributes:
            groups.setdefault((attr.platform, attr.display_name), []).append(attr)

        for (platform, name), attrs in groups.items():
            if len(attrs) > 1:
                for attr in attrs:
                    attr._display_name = '{}（{}）'.format(name, attr.key)
                _LOGGER.info(
                    'Device %s has %d attributes named "%s" on %s, suffixed with identifier',
                    self.id, len(attrs), name, platform
                )

    def __str__(self) -> str:
        return json.dumps({
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'product_key': self.product_key,
            'is_online': self.is_online,
            'is_control': self.is_control
        })
