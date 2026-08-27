# TCL配置文件中设备属性的name并不唯一，identifier才是唯一的
# 用ATTR_NAME来存储需要替换的属性名称，也可以在这里修改描述不准确的属性名称，避免歧义
ATTR_NAME = {
    "newWindECOSwitch": "新风节能",
    "newWindAntiCondensation": "新风防凝露",
    "newWindDeodorize": "新风除味",
    "workMode": "模式",
    "verticalWind": "上下扫风",
    "selfCleanStatus": "蒸发器清洁状态",
    "filterAgePercentage": "净化滤芯",
    "screen": "灯光",
    "beepSwitch": "提示音",
    "sleep": "睡眠模式",
    "sleepTime": "睡眠时间",
    "targetTemperature": "温度",
    "roomSize": "房间大小",
    "windSpeedAutoSwitch": "风速自动",
    "windSpeedPercentage": "风速",
    "windSpeed7Gear": "七档风速",
    "antiMoldew": "干燥",
    "purifyDeodorizeSwitch": "净化除味",
    "powerSwitch": "电源开关",
    "ECO": "节能",
    "newWindPercentage": "新风风速",
    "newWindAutoSwitch": "新风风速自动",
    "newWindSwitch": "新风开关",
    "sensorTVOCLevel": "TVOC质量等级",
    "healthy": "健康模式",
    "selfLearn": "自学习",
    "selfClean": "蒸发器清洁",
    "PTC": "电辅热",
    "horizontalWind": "左右扫风",
    "softWind": "柔风",
    "lightSense": "光敏",
    "blueLightSwitch": "小蓝翼灯光",
    "horizontalDirection": "左右送风",
    "verticalDirection": "上下送风",
    # 诊断/状态类传感器命名（部分机型物模型会返回）
    "lightSenserStatus": "光敏状态",
    "PTCStatus": "电辅热状态",
    "currentTemperature": "当前温度",
    "internalUnitCoilTemperature": "内机盘管温度",
    "externalUnitCoilTemperature": "外机盘管温度",
    "externalUnitTemperature": "外机环境温度",
    "externalUnitExhaustTemperature": "外机排气温度",
    "internalUnitFanSpeed": "内机风机转速",
    "externalUnitFanSpeed": "外机风机转速",
    "externalUnitFanGear": "外机风档",
    "compressorFrequency": "压缩机频率",
    "externalUnitElectricCurrent": "外机电流",
    "externalUnitVoltage": "外机电压",
    "fourWayValveStatus": "四通阀状态",
    "errorCode": "故障码",
    "aiSmartControlSource": "AI控制来源",
    "airQuality": "空气质量",
}

def try_read_as_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value == '1'

    if isinstance(value, int):
        return value == 1

    raise ValueError('[{}]无法被转为bool'.format(value))

def get_key_by_value(d, value):
    for key, val in d.items():
        if val == value:
            try:
                return int(key)
            except ValueError:
                # 如果转换失败，返回原字符串
                return key
    return None  # 如果没有找到，返回None

