# 房间模式原型火球施法朝向修复

2026-10-31。

## 原因

BP_DungeonPlayer 的初始能力包含 `/Game/PureMass/Abilities/GA_Prototype_Projectile`，并非原版 `/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/GA_FireBolt`。原型执行路径生成投射物，但没有更新玩家朝向；原版依靠转向接口与蒙太奇的 Motion Warping 窗口。

真实实例检查证实房间玩家保留MotionWarping组件。通过反射事件UpdateFacingTarget调用并播放原版火球蒙太奇，角色从0度转到90度。直接Python接口包装调用没有触发蓝图事件，早期探针的0度结果不能用来判定该接口损坏。

## 修改

`PrototypeFacing.h` 提供即时原型技能的水平转向。传统PrototypeAbility与房间当前使用的PureMassAbility执行路径在成功创建技能运行实例后调用。仅服务端玩家生效；自身技能、垂直/重合目标、非有限目标不转向，非玩家AI保持原路径。未替换玩家或技能名单，不切换战斗后端。

## 验证与边界

Editor目标编译链接成功。`test_25d.Abilities.PrototypeFacing` 为Success，覆盖房间玩家转向、水平姿态、自身与垂直目标保持朝向、非玩家不受影响。测试使用无模型原生Pawn，报告包含武器插槽缺模型警告，不是断言失败。

证据：Saved/GAAuthoring/MonsterWave1/FacingTests/index.json；loadout.json；facing-runtime.json；facing-direct-control.json。

上述自动化是原生转向策略验证，尚未完成鼠标输入→实际原型火球→远端表现的端到端测试。用户PIE验收：进入可战斗房间，停止移动，向左/右/后方释放初始火球，确认角色水平朝向目标，投射物与伤害正常；自身范围技能不应突然转向。移动中施法和多人延迟表现仍需复核。

## 测试阻塞修复

Grux演示玩家蓝图中失效的ResetOrientationAndPosition调用会阻塞PIE。备份后仅删除该节点（没有后续执行节点），编译为BS_UpToDateWithWarnings并保存。模型、动画不变；旧输入映射警告仍存在。备份：Saved/GAAuthoring/MonsterWave1/GruxPlayerCharacter-before.uasset。
