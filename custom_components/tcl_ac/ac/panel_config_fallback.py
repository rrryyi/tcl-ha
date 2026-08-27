"""
TCL 空调面板物模型 fallback 数据。

当 API (rn-panel-config) 返回的属性列表不完整时，
使用此本地数据补充缺失的属性定义。

数据来源: TCL Plus App RN 插件包 2ed0bf34 (productKey: 1112017519N) 的 config.json
"""

PANEL_CONFIG_FALLBACK = {
    "1112017519N": [
        {"function": "powerSwitch", "identifier": "powerSwitch", "title": "电源开关", "description": "", "type": "bool", "specs": {"1": "开机", "0": "关机"}, "uiComponent": "UISwitch"},
        {"function": "targetTemperature", "identifier": "targetTemperature", "title": "温度", "description": "", "type": "int", "specs": {"min": 16, "max": 31, "step": 0.5, "unit": "℃"}, "uiComponent": "UISwitch"},
        {"function": "newWind", "identifier": "newWindSwitch", "title": "新风", "description": "", "type": "bool", "specs": {"0": "关", "1": "开"}, "uiComponent": "UISwitch"},
        {"function": "newWind", "identifier": "newWindPercentage", "title": "新风", "description": "", "type": "int", "specs": {"min": 1, "max": 100, "step": 1, "unit": "%"}, "uiComponent": "UISwitch"},
        {"function": "newWind", "identifier": "newWindAutoSwitch", "title": "新风", "description": "", "type": "bool", "specs": {"0": "关", "1": "开"}, "uiComponent": "UISwitch"},
        {"function": "workMode", "identifier": "workMode", "title": "模式", "description": "", "type": "enum", "specs": {"1": "制冷", "4": "制热", "2": "除湿", "3": "送风", "0": "自动"}, "uiComponent": "UISwitch"},
        {"function": "windSpeed", "identifier": "windSpeedAutoSwitch", "title": "风速", "description": "", "type": "bool", "specs": {"0": "关", "1": "开"}, "uiComponent": "UISwitch"},
        {"function": "windSpeed", "identifier": "windSpeedPercentage", "title": "风速百分比", "description": "", "type": "int", "specs": {"min": 1, "max": 100, "step": 1, "unit": "%"}, "uiComponent": "UISwitch"},
        {"function": "softWind", "identifier": "softWind", "title": "柔风", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "ECO", "identifier": "ECO", "title": "节能", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "newWindECOSwitch", "identifier": "newWindECOSwitch", "title": "新风节能", "description": "夜间室内环境温度达到舒适区时关闭空调外机，并保持新风继续维护室内舒适度", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "blueLightSwitch", "identifier": "blueLightSwitch", "title": "小蓝翼灯光", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "PTC", "identifier": "PTC", "title": "电辅热", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "lightSense", "identifier": "lightSense", "title": "光敏", "description": "自动调节灯光亮度和提示音大小", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "beepSwitch", "identifier": "beepSwitch", "title": "提示音", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "screen", "identifier": "screen", "title": "灯光", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "sleep", "identifier": "sleep", "title": "睡眠模式", "description": "", "type": "enum", "specs": {"1": "标准", "3": "儿童", "2": "老人", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "purifyDeodorizeSwitch", "identifier": "purifyDeodorizeSwitch", "title": "净化除味", "description": "监测空气质量，智能开启新风", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "selfClean", "identifier": "selfClean", "title": "蒸发器清洁", "description": "", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "selfCleanStatus", "identifier": "selfCleanStatus", "title": "蒸发器清洁状态", "description": "", "type": "enum", "specs": {"0": "凝露", "1": "结霜", "2": "除霜", "3": "风干", "4": "失败", "5": "成功", "6": "未启动"}, "uiComponent": "UISwitch"},
        {"function": "antiMoldew", "identifier": "antiMoldew", "title": "干燥", "description": "自动吹干空调内的水汽，保持干燥，防止潮湿而发生霉变", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "selfLearn", "identifier": "selfLearn", "title": "自学习", "description": "在空调开机时，根据用户习惯自动控制空调", "type": "bool", "specs": {"1": "开", "0": "关"}, "uiComponent": "UISwitch"},
        {"function": "horizontalDirection", "identifier": "horizontalDirection", "title": "左右送风", "description": "", "type": "enum", "specs": {"1": "左右扫风", "2": "左中扫风", "3": "中扫风", "4": "右中扫风", "8": "送风关闭", "9": "送风", "10": "偏左风", "11": "中风", "12": "偏右风", "13": "右风"}, "uiComponent": "UISwitch"},
        {"function": "verticalDirection", "identifier": "verticalDirection", "title": "上下送风", "description": "", "type": "enum", "specs": {"1": "上下扫风", "2": "上中扫风", "3": "中下扫风", "8": "送风关闭", "9": "上风", "10": "偏上风", "11": "中风", "12": "偏下风", "13": "下风"}, "uiComponent": "UISwitch"},
        {"function": "filterAgePercentage", "identifier": "filterAgePercentage", "title": "净化滤芯", "description": "", "type": "int", "specs": {"min": 0, "max": 100, "step": 1, "unit": "%"}, "uiComponent": "UISwitch"},
        {"function": "roomSize", "identifier": "roomSize", "title": "房间大小", "description": "", "type": "int", "specs": {"min": 0, "max": 100, "step": 1, "unit": "㎡"}, "uiComponent": "UISwitch"}
    ]
}


def get_fallback_attributes(product_key: str) -> list:
    """获取指定 productKey 的 fallback 属性列表"""
    return PANEL_CONFIG_FALLBACK.get(product_key, [])


def merge_attributes(api_attributes: list, product_key: str) -> list:
    """
    将 API 返回的属性列表与 fallback 数据合并。
    以 API 返回为主，补充 API 中缺失的属性。
    """
    if not product_key:
        return api_attributes or []

    fallback = get_fallback_attributes(product_key)
    if not fallback:
        return api_attributes or []

    if not api_attributes:
        _log_fallback_used(product_key, len(fallback), "API 返回为空")
        return fallback

    # 已有的 identifier 集合
    existing_ids = set()
    for item in api_attributes:
        identifier = item.get('identifier')
        if identifier:
            existing_ids.add(identifier)

    # 补充缺失的属性
    merged = list(api_attributes)
    added = []
    for item in fallback:
        identifier = item.get('identifier')
        if identifier and identifier not in existing_ids:
            merged.append(item)
            added.append(identifier)

    if added:
        _log_fallback_used(product_key, len(added), "补充缺失属性: " + ", ".join(added))

    return merged


def _log_fallback_used(product_key: str, count: int, reason: str):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        "Panel config fallback used for productKey=%s, %d attributes added. Reason: %s",
        product_key, count, reason
    )
