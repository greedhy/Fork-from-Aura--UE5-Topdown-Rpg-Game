# 装备 GE 属性加成修复

## 原因与修改

玩家实际使用的 `GE_SecondaryAttributes` 在 Channel0 通过 Override 计算护甲、最大生命和最大法力。旧装备 GE 同样位于 Channel0，AddBase 被 Override 覆盖，因此 Active GE 存在但属性不增加。

保留基础 GE 的计算公式与 Channel0；将三件样例装备 GE 的所有 Modifier 迁移为 Channel1 AddBase。装备 Infinite GE 的应用、独立句柄、卸除与物品实例流程保持原逻辑。曲线数值仍由 `CT_EquipmentStats` 修改。

`Config/DefaultGame.ini` 的 `[/Script/GameplayAbilities.AbilitySystemGlobals]` 段启用 `bAllowGameplayModEvaluationChannels`，并命名 Channel0 为 BaseAttributes、Channel1 为 EquipmentBonuses。UE 5.8 的 `UGameplayAbilitiesDeveloperSettings::OverrideConfigSection` 明确使用这个兼容配置段；不能根据新设置类名猜测配置段。

`IsSafeEquipmentEffect` 要求通道已启用且每个 Modifier 位于 Channel1。`author_examples.py` 创建新装备时设置 Channel1；`migrate_equipment_channels.py` 仅迁移三件现有样例，保留 Modifier 属性、数值及曲线引用。制作 skill 已同步该约束。

## 验证要求

- `AuthoredTableAssets` 先应用真实 `GE_SecondaryAttributes`，再验证三件真实装备数值、卸下还原、不自动补血补蓝、主属性重算及两枚戒指独立叠加。
- `RejectWrongEvaluationChannel` 验证项目开关及 Channel0 装备被拒绝。
- `pie_attribute_probe.py` 在真实地图逐件拾取、装备、卸下，记录实际属性与 Active GE，恢复原物品快照。
- `pie_attribute_network_probe.py` 使用监听服务器和远端客户端验证装备请求、属性复制及装备面板；不替代人工键鼠交互验收。

预期增量：IronGuardChest 护甲 +7，SapphireRing 最大法力 +25，RubyRing 最大生命 +50。配置和 GE 修改后须重启编辑器并开始新的 PIE，已存在的 Active GE 不会自动迁移通道。

## 本次验证结果

2026-10-30：Development Editor 构建成功；全项目自动化 202 项通过、0 失败、0 未运行。真实单机 PIE 和监听服务器 + 远端客户端 PIE 均通过三件样例逐件穿脱流程，客户端与服务器属性一致，实际增量分别为 +25 最大法力、+50 最大生命、+7 护甲。测试结束恢复原物品快照。

报告：`Saved/Automation/Equipment/index.json`、`Saved/Equipment/pie_equipment_attributes.json`、`Saved/Equipment/pie_equipment_network.json`。网络脚本需使用当前进程的命令行配置覆盖启动：

```
-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNetMode=PIE_ListenServer,[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNumberOfClients=2,[/Script/UnrealEd.LevelEditorPlaySettings]:RunUnderOneProcess=True
```

脚本通过真实客户端请求和复制通路测试，不模拟鼠标点击；尚未覆盖专用服务器、延迟/丢包及多客户端同时争抢装备。仓库与已安装 build-equipment skill 内容一致，skill 校验通过。
