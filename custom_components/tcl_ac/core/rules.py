"""
TCL 面板联动规则与禁用规则。

规则数据移植自对 TCL+ App 面板行为的逆向（参考 tclplus-ac 项目），
用于让集成像 App 一样：
1. 下发控制时附带联动属性（如切模式时清理 ECO/睡眠/电辅热等状态）
2. 在特定工况下将 App 面板置灰的属性标记为不可用（如关机时温度不可调）

规则中的属性值为物模型 identifier，与设备快照数据（attribute_snapshot_data）对应。
"""

# 禁用规则: (条件元组或条件元组列表, 要禁用的属性)
# 单条件 (("powerSwitch", "==", 0), "targetTemperature") 表示: 关机时温度不可用
# 多条件 ((cond1, cond2), attr) 表示: 所有条件同时满足时禁用
DISABLE_RULES = [
    (("powerSwitch", "==", 0), "targetTemperature"),
    (("powerSwitch", "==", 0), "workMode"),
    (("workMode", "==", 2), "windSpeedAutoSwitch"),
    (("workMode", "==", 2), "windSpeedPercentage"),
    (("workMode", "!=", 1), "softWind"),
    (("powerSwitch", "==", 0), "softWind"),
    ((("workMode", "!=", 1), ("workMode", "!=", 4)), "ECO"),
    (("powerSwitch", "==", 0), "ECO"),
    (("powerSwitch", "==", 0), "PTC"),
    (("powerSwitch", "==", 0), "sleep"),
    (("workMode", "!=", 4), "PTC"),
    (("powerSwitch", "==", 0), "antiMoldew"),
    (("workMode", "==", 0), "antiMoldew"),
    (("workMode", "==", 3), "antiMoldew"),
    (("workMode", "==", 4), "antiMoldew"),
    (("workMode", "==", 5), "antiMoldew"),
    (("workMode", "==", 0), "sleep"),
    (("workMode", "==", 2), "sleep"),
    (("workMode", "==", 3), "sleep"),
]

# 联动规则: 控制 main 属性（且满足 when 条件）时，附带下发 actions 中的属性
LINK_RULES = [
    {"main": ("powerSwitch", "==", 0), "when": [], "actions": [{"softWind": 0}]},
    {"main": ("powerSwitch", "==", 1), "when": [("workMode", "==", 2)], "actions": [{"antiMoldew": 0}]},
    {"main": ("powerSwitch", "==", 1), "when": [("workMode", "!=", 2)], "actions": [{"antiMoldew": 0}]},
    {"main": ("targetTemperature", "<", 26), "when": [("workMode", "==", 1)], "actions": [{"ECO": 0}]},
    {"main": ("targetTemperature", ">", 25), "when": [("workMode", "==", 4)], "actions": [{"ECO": 0}]},
    {"main": ("targetTemperature", "==", "any"), "when": [], "actions": [{"selfLearn": 0}]},
    {
        "main": ("workMode", "==", "any"),
        "when": [],
        "actions": [
            {"ECO": 0},
            {"sleep": 0},
            {"sleepTime": 0},
            {"antiMoldew": 0},
            {"PTC": 0},
            {"selfLearn": 0},
            {"softWind": 0},
        ],
    },
    # 风速与"风速自动"双向联动（与 App 面板一致，风速 0 即自动档）：
    # 风速设 0 → 开自动；设非 0 → 关自动；关自动 → 风速落到最小档 1；开自动 → 风速归 0。
    # 任何风速类操作都会取消自学习。
    {"main": ("windSpeedAutoSwitch", "==", 0), "when": [], "actions": [{"windSpeedPercentage": 1}, {"selfLearn": 0}]},
    {"main": ("windSpeedAutoSwitch", "==", 1), "when": [], "actions": [{"windSpeedPercentage": 0}, {"selfLearn": 0}]},
    {"main": ("windSpeedPercentage", "==", 0), "when": [], "actions": [{"windSpeedAutoSwitch": 1}, {"selfLearn": 0}]},
    {"main": ("windSpeedPercentage", "!=", 0), "when": [], "actions": [{"windSpeedAutoSwitch": 0}, {"selfLearn": 0}]},
    {"main": ("horizontalDirection", "==", "any"), "when": [], "actions": [{"selfLearn": 0}]},
    {"main": ("verticalDirection", "==", "any"), "when": [], "actions": [{"selfLearn": 0}]},
    {"main": ("sleep", "==", "any"), "when": [], "actions": [{"selfLearn": 0}]},
    {
        "main": ("ECO", "==", 1),
        "when": [("workMode", "==", 1), ("targetTemperature", "<", 26)],
        "actions": [{"targetTemperature": 26}],
    },
    {
        "main": ("ECO", "==", 1),
        "when": [("workMode", "==", 4), ("targetTemperature", ">", 25)],
        "actions": [{"targetTemperature": 25}],
    },
    {"main": ("ECO", "==", 1), "when": [], "actions": [{"PTC": 0}]},
    {"main": ("PTC", "==", 1), "when": [], "actions": [{"ECO": 0}]},
    {"main": ("selfClean", "==", 1), "when": [], "actions": [{"powerSwitch": 0}]},
    # 新风超强风开启时，把新风风速拉满到 100（与 App 面板一致）
    {"main": ("newWindSuper", "==", 1), "when": [], "actions": [{"newWindPercentage": 100}]},
]


def _coerce(value):
    """尽量把字符串转为数值，便于与规则值比较"""
    if isinstance(value, str):
        text = value.strip()
        if text == "any":
            return text
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return text
    return value


def _compare(left, operator: str, right) -> bool:
    left = _coerce(left)
    right = _coerce(right)
    if right == "any":
        return True
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    try:
        left_num = float(left)
        right_num = float(right)
    except (TypeError, ValueError):
        return False
    if operator == ">":
        return left_num > right_num
    if operator == "<":
        return left_num < right_num
    if operator == ">=":
        return left_num >= right_num
    if operator == "<=":
        return left_num <= right_num
    return False


def _condition_matches(condition: tuple, props: dict) -> bool:
    identifier, operator, value = condition
    # 属性未上报时不参与匹配，避免误禁用
    if identifier not in props:
        return False
    return _compare(props.get(identifier), operator, value)


def _normalize_conditions(raw) -> list:
    if isinstance(raw, tuple) and len(raw) == 3 and isinstance(raw[0], str):
        return [raw]
    return list(raw)


def is_disabled(identifier: str, props: dict) -> bool:
    """判断某属性当前是否被 App 面板规则禁用（应显示为不可用）"""
    for raw_conditions, target in DISABLE_RULES:
        if target != identifier:
            continue
        conditions = _normalize_conditions(raw_conditions)
        if all(_condition_matches(c, props) for c in conditions):
            return True
    return False


def linked_attributes(attributes: dict, props: dict) -> dict:
    """
    根据联动规则，计算控制 attributes 时应附带下发的额外属性。
    只返回额外属性，调用方自行合并；不修改入参。
    """
    after = dict(props)
    after.update(attributes)
    extra: dict = {}

    for identifier, value in attributes.items():
        for rule in LINK_RULES:
            main_id, main_op, main_value = rule["main"]
            if main_id != identifier or not _compare(value, main_op, main_value):
                continue
            if not all(_condition_matches(c, after) for c in rule["when"]):
                continue
            for action in rule["actions"]:
                for action_id, action_value in action.items():
                    after[action_id] = action_value
                    if action_id not in extra:
                        extra[action_id] = action_value
    return extra
