import logging
from abc import abstractmethod, ABC

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import Platform

from ..helpers import ATTR_NAME

_LOGGER = logging.getLogger(__name__)

# 已确认的只读属性，应解析为 SENSOR 而非 NUMBER/SELECT/SWITCH
READONLY_SENSOR_KEYS = {
    'filterAgePercentage',
    'selfCleanStatus',
    'lightSenserStatus',   # 光敏检测状态（TCL 官方拼写即为 Senser）
    'sleepTime',
    'windSpeed7Gear',
    'errorCode',
    'aiSmartControlSource',
    'tslLatestVersion',
    'tslReqVersion',
    'tslQueryTime',
    'currentTemperature',
    'roomTemperature',
    # 以下为空调诊断类只读属性（数值/枚举都应作为传感器展示，不能作为可写 Number/Select）
    'internalUnitCoilTemperature',
    'externalUnitCoilTemperature',
    'externalUnitTemperature',
    'externalUnitExhaustTemperature',
    'internalUnitFanSpeed',
    'externalUnitFanSpeed',
    'externalUnitFanGear',
    'compressorFrequency',
    'externalUnitElectricCurrent',
    'externalUnitVoltage',
    'expansionValve',
}

# 温度类只读传感器，设置 TEMPERATURE 设备类
TEMPERATURE_SENSOR_KEYS = {
    'currentTemperature',
    'roomTemperature',
    'internalUnitCoilTemperature',
    'externalUnitCoilTemperature',
    'externalUnitTemperature',
    'externalUnitExhaustTemperature',
}

# 部分诊断传感器在物模型 specs 中可能不包含 unit，这里补充单位
SENSOR_UNIT_BY_KEY = {
    'internalUnitFanSpeed': 'rpm',
    'externalUnitFanSpeed': 'rpm',
    'compressorFrequency': 'Hz',
    'externalUnitElectricCurrent': 'A',
    'externalUnitVoltage': 'V',
}

# bool 类型的只读状态位默认按此表翻译
DEFAULT_BOOL_TABLE = {'0': '关', '1': '开'}


def is_readonly_key(identifier: str) -> bool:
    """TCL 物模型约定 *Status 后缀为只读状态位（如 selfCleanStatus、PTCStatus）"""
    if not identifier:
        return False
    return identifier in READONLY_SENSOR_KEYS or identifier.endswith('Status')


class TclAttribute:

    def __init__(self, key: str, display_name: str, platform: Platform, options: dict = None, ext: dict = None):
        self._key = key
        self._display_name = display_name
        self._platform = platform
        self._options = options if options is not None else {}
        self._ext = ext if ext is not None else {}

    @property
    def key(self) -> str:
        return self._key

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def platform(self) -> Platform:
        return self._platform

    @property
    def options(self) -> dict:
        return self._options

    @property
    def ext(self) -> dict:
        return self._ext


class TclAttributeParser(ABC):

    @abstractmethod
    def parse_attribute(self, attribute: dict) -> TclAttribute:
        pass

