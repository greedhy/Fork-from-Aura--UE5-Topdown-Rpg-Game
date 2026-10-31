# 装备全属性扩展（2026-10-31）

## 范围

扩展现有 AttributeSet 中的 20 个持久属性；维持 Infinite、非周期、Stacking=None、Channel1 AddBase。当前 Health/Mana 是可消耗资源，IncomingDamage/IncomingXP 是结算元属性，继续禁止作为装备常驻 Modifier。未添加百分比运算、总乘或触发能力。

同一 GE 可有任意非空的受支持属性子集，不再要求恰好三条。属性不能重复，Tag 必须与 Attribute 对应。实例包含模板未覆盖的属性时，装备请求失败，不能静默漏加。共用 GE_Equipment_Random 配置全部 20 项，未抽中的项以 0 写入。

## 属性与默认后缀

统一注册表：`Source/test_25d/Private/Equipment/EquipmentStats.cpp`。Tag 通过 NativeGameplayTags 注册，不需在 ini 重复声明。沿用原 AttributeSet 拼写（如 ArmorPene、CriticalHitResistence），避免改变既有反射字段和存档。

| 属性 | 中文 | SetByCaller Tag | 新增后缀行 |
|---|---|---|---|
| Strength | 力量 | Equipment.Stat.Strength | OfStrength（之力量） |
| Intelligence | 智力 | Equipment.Stat.Intelligence | OfIntelligence（之智力） |
| Resilience | 韧性 | Equipment.Stat.Resilience | OfResilience（之韧性） |
| Vigor | 活力 | Equipment.Stat.Vigor | OfVigor（之活力） |
| Armor | 护甲 | Equipment.Stat.Armor | OfArmor（之护甲） |
| ArmorPene | 护甲穿透 | Equipment.Stat.ArmorPene | OfArmorPene（之护甲穿透） |
| BlockChance | 格挡率 | Equipment.Stat.BlockChance | OfBlockChance（之格挡率） |
| CriticalHitChance | 暴击率 | Equipment.Stat.CriticalHitChance | OfCriticalHitChance（之暴击率） |
| CriticalHitDamage | 暴击伤害 | Equipment.Stat.CriticalHitDamage | OfCriticalHitDamage（之暴击伤害） |
| CriticalHitResistence | 暴击抗性 | Equipment.Stat.CriticalHitResistence | OfCriticalHitResistence（之暴击抗性） |
| HealthRegeneration | 生命恢复 | Equipment.Stat.HealthRegeneration | OfHealthRegeneration（之生命恢复） |
| ManaRegeneration | 法力恢复 | Equipment.Stat.ManaRegeneration | OfManaRegeneration（之法力恢复） |
| MaxHealth | 最大生命 | Equipment.Stat.MaxHealth | OfMaxHealth（之最大生命） |
| MaxMana | 最大法力 | Equipment.Stat.MaxMana | OfMaxMana（之最大法力） |
| FireResistance | 火焰抗性 | Equipment.Stat.FireResistance | OfFireResistance（之火焰抗性） |
| ThunderResistance | 雷电抗性 | Equipment.Stat.ThunderResistance | OfThunderResistance（之雷电抗性） |
| WaterResistance | 水系抗性 | Equipment.Stat.WaterResistance | OfWaterResistance（之水系抗性） |
| MagicResistance | 魔法抗性 | Equipment.Stat.MagicResistance | OfMagicResistance（之魔法抗性） |
| PhysicsResistance | 物理抗性 | Equipment.Stat.PhysicsResistance | OfPhysicsResistance（之物理抗性） |
| PureResistance | 纯粹抗性 | Equipment.Stat.PureResistance | OfPureResistance（之纯粹抗性） |

新后缀在 DT_EquipmentAffixes 配置：bPrefix=false，Weight=1，ExclusiveGroup 为属性名，Profiles 为空表示适用于所有 Profile。默认 Tier1 为等级 1～9、Tier2 为 10～20，第二档为第一档两倍。上限类默认 10～20，恢复属性 0.2～0.5（1 位小数），其他属性 1～3。它们是可修改的初始策划值，不代表最终平衡；概率属性的加法单位沿用现有属性语义，不是百分比乘法。

原四条词缀及已存在同名行保留。新增池会改变新物品抽取分布；旧 RollData 不重抽。单块统计项上限随注册表数量更新，保留六词缀上限及有限值/总量检查。恢复类装备只改变恢复属性，不新增计时回血/回蓝系统。

## 资产迁移与验证

1. 保存并关闭项目，构建最新 Editor 模块。
2. 使用 UE Python 执行 `Scripts/Equipment/author_all_equipment_suffixes.py`。脚本合并缺失后缀；将共用 GE_Equipment_Random 的 Modifier 列表迁移为原生模板的 20 条。该列表由代码维护，其他 GE 不修改。
3. 查看 `Saved/Equipment/all_attributes_authored.json` 与 `ALL_EQUIPMENT_ATTRIBUTES_SUCCESS` 标记。
4. 运行 `Scripts/test_equipment.ps1 -AllProjectTests`；AllAttributes 测试组合真实基础 GE，逐属性穿戴、快照恢复、卸下并检查所有属性还原，包含派生属性联动。

## 本次验证结果

- Editor 构建成功，共用 GE 迁移为 20 条 Modifier；新增 20 种后缀，保留旧行。
- `Scripts/test_equipment.ps1 -AllProjectTests`：220 项通过，120 项 Success、100 项 SuccessWithWarnings，0 失败、0 未运行。报告 `Saved/Automation/Equipment/index.json`；日志 `Saved/Logs/EquipmentAllStatsRegression.log`。
- 新增 `test_25d.Equipment.Random.AllAttributes` 从磁盘加载真实 GE/词缀表，组合真实 GE_SecondaryAttributes，逐项验证加成、恢复不叠加及卸下后全部属性还原；覆盖非三条模板、重复属性拒绝、20 项 RollData 和中文详情。原随机生命周期测试保留保存/加载及丢弃回拾覆盖，夹具固定词缀以避免策划池变化改变预期。
- 本次未执行新增属性的双端 PIE、键鼠体验或网络延迟测试；以前三属性 PIE 结果不能替代本次 20 属性联机验收。
