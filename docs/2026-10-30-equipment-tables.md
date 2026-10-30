# 装备表格与样例

## 资产位置

| 装备 | 图标 | 装备槽 | 等级 1 效果 |
| --- | --- | --- | --- |
| 蓝宝石戒指 SapphireRing | `/Game/Assets/EquipmentIcon/18824_1` | 左/右戒指 | 最大魔法 +25 |
| 红宝石戒指 RubyRing | `/Game/Assets/EquipmentIcon/19204_1` | 左/右戒指 | 最大生命 +50 |
| 铁卫胸甲 IronGuardChest | `/Game/Assets/EquipmentIcon/24119_1` | 胸甲 | 护甲 +7 |

GE 位于 `/Game/Equipment/Effects/GE_Equipment_<名称>`。三件样例使用导入的原始纹理，不重新生成图标。它们已进入现有物品目录的 EquipmentTable；没有自动发放到正式玩家背包，也没有配置世界掉落模型或改动现有 UI 布局。

## 如何修改

打开 `/Game/Equipment/DT_Equipment` 修改装备名称、图标、允许槽位、GE 引用、等级和拾取相关字段。行结构为 `BackpackItemDefEntry`。装备定义 ID 保持唯一且稳定；其命名格式是 `BackpackItem:SapphireRing` 等。

打开 `/Game/Equipment/CT_EquipmentStats` 修改数值：

- `SapphireRing_MaxMana`：25。
- `RubyRing_MaxHealth`：50。
- `IronGuardChest_Armor`：7。

这与红药水的 `GE_PotionHeal → ScalableFloat → CT_PotionHeal` 相同。装备 GE 的 ScalableFloat 系数为 1，引用上述对应行；横轴为 EquipEffectLevel，当前使用等级 1。可以新增等级关键帧；实际加成由该等级下的曲线取值决定。

这两张表分别管理元数据和数值。GE 仍定义“改变哪个 GAS 属性”等效果结构；换属性/增加属性条目时需配置相应 GE Modifier 和曲线行，不能只添加一个未被引用的曲线行。当前实现支持固定加法，不支持乘法、随机词条或主动能力。

改表后保存，在新 PIE 或卸下后重新装备验证；已应用的 Active GE 不保证热更新。原药水仍在目录 Items 中，未修改原药水 GE/曲线。

## 制作与测试

`Scripts/Equipment/author_examples.py` 在 UE Python 中创建缺失的三件样例与表，并连接目录和玩家槽位。重复执行保留已有表值，不用于覆盖设计师的调参结果。

`Scripts/test_equipment.ps1` 执行编译与装备/背包测试。新增 `test_25d.Equipment.AuthoredTableAssets` 加载真正的表和 GE，验证图标引用、三个加成与卸除，再临时将护甲曲线调为 13，验证新装备应用读取 13，最后恢复曲线且不保存测试修改。

2026-10-30：独立 DLL 编译成功；装备/背包 38 项自动化全部通过（37 项无警告、1 项带警告），0 失败、0 未运行。报告 `Saved/Automation/EquipmentAssets/index.json`。具体双客户端 PIE 与正式 UI 仍待用户验收。

后续制作可调用 `$build-equipment`。维护源为 `skills/build-equipment/SKILL.md`。

最终回归：常规默认 DLL 构建成功，`Scripts/test_equipment.ps1 -AllProjectTests` 完成 199 项测试（107 项无警告成功、92 项带警告成功），0 失败、0 未运行。最终报告 `Saved/Automation/Equipment/index.json`。
