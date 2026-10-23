# 项目接入地图

以下路径相对 `.uproject` 所在目录，资产路径大小写沿用 `BluePrints`。这是定位索引；有变更时以实际源码和资产读回为准，不将旧文档里的 UE 5.2 当作当前引擎。当前样例 `.uproject` 为 5.8，制作记录为 5.8.1。

## 最少读取范围

先读 `docs/2026-10-21-arcane-nova-guide.md` 的对应章节；再读所选原型、其基类及本次涉及的接入点。不用完整遍历 Content 或读取整份 README。

| 职责 | 真实文件/资产 | 本项目约定 |
| --- | --- | --- |
| GA 基类 | `Source/test_25d/Public/AbilitySystem/Ability/MyGameplayAbility.h`、对应 Private cpp | StartupInputTag；GetDescription/GetNextLevelDescription；GE 读取耗蓝/冷却 |
| 伤害基类 | 同目录 `MyDamageGameplayAbility.h/.cpp` | FScalableFloat、DamageType、FDamageEffectParams；默认 DebuffChance=20，不能无意继承 |
| 瞬发范围样例 | 同目录 `MyArcaneNova.h/.cpp` | ServerOnly；Commit 一次；候选目标进一步筛选；Cue；结束 |
| 投射物/近战/持续/召唤/被动 | 同目录 `MyProjectileSpell`、`MyFireBolt`、`MyMeleeAttack`、`MyBeamSpell`、`SummonAbility`、`MyPassiveAbility` | 其 C++ 可能只是辅助函数，实际执行图仍须读蓝图 |
| 伤害通路 | `Private/AbilitySystem/MyAbilitySystemLibrary.cpp`、`ExecCalc/ExecCalc_Damage.cpp`、`MyAttributeSet.cpp` | ApplyDamageEffect → GE_Damage/ExecCalc → 属性后处理、受击/死亡 |
| 原生标签 | `Public/MyGameplayTags.h`、`Private/MyGameplayTags.cpp` | FMyGameplayTags::InitializeNativeGameplayTags；声明与注册同时改 |
| 授予、输入、装备 | `Private/AbilitySystem/MyAbilitySystemComponent.cpp` | 身份在 AbilityTags；输入和状态在 Spec.DynamicAbilityTags |
| 角色/存档 | `Private/Character/PlayerCharacter.cpp`、`BaseCharacter.cpp`、`Public/Game/LoadScreenSaveGame.h` | 新档 Startup；旧档先恢复再 UpdateAbilityStatuses；FSavedAbility |
| 技能目录结构 | `Public/AbilitySystem/Data/AbilityInfo.h` | FMyAbilityInfo；AbilityInformation 数组 |
| 技能 UI | `Private/UI/WidgetController/SpellMenuWidgetController.cpp`、`MyWidgetController.cpp`、`OverlayWidgetController.cpp` | 控制器广播目录与运行时状态，技能球按标签筛选 |
| 输入链 | `Private/Player/MyPlayerController.cpp`、`Public/Input/MyInputComponent.h`、`MyInputConfig.h` | Enhanced Input→ASC 的 Pressed/Held/Released |
| 目标同步 | `Private/AbilitySystem/AbilityTask/TargetDataUnderMouse.cpp` | 本地鼠标 TargetData→服务端；处理提前到达数据 |
| 自动化样例 | `Private/Tests/ArcaneNovaTests.cpp` | 真实 GA/GE 资产、瞬态测试 World、ASC 与属性初始化 |

上表简写的 Public/Private 均在 `Source/test_25d/` 下；其他项目先找模块名。

## 资产锚点

