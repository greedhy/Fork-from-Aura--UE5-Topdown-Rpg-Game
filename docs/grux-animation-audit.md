# Grux 下一批动作检查

2026-10-31。首轮只读资源检查记录，现已完成Grux实现与Boss接入，最终时序和证据见 [Grux制作记录](grux-implementation.md)。沿用既定Grux→蘑菇顺序；恶魔/萨满结果见 monster-wave1-acceptance.md。

源模型 `/Game/ParagonGrux/Characters/Heroes/Grux/Meshes/Grux`。首轮报告 `Saved/GAAuthoring/GruxDesign/source-audit.json`，脚本 `Scripts/GA/audit_grux_combat.py`。

| 动作 | 长度 | 下一步用途 |
|---|---:|---|
| PrimaryAttack_LA / RA | 各1.133s | 左右独立斧击候选，先测weapon_l/r实际刃部轨迹 |
| PrimaryAttack_FourStrikes | 3.700s | 连击候选，每段需独立可辨识预警；不能直接播放四段只提示一次 |
| Stampede | 0.700s | 冲锋循环/短段候选 |
| Stampede_Knockup | 1.533s | 冲锋末段挑飞候选，需独立核对接触与危险区 |
| Ultimate_Roar | 1.400s | 咆哮增益候选，无直接伤害时不绘制虚假伤害圈 |
| Jog_Fwd / Run_Fwd | 各1.533s | 实际速度驱动移动 |
| Death_A | 1.667s | 仅参考表现，不直接替换当前池死亡流程 |

上述动作的11个均匀采样点根位置/旋转均为零，Root Motion和ForceRootLock均关闭。冲锋位移必须由服务端显式移动、碰撞扫掠和边界限制执行，不能依赖源动画推着Actor前进。采样间隔尚不能用于确认接触帧。

模型加载有旧 `Paragon_Proto_Retarget` Rig类型不存在的资源包警告；当前骨骼与动作仍可读取。先确认本骨骼播放链是否受影响，再决定是否需要独立AnimBP；不直接修改源资源或引入示例玩家逻辑。

下一阶段先在带双斧模型上逐帧核对左/右斧击、冲锋挑飞和咆哮，再写入正式技能参数与执行计划。保留现有Boss入口，直到新Boss具备预警、逻辑、表现和生命周期测试证据。
