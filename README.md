# TCL AC for Home Assistant

将 TCL 空调（微信小程序通道）接入 Home Assistant 的非官方集成，理论上支持所有小程序可控设备。

基于 [ndwzy/tcl-ha](https://github.com/ndwzy/tcl-ha) 改进（面板联动/禁用规则参考了 [qwqqq6/tclplus-ac](https://github.com/qwqqq6/tclplus-ac) 对 TCL+ App 面板行为的逆向），并以独立集成 `tcl_ac` 发布——与原版 `tcl` 集成互不影响，可视为全新插件安装。

感谢 [banto6](https://github.com/banto6/haier) 提供的参考。

## 功能特性

- 三种登录方式：账号密码、短信验证码、抓包 refreshToken（配置后可在选项中更换）
- MQTT 实时推送设备状态（cloud_push），不轮询
- 物模型驱动实体：Switch / Number / Select / Sensor / Climate 按云端物模型自动生成
- 空调电量统计传感器（电量、电费、运行时长、碳排放、历史周期）
- 设备/实体两级筛选，可隐藏不想接入的设备或属性

## 相对上游 ndwzy/tcl-ha 的改进

**实体准确性**
- 只读状态位不再生成"能看不能控"的假开关：`*Status` 后缀属性（如 `lightSenserStatus`、`PTCStatus`）及已知只读属性自动解析为只读传感器，值按物模型 specs 翻译为"开/关"等可读文本
- `currentTemperature` 等只读数值不再生成可写 Number 实体
- 云端物模型重复返回的属性按 identifier 去重；物模型 title 重名时自动附加 identifier 后缀，避免同名实体
- 补充了光敏状态、新风防凝露、盘管温度、压缩机频率等常见属性的中文命名

**面板行为还原（参考 TCL+ App）**
- 控制联动：下发指令自动附带 App 会联动下发的属性——关机连关柔风、切模式清理 ECO/睡眠/电辅热/自学习、ECO 与电辅热互斥、手动风速关自动风、开自清洁自动关机等；且只附带当前设备物模型中存在的属性
- 工况禁用：App 面板会置灰的控件在 HA 中同样显示为不可用（如关机时温度/模式/柔风/ECO 不可用，除湿模式下风速不可用）

**Climate 实体**
- "自动"风速真实下发 `windSpeedAutoSwitch`，手动档位下发风速百分比并联动关闭自动风
- 温度上下限/步进优先取自物模型 specs（随机型而异），默认 16-31℃ / 0.5
- 兼容 workMode=5（AI 模式）上报，映射为自动模式

**会话与稳定性**
- token 按 JWT 过期时间提前刷新（剩余 30 分钟内），减少运行中突然失效
- 修复 MQTT 连接阻塞 HA 事件循环的问题（connect 移入线程池）
- 锁定 paho-mqtt < 2.0（2.x API 不兼容会导致集成无法启动）

## 安装

### 从旧版 ndwzy/tcl-ha 迁移

本集成为独立新插件（域名 `tcl_ac`）。如果之前装过原版：
1. 先在 HA 中删除原有的 `Tcl` 集成（避免实体 ID 冲突产生 `_2` 后缀实体）
2. 删除 `custom_components/tcl` 目录
3. 重启后按下述方法安装本集成，重新登录添加

### HACS 安装

1. HACS → 自定义仓库 → 添加 `https://github.com/rrryyi/tcl-ha`，类别选 Integration
2. 安装 `TCL AC` 后重启 Home Assistant

### 手动安装

复制 `custom_components/tcl_ac` 文件夹到 HA 配置目录的 `custom_components/` 下：

```text
config/
  custom_components/
    tcl_ac/
      manifest.json
      __init__.py
      ...
```

重启 Home Assistant。

## 配置

设置 → 设备与服务 → 添加集成 → 搜索 `TCL AC`

支持三种登录方式（token 抓包 / 账号密码 / 短信验证码），添加后可在集成"配置"里更换账号、筛选设备与实体。

## 调试

在 `configuration.yaml` 中加入以下配置打开调试日志：

```yaml
logger:
  default: warn
  logs:
    custom_components.tcl_ac: debug
```

## 免责声明

非官方项目，与 TCL / TCL+ / Home Assistant 官方无关。云接口可能随 App 更新变化，使用风险自负。
