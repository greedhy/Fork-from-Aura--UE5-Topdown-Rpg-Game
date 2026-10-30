# 随机装备接入指南（2026-10-31）

随机装备复用现有目录、服务器拾取、背包实例、装备事务和快照。固定装备与药水继续使用原定义，不将旧 ID 改成随机装备。

## 资产与表格

`Scripts/Equipment/author_random_equipment.py` 是 UE Python 初始化脚本。先完成新增反射类型的 Editor 构建并重启编辑器，再执行脚本。执行前保存编辑器中已有工作。脚本只添加缺失资产和行，保留同名行的策划修改；不用于覆盖同步策划值。

| 资产 | 编辑内容 |
| --- | --- |
| `/Game/Equipment/DT_Equipment` | 新增 RolledSapphireRing、RolledRubyRing、RolledIronGuardChest；稳定定义 ID、名称、图标、槽位、随机开关、GenerationProfile |
| `/Game/Equipment/DT_EquipmentGenerationProfiles` | 默认物品等级、基础属性上下限、可选品质 ID |
| `/Game/Equipment/DT_EquipmentRarities` | 品质名称、权重、词缀数量上下限、前后缀各自上限 |
| `/Game/Equipment/DT_EquipmentAffixes` | 词缀名称、前后缀、权重、适用 Profile、互斥组及等级分档 |
| `/Game/Equipment/CT_RandomEquipmentLevels` | LevelScale 在等级 1 为 1、等级 20 为 2；基础上下限引用该曲线 |
| `/Game/Equipment/Effects/GE_Equipment_Random` | 派生 RandomEquipmentGameplayEffect，继承三条 SetByCaller 加法属性模板 |

目录 `/Game/BluePrints/DA/DA_BackpackItemDefinitions` 引用以上三张生成表。已有非空但不同的表引用会使脚本拒绝替换，避免覆盖策划目录。原 Items 药剂条目不会改写。合并装备表时先将导出的 PrimaryAssetId 规范为 `BackpackItem:<name>`，避免 UE JSON 导出的空 PrimaryAssetType 丢失类型。

默认品质权重普通/魔法/稀有为 60/30/10，分别产生 0/1/2 条词缀；稀有最多一前缀一后缀。同一 ExclusiveGroup 不会重复选择。默认词缀等级档为 1–9 和 10–20。示例配置面向等级 1–20，扩展等级时必须同步补充词缀档和曲线。

属性白名单为 `Equipment.Stat.Armor`、`Equipment.Stat.MaxHealth`、`Equipment.Stat.MaxMana`。MinValue/MaxValue 是 ScalableFloat，可直接编辑常数或引用曲线；DecimalPlaces 控制精度。所有随机属性通过服务器结果写入独立 GE Spec，不修改共享 GE 默认对象。GE 使用 Channel1 AddBase，与真实玩家基础属性 Channel0 Override 共存。

## 实例与兼容

服务器生成一次实际结果，结果包括版本、Profile、等级、seed、品质名称、基础属性及词缀实际数值和显示名。拾取、穿脱、丢弃、复制和快照恢复应沿用同一 ItemInstanceId 与 RollData；不能在显示或装备时根据 seed 重抽。保存实际结果，因此后续表格平衡调整不应改变已经生成的装备。GenerationVersion=0 保持原固定装备通路；随机定义使用独立 ID，保留已有三件固定样例和药水。

脚本在已有唯一 EquipmentEntranceSamples 的 EquipmentNames 末尾追加三件随机样例，保留原五项和其他设计师条目，不创建第二个生成器。

## 执行与验收

1. 构建并重启加载最新模块后，在 UE Python 执行 `author_random_equipment.py`。
2. 检查日志 `RANDOM_EQUIPMENT_AUTHOR_SUCCESS` 和 `Saved/Equipment/random_equipment_authored.json`，重新加载核对表、类、目录引用和入口样例。
3. 重跑脚本确认已有行、药水、固定装备和原五项入口样例保留，随机样例不重复追加。
4. 运行项目装备自动化；生成测试应覆盖相同 seed、范围、等级过滤、权重、互斥、非法数据。GAS 测试组合真实 GE_SecondaryAttributes，核对三属性增量、独立卸除、重复恢复。
5. Listen Server 和远程客户端分别拾取、换装、丢弃再拾取、保存恢复；对比实例 ID、名称与实际属性，验证不重抽、不复制、不叠加。观察两客户端 UI 同步及资源上限。

## 本次实际验证结果

- 最新 Editor 模块构建完成；`Scripts/test_equipment.ps1 -AllProjectTests` 通过 205 项测试，0 失败。报告：`Saved/Automation/Equipment/index.json`，执行日志：`Saved/Logs/RandomEquipmentRegression.log`。
- 真实资产已生成并重新加载验证。重复执行初始化脚本成功，入口列表仍为 8 项（原 5 项 + 3 件随机装备），没有重复追加。报告：`Saved/Equipment/random_equipment_authored.json`。
- `pie_random_equipment_probe.py` 在真实地图完成三件随机装备拾取、背包和装备面板打开、穿戴、卸下与原快照恢复。真实玩家基础 GE 与随机 GE 共同生效，三属性增量等于实例保存值，卸下恢复原值。报告：`Saved/Equipment/pie_random_equipment.json`。
- 自动化生命周期测试另覆盖两件独立实例、丢弃再拾取、真实 SaveGame 内存序列化及加载、修改生成表后旧实例不重抽、重复恢复不叠加。
- `pie_random_equipment_network_probe.py` 在 Listen Server + 远程客户端 PIE 完成三件装备同样流程，逐件核对完整 RollData、实例 GUID 和服务器/客户端实际属性一致，卸下还原、快照恢复成功。最终报告：`Saved/Equipment/pie_random_equipment_network.json`（passed=true，三件 server_roll_matches=true），日志：`Saved/Logs/RandomEquipmentNetworkFinal.log`。

### 编辑器中试用

打开 `/Game/RoguelikeGeneration/Maps/L_RoguelikeRun` 开始 PIE，出生房间生成 8 个 Soul，其中 3 个是随机蓝宝石戒指、随机红宝石戒指和随机铁卫胸甲。靠近查看名称，按 E 拾取、B 打开背包，选择物品查看品质、等级、基础数值和词缀，再装备核对属性栏。每次重新生成世界物品允许抽到不同结果，已拾取物品穿脱不重抽。

本期只支持护甲、最大生命、最大法力的加法数值。百分比词缀、触发技能和洗练尚未实现。真实 PIE 脚本使用现有输入动作桥接与 RPC；鼠标/键盘手动体验、独立 Dedicated Server 和网络延迟/丢包验收仍需另测。此前双端运行还出现过地牢连接导航就绪超时警告；装备验证不代表完整地牢流程通过。
