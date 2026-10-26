# 玩家动画修复与 Mass 使用边界

## 原因与修复

`BP_MassPlayer` 是 `BP_Player` 的副本，父类改为原生 `APureMassPlayerCharacter`，不是 `BP_Player` 的蓝图子类。它仍引用原 `ABP_Player`；该 AnimBP 初始化执行 `Cast To BP_Player`，随后缓存 `BP_Player_Character` 和 `Character Movement`。转换失败后两个引用为空，Ground_speed 一直为 0，移动状态无法正常更新。玩家一直是 Character Actor，此问题不是 Mass 禁用了玩家动画。

新增 `/Game/PureMass/ABP_MassPlayer`，保留原动画状态机、序列、插槽和更新流程，仅将 EventGraph 的玩家类引用及缓存变量类型改为 `BP_MassPlayer`。将新增路径内的 BP_MassPlayer 指向该 AnimBP；原 BP_Player 和 ABP_Player 均未修改。资产重建脚本会保留该新 AnimBP，避免再次复制原玩家时覆盖修复。

验证脚本 `Scripts/PureMass/verify_player_animation.py` 在修复前明确失败于动画玩家绑定；修复后单人 8 项、双客户端 26 项检查通过：四个玩家副本均正确绑定 CharacterMovement，待机/移动骨骼姿势持续变化，动画速度随实际移动达到 600，停下后回到 Idle。每个世界仍保留 200 个 Mass 怪物。

报告：`Saved/PureMass/PlayerAnimation/regression-before-fix.json`、`animation-1.json`、`animation-2.json`、`compile.json`。测试结束已退出 PIE，未保存临时运行状态。

## 用户明确的分工

- 普通怪物：Mass 实体，负责其移动、导航、碰撞、渲染和轻量战斗状态。
- 玩家：Actor/Character、CharacterMovement、SkeletalMesh、AnimBP、ASC/GAS；正式接入可以继续使用 BP_Player。
- 后续精英怪、Boss：Actor/Character 与 GAS，保留独立动画、技能、复杂 AI 和表现能力。

Mass 不要求玩家改类。当前 BP_MassPlayer 是隔离存档、测试装备与同关卡重生的沙盒实现。将正式玩家恢复为 BP_Player 需要把这部分测试专用逻辑与生产逻辑区分，并接入能识别 Mass Entity 和 Actor 两种目标的技能/伤害接口。当前 PureMassTargetData/PureMassRuntime 仍面向实体目标，不能宣称已支持 Actor 精英怪/Boss 的全部战斗流程。本次修复不新增精英怪/Boss、不扩大为战斗接口重构。
