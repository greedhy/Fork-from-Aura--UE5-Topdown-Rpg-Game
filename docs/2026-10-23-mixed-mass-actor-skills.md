# 技能同时命中 Mass 与 Actor

## 使用范围

`/Game/PureMass/Abilities` 中继承 `UPureMassAbility` 的 26 个技能资产共用本次适配，原型配置可继续组合。18 种行为涵盖投射物、多重投射、爆发、射线、地表、环绕、持续区域、陷阱、追踪、穿透、连锁、锥形、波纹、回旋、发射器、延迟、圆环和直线。

普通怪物仍由 Mass Entity 表示，没有为它们创建逐怪 Actor、ASC 或碰撞组件。Actor 敌人继续使用 CombatInterface、阵营标签和原有 ASC/GE_Damage；玩家仍为 Character/Actor。此次没有实现精英属性或 Boss AI。

独立测试地图与 `L_DungeonLabyrinth` 使用 PureMass 技能目录。原有 `/Game/BluePrints/...` 技能资产、`BP_Player`、存档能力和 Actor 战斗框架没有自动替换；仅把旧 GA 装上并不会使其支持 Mass。若后续使用原 `BP_Player`，需要配套启用 Mass 世界、混合目标控制器并授予本目录技能，保留其原动画蓝图。

## 目标与伤害

- `FPureMassCombatTarget` 保存 Mass 稳定 ID 或 Actor 弱引用。两种身份不能同时存在。
- 鼠标选择、投射物碰撞、范围查询、连锁和追踪共用 `PureMassCombat`；穿透按碰撞时间混合排序，对两类目标统一去重。友军、尸体不遮挡技能，实体墙体优先于同时间命中。
- GAS TargetData 传递 Actor 网络引用或 Mass ID。服务端重新检查所属世界、敌我、存活、射程、瞄准点和视线；伤害和消耗不由客户端决定。
- Actor 伤害应用原有 GE_Damage；Mass 伤害写入实体状态并通过快照复制。技能运行时和特效仍为每个技能行为节点的共享 Actor，并非每只怪物的 Actor。
- 连锁能在 Mass → Actor → Mass 之间跳转，子节点保留目标身份与施法预算。射线、追踪和环绕在目标死亡/销毁时重新检查身份并清理或回到盘旋。
- 地表沿用 Actor GAS 地表状态与 Mass 地表采样，保持施法者免疫。

## 验证入口

新增原生测试：`test_25d.PureMass.Mixed.*`；报告位于 `Saved/PureMass/MixedCombat/`。

`Scripts/PureMass/verify_mixed_pie.py` 在 `L_PureMassDungeon` 的双客户端 Listen Server PIE 中运行，临时创建一个 Actor Goblin 和一个 Mass Goblin，通过远端客户端 Enhanced Input 实际施放追踪、范围、连锁、左键投射、射线和环绕。检查服务端伤害、两端血量、一次扣蓝和持续技能清理。测试只改变 PIE 对象，结束后停止 PIE 即可移除夹具。

Actor 查询当前遍历世界中实现 CombatInterface 的 Actor；适合少量精英/Boss，与大量普通怪物的 Mass 空间查询并存。尚未进行大规模 Actor 查询性能压测。

## 本次验证结果

- Editor Development 编译成功：`Saved/PureMass/MixedCombat/build-3.log`。
- 完整项目自动化 119/119 成功，其中混合目标新增 12 项；0 失败、0 未运行。59 项有测试夹具/既有资源警告（例如无骨骼 Mesh 的原生测试角色）。报告：`Saved/PureMass/MixedCombat/tests-2/index.json`。
- 双客户端实际输入 35/35 检查通过：`Saved/PureMass/MixedCombat/pie.json`。包括远端 Actor/Mass 定点攻击、同次 Burst/Chain 命中两类目标、左键 Actor 攻击、两端 HP 一致、单次提交消耗，以及 Actor 目标触发环绕攻击和关闭清理。
- 26 个复制技能及目录配置验证通过：`Saved/PureMass/asset-validation.json`。
- 测试结束已停止 PIE；未保存运行时生成的 QA 敌人，未修改原 Actor 技能/角色资产。

### 编译环境说明

默认 Unity 合并编译暴露旧 `PrototypeTests.cpp` 与 `TerrainSurfaceTests.cpp` 的全局 `using namespace`/同名 `FWorld` 冲突。本次按“不修改已有框架/文件”的约束保留这两个文件，通过临时设置项目本地 `Saved/UnrealBuildTool/BuildConfiguration.xml` 的 `ModuleConfiguration/DisableUnityBuild/Item=test_25d` 完成独立编译，随后恢复本地配置。该旧 Unity 冲突尚未修改；重新编译时可采用相同的模块独立编译设置。UE 5.8 本环境单独传入 `-DisableUnity` 未禁用项目模块的 Unity，不能用该次失败记录作为通过证据。
