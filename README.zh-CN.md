# MissionPlanner 简体中文汉化版(zh-Hans Localization)

本仓库是 [ArduPilot MissionPlanner](https://github.com/ArduPilot/MissionPlanner) 的简体中文汉化版,**非官方**构建。在上游 master 基础上完成了一次系统性翻译审核与修复,不改动任何业务逻辑。

## 相比上游的改动

### 1. 翻译修正(准确性)
- 修正 25 处错译/漏译,例如:
  - 「估算便宜」→「估算偏移」(Estimate Offset)
  - 「在起点投放图像」→「丢弃开头图像」(Drop image at start,此处 Drop 指剔除)
  - 「操作重发」→「机会性重发」(Opportunistic Resend)
  - 「很有空」→「很有用」等错别字
- 运行时会覆盖 resx 中文翻译的 21 处代码赋值,全部改为走 `L10NU.GetString()` 翻译表(否则界面永远显示英文)。

### 2. 补齐缺失翻译(完整性)
- 审计发现约 1000 条用户可见字符串从未翻译(回退英文)。本次补译:
  - 共享字符串库 `Strings.resx`(94 条)、FlightData、SiK 数传电台、GridUI 测绘规划(整页 82 条)、GPS 注入模拟器 ConfigSerialInjectGPS(整页 69 条)、SITL 仿真设置等
  - 新增 `GridUI.zh-Hans.resx`、`ConfigSerialInjectGPS.zh-Hans.resx`、`SITL.zh-Hans.resx` 三个整页汉化资源
- 38 个高频弹窗/按钮的硬编码英文(连接失败、解锁/上锁确认、参数写入、固件刷写等)接入 `L10NU` 翻译表并补齐中文。

### 3. 修复上游编码 Bug
- `ExtLibs/Utilities/Properties/Resources.resx` 中 `strings_zhHans.txt` 的编码声明为 `gb2312`,而文件实际是 UTF-8,导致翻译表运行时读出乱码。已改为 `utf-8`。

### 4. 飞控消息友好翻译(STATUSTEXT)
- 飞控下发的英文运行消息(如 `PreArm: Barometer not healthy`)在消息列表与语音播报中显示中文译文;语料 194 条覆盖 ArduPilot 常见告警,仅当界面语言为中文时启用,未命中的消息原样透传,任何异常自动降级——消息永不丢失。
- 仅翻译显示副本:日志、语音压制、解锁前检查匹配仍用英文原文,不影响任何功能逻辑。

### 5. 主流程界面全量汉化(2026-11-22)
- 新增 25 个窗体的 zh-Hans 资源,覆盖固件安装页(含 ConfigFirmwareManifest)、解锁前检查、振动/EKF 状态、罗盘校准、串口参数、舵口输出、初始参数、摇杆动作对话框、离线地图预取、日志分析等主流程/常用页面;回填 33 个已有窗体缺失的 246 条用户可见条目。
- 再补 329 处硬编码英文弹窗/按钮/提示(含强制解锁/上锁的安全确认文案、全部共用对话框的 确定/取消/是/否 按钮),按所在程序集接入 `Strings.*` 或 `L10NU` 翻译表。

## 使用方法

1. 下载 [Releases](../../releases) 中的 `MissionPlanner-zhCN-*.zip` 并解压,运行 `MissionPlanner.exe`(需 .NET Framework 4.7.2,Windows)。
2. 菜单 `配置(Configuration) → Planner`,将 Language 设为 **简体中文(zh-Hans)**,重启后生效。

## 与上游同步

本 fork 基于上游 master 的某个快照,并直接修改了上游文件,合并上游时会有预期内的冲突:

- 易冲突点:`GCSViews/FlightData.cs`、`GCSViews/FlightPlanner.cs`、`MainV2.cs`、`GCSViews/ConfigurationView/Config*.cs`(做过 L10NU 包裹)、`ExtLibs/Utilities/Properties/Resources.resx`(编码修复),以及各 `*.zh-Hans.resx`(上游会随翻译更新重写)。
- 同步流程:`git fetch origin && git rebase origin/master`。
- resx 冲突的处理原则:保留本地中文条目,合并上游新增的控件条目;冲突面大时以上游版本为基础重放本地条目。

## 覆盖现状(诚实声明)

汉化尚未 100% 覆盖,以下范围内遇到英文界面属于正常回退:

- 约 101 个冷门窗体(深度调参/调试工具/插件页,如 ADSB、DroneCAN、OSD、Swarm、SITL 工具、第三方插件)仍无 zh-Hans 资源——正常使用的主流程(连接、固件、校准、飞行、规划、常规配置)已全部中文。
- 参数编辑器中每个参数的英文元数据描述来自上游参数定义,属于专业知识文本,未翻译;参数名本身也保持原文。
- SikRadio 独立小工具(SiK 数传终端)的少量弹窗仍为英文。
- 欢迎按需补充:复制同名 `.resx` 中对应的 `<data>` 条目到 `.zh-Hans.resx` 即可开始。

## 构建

```bat
git submodule update --init
nuget restore MissionPlanner.sln
msbuild -v:m -restore -t:Build -p:Configuration=Release MissionPlanner.sln
```

需要 Windows + Visual Studio 2022。推 `v*-zh*` 格式的 tag 会触发 `release-zh.yml` 自动构建并发布 Release。

## 许可

遵循上游 [GPL-3.0](COPYING.txt) 许可,版权与功劳属于 MissionPlanner 的原作者与贡献者。本仓库的翻译改动同样以 GPL-3.0 发布。