class V1SpecAttributeParser(TclAttributeParser, ABC):

    def parse_attribute(self, attribute: dict) -> TclAttribute:
        identifier = attribute.get('identifier')
        data_type = attribute.get('type', '')

        # 结构体 → 传感器（先于只读判断，结构体有自己的解析逻辑）
        if 'struct' in data_type:
            return self._parse_as_sensor(attribute)

        # 只读属性（*Status 后缀或已知集合）→ 传感器，避免生成"能看不能控"的假开关
        if is_readonly_key(identifier):
            return self._parse_as_simple_sensor(attribute)

        # 按钮处理
        if 'bool' in data_type:
            return self._parse_as_switch(attribute)
        # 模式选择
        if 'enum' in data_type:
            return self._parse_as_select(attribute)
        # 数值类型
        if 'int' in data_type or 'double' in data_type or 'float' in data_type:
            return self._parse_as_number(attribute)

        return None

    @staticmethod
    def _parse_as_simple_sensor(attribute):
        """将只读属性解析为简单传感器（enum/bool/int，非结构体）"""
        data_type = attribute['type']
        specs = attribute.get('specs', {})
        ext = {'sensor_type': 'simple'}
        options = {}

        if 'enum' in data_type or 'bool' in data_type:
            # enum 的 specs 是 {值: 名称} 映射；bool 的 specs 是 {"0": "关", "1": "开"}
            value_comparison_table = {}
            if isinstance(specs, dict) and specs:
                for key, value in specs.items():
                    value_comparison_table[str(key)] = value
            if not value_comparison_table:
                value_comparison_table = dict(DEFAULT_BOOL_TABLE)
            options = {
                'device_class': SensorDeviceClass.ENUM,
                'options': list(value_comparison_table.values())
            }
            ext['value_comparison_table'] = value_comparison_table
        elif 'int' in data_type or 'double' in data_type or 'float' in data_type:
            unit = specs.get('unit') or SENSOR_UNIT_BY_KEY.get(attribute['identifier'])
            options['native_unit_of_measurement'] = unit
            if attribute['identifier'] in TEMPERATURE_SENSOR_KEYS:
                options['device_class'] = SensorDeviceClass.TEMPERATURE
            ext['unit'] = unit or ''

        return TclAttribute(
            attribute['identifier'],
            ATTR_NAME.get(attribute['identifier'], attribute['title']),
            Platform.SENSOR,
            options,
            ext
        )

    @staticmethod
    def _parse_as_sensor(attribute):
        options = {}
        ext = {}
        value_comparison_table = {}

        # 保存结构体的整体信息
        ext['struct_info'] = {
            'title': attribute['title'],
            'description': attribute.get('description', ''),
            'function': attribute.get('function', '')
        }

        for item in attribute['specs']:
            data_type = item['dataType']['type']
            data_id = item['identifier']
            data_opthons = {}
            data_ext = {
                'name': item['name']  # 保存字段的中文名称
            }
            data_value_comparison_table = {}

            # 处理枚举类型
            if 'enum' in data_type:
                for key, value in item['dataType']['specs'].items():
                    data_value_comparison_table[str(key)] = value
                data_opthons['device_class'] = SensorDeviceClass.ENUM
                data_opthons['options'] = list(data_value_comparison_table.values())
                data_ext['value_comparison_table'] = data_value_comparison_table

            # 处理数值类型
            if 'int' in data_type or 'double' in data_type or 'float' in data_type:
                specs = item['dataType']['specs']
                data_opthons = {
                    'native_min_value': float(specs.get('min', 0)),
                    'native_max_value': float(specs.get('max', 100)),
                    'native_step': float(specs.get('step', 1))
                }

                # 添加单位信息
                if 'unit' in specs:
                    data_opthons['native_unit_of_measurement'] = specs['unit']
                    data_ext['unit'] = specs['unit']
                    if 'unitName' in specs:
                        data_ext['unit_name'] = specs['unitName']

            # 保存映射类型信息
            if 'mappingType' in item['dataType']:
                data_ext['mapping_type'] = item['dataType']['mappingType']

            options[str(data_id)] = data_opthons
            ext[str(data_id)] = data_ext
            value_comparison_table[str(data_id)] = data_value_comparison_table

        return TclAttribute(attribute['identifier'], ATTR_NAME.get(attribute['identifier'],attribute['title']), Platform.SENSOR, options, ext)

    @staticmethod
    def _parse_as_number(attribute):
        specs = attribute.get('specs', {})
        unit = specs.get('unit')
        options = {
            'native_min_value': float(specs.get('min', 0)),
            'native_max_value': float(specs.get('max', 100)),
            'native_unit_of_measurement': unit,
            'native_step': float(specs.get('step', 1))
        }

        return TclAttribute(attribute['identifier'], ATTR_NAME.get(attribute['identifier'],attribute['title']), Platform.NUMBER, options)

    @staticmethod
    def _parse_as_select(attribute):
        value_comparison_table = {}
        optionslist = []
        for key, value in attribute['specs'].items():
            value_comparison_table[str(key)] = value
            optionslist.append(value)

        ext = {
            # 键统一转 str，与 select/sensor 读取时的 str(value) 查找保持一致
            'value_comparison_table': value_comparison_table
        }

        options = {
            'options': optionslist
        }

        return TclAttribute(attribute['identifier'], ATTR_NAME.get(attribute['identifier'],attribute['title']), Platform.SELECT, options, ext)

    @staticmethod
    def _parse_as_switch(attribute):
        options = {
            'device_class': SwitchDeviceClass.SWITCH
        }

        return TclAttribute(attribute['identifier'], ATTR_NAME.get(attribute['identifier'],attribute['title']), Platform.SWITCH, options)
