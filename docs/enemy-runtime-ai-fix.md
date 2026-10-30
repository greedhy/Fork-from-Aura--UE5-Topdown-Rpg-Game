# 房间动态生成怪物不启动 AI 修复

## 原因与修改

普通怪 `BP_GoblinSpear`、`BP_Goblin_Slinshot`、`BP_Ghoul` 已配置控制器和行为树，但 `Auto Possess AI` 为 `Placed in World`。房间通过运行时生成 Actor 创建怪物，因此不会自动创建控制器，也不会进入 `AEnemyCharacter::PossessedBy` 的行为树启动流程。

三者已改为 `Placed in World or Spawned` 并编译保存。StoneGolem 原本就是此配置，因此没有同样的问题。未修改共享行为树、攻击技能或对象池逻辑。

`Scripts/RoguelikeGeneration/fix_enemy_runtime_ai.py` 保存了带备份的修复过程；`author_enemy_roster.py` 增加运行时自动接管配置检查，阻止再次接入此类错误配置。

## 验证

在隔离临时地图的 PIE 中通过引擎 Summon（实际调用 SpawnActor）动态生成三个类型，而不是预先放置：

- 修复前：三个类型均无 Controller、无 BrainComponent。
- 修复后：三个类型均获得 BP_MyAIController，BehaviorTreeComponent.is_running() 均为 true，3/3 通过。
- 证据：`Saved/GAAuthoring/EnemyAIRegression/spawn-before.json`、`spawn-probe.json`、`asset-fix.json`。
- 本次测试验证动态生成后的控制器与行为树启动；临时地图没有导航网格，不替代实际房间内追逐、攻击与对象池复用的完整试玩。

## StoneGolem 行动配置位置

以下资源均位于 `/Game/BluePrints` 下：

| 职责 | 位置 |
|---|---|
| 索敌、追逐及攻击流程 | `AI/BehaviorTree/BT_EnemyBehaviorTree`，由 `Characters/StoneGolem/DA_StoneGolemElite` 的 Behavior 字段指定 |
| 基础移动速度、资源、技能配置 | `Characters/StoneGolem/DA_StoneGolemElite` |
| 各技能距离、选择权重、冷却、伤害、预警及命中时序 | `Characters/StoneGolem/DA_SG_HeavyHammer`、`DA_SG_Quake`、`DA_SG_ShieldBash` |
| 移动动画及攻击 Slot 播放 | `Characters/StoneGolem/Animations/ABP_SG_Elite` |

行为树的 `BTT_Attack` 通过 `Abilities.Attack` 标签激活技能选择入口。`Source/test_25d/Private/StoneGolem/StoneGolemCharacter.cpp` 中的 `TryChooseAttack()` 根据可激活条件和配置权重选择技能；`StoneGolemAbility.cpp` 执行预警、蒙太奇、命中及清理。动画蓝图负责播放动作，行为树与 GA 负责行动决策和执行。