- GA 根：`/Game/BluePrints/AbilitySystem/Player/Ability/`。现有子目录：`Fire/FireBolt`、`Arcane/ArcaneChard`（保留此拼写）、`Arcane/ArcaneNova`、`Thunder`、`PassiveSpell`、`Passive_Startup`。
- 敌人 GA：`/Game/BluePrints/AbilitySystem/Enemy/Ability/`。
- 伤害 GE：`/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage`。
- 目录：`/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo`；敌人初始化参阅 `DA_CharacterClassInfo`。
- 玩家：`/Game/BluePrints/Characters/Player/BP_Player`，属性 `startup_ability` / `startup_passive_ability`。
- Cue：`/Game/BluePrints/AbilitySystem/GameplayCueNotify/`，检查 Config 中 GameplayCueNotifyPaths 覆盖。
- 输入：`/Game/BluePrints/Input/DA_MyInputConfig`、`IMC_PlayerContext` 和 InputActions。
- 进攻树：`/Game/BluePrints/UI/SpellMenu/WBP_OffensiveSpellTree`；被动树通过资产检索定位，不猜名字。

## 必须区分的标签

| 意义 | 示例/约定 |
| --- | --- |
| 唯一身份 | `Abilities.Arcane.ArcaneNova`，GA AbilityTags 中用于检索；一项明确身份 |
| 冷却 | `Cooldown.Arcane.ArcaneNova`，GA 冷却 GE 和目录一致，真正授予 ASC |
| 表现 | `GameplayCue.ArcaneNova`，实际 GC 映射与目录发现 |
| 输入槽 | `InputTag.LMB/RMB/1/2/3/4`、`InputTag.Passive.1/2` |
| 状态 | `Abilities.Status.Eligible/Unlocked/Equipped`，运行时 Spec 决定 |
| 类型 | `Abilities.Type.Offensive/Passive`，目录决定装备与存档路径 |

当前已有 Damage.Fire/Thunder/Magic/Physics/Water/Pure。**冰霜视觉不自动意味着项目支持 Damage.Ice。** 若用户只是冰霜外观，明确采用的已有伤害类型；若要求新的元素机制，检查并实现 DamageTypesToResistance、AttributeSet、ExecCalc 捕获以及适用的 Debuff 映射，不能只注册一个标签就算完成。

## 授予、UI、存档

1. `DA_AbilityInfo` 中按 AbilityTag **和** Ability class 查重；同一身份更新对应行，冲突先定位。静态字段是 AbilityTag/CooldownTag/AbilityType/LevelRequirement/Ability/Icon/BackgroundMaterial。InputTag、StatusTag 属运行时信息，不固定为 Equipped。
2. 可学习技能只登记目录和技能树。要求新角色初始可用时才追加正确 Startup 数组，核实输入槽未占用。ArcaneNova 已占用过 `InputTag.1` 和树按钮 `_7`，每次都重新读回；它们不是空槽模板。
3. 输入标签存在不代表实体按键接通。检查 InputAction→InputConfig→IMC→控制器；当前 Held 会尝试激活，所以输入触发器会影响长按连放。
4. 技能球除 AbilityTag 外必须保留控制器绑定和 OnSpellButtonSelected 链；使用可用空位或按现有布局新增控件。只改 CDO 标签不能证明点击工作。
5. 当前 `LoadProgress` 已有 `UpdateAbilityStatuses(SaveData->PlayerLevel)`。先检查，不重复插入；保证已有 Spec 等级/状态/槽位不变，新项满足等级才 Eligible。不得为测试删除用户存档。
6. 被动恢复不能只测新技能重新激活：当前替换旧被动时 ClearSlot 未同步移除 Equipped。若本任务涉及被动替换/卸下，检查旧 Spec 状态、UI 广播和保存记录，防止旧效果读档后复活；见 [被动生命周期](ability-patterns.md)。
7. 敌人技能不默认进入玩家目录和菜单；读 CharacterClassInfo、敌人授予与 BTTask_Attack 的标签调用。

## 已有脚本的用途

`Scripts/create_arcane_nova_assets.py`、`configure_arcane_nova_assets.py` 和 `verify_arcane_nova_*` 是样例，不是通用入口。它们固定名字、伤害增量、输入、树位置、报告目录和测试数量。新 GA 生成自己的脚本与断言；修改一个旧 GA 时不重跑 Nova 接入脚本。旧 `inspect_arcane_nova_references.py` 中冷却 `components` 可能读不到；当前配置脚本用 `ge_components`。
