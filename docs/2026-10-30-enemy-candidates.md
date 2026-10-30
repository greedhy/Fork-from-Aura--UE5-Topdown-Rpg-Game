# 怪物资源检查与接入建议（2026-10-30）

本次只读检查，未改动游戏资产。证据：Saved/GAAuthoring/EnemyCandidates/89cd80e3ffe64419bdb7ae301e8e4ee2/inventory.json；audit.log。

| 候选 | 实际检查 | 接入判断与建议 GA |
|---|---|---|
| StoneGolem | SKM_StoneGolem、对应Skeleton、ABP_StoneGolem绑定；5种攻击、3种受击、3种死亡及移动动作 | 首选新精英。普通Character父类，需新建EnemyCharacter派生。建议重锤近战、预警地震、盾击；具体动作分配须预览攻击1–5后确定。 |
| Paragon Grux | 108动画序列、6蒙太奇、1骨骼，角色已绑定模型及AnimBP | 适合Boss。示例玩家BP有过时ResetOrientationAndPosition函数错误、旧输入映射警告；另建GAS敌人BP，复用资源。建议双斧连击、冲锋挑飞、咆哮增益。 |
| 哥布林/长矛/弹弓 | 现有EnemyCharacter派生，模型与AnimBP已绑定 | 可优先作为接入基线；突刺、远程抛射等需核查已有技能避免重复。 |
| 萨满 | 现有EnemyCharacter派生，Shaman模型及AnimBP绑定 | 适合支援敌人：远程施法、地面危险区或召唤。 |
| 食尸鬼 | 现有EnemyCharacter派生，Ghoul模型及AnimBP绑定 | 适合普通近战：左右爪击，后续可增加有预警的突进。 |
| 恶魔近战/远程 | 现有EnemyCharacter派生，共享Demon模型及AnimBP；有攻击、投掷、甩尾动作 | 可扩为精英：甩尾范围攻击、投掷弹、近战连击。 |
| Shroom蘑菇 | 发现模型与Idle/Bounce/Attack序列，未在已扫描角色目录找到对应GAS敌人BP | 次批：弹跳攻击、孢子区域；需补AnimBP、受击/死亡方案。 |
| RPGHeroSquad / BattleWizardPolyart | 模型、动作与演示蓝图存在 | 属英雄/人形资源，可做敌对冒险者、法师；本轮不计为现成怪物。 |

StoneGolem包内的Demo人偶动画不应计入石巨人可用动作；分件模型和换肤也不等于独立怪物。

## 下一步建议

1. 先做StoneGolem精英：复用BP_EnemyBase的ASC、属性、阵营、AI和死亡流程，替换模型与动画；明确插槽、蒙太奇Slot与命中Notify，再制作2–3个GA。
2. 再做Grux Boss：独立EnemyCharacter蓝图，不依赖出错的示例玩家控制逻辑；预览Root Motion、攻击窗口与恢复段后确定技能节奏。
3. 补强现有恶魔/萨满作为低成本普通怪与精英变化。
4. 当前DungeonRunProfile仅有NormalClass/EliteClass/BossClass单槽。单一精英/Boss可分别配置；多种普通怪混编需增加带权重、数量和房间条件的候选配置，再接入生成器。
5. 每只怪物按逻辑、动画命中时刻、特效、自动测试、人工PIE流程交付；覆盖死亡打断、冷却、友军过滤、墙体阻挡，以及对象池复用后的GA/特效清理。

## 验证边界

本轮核实资产类型、注册表骨骼关系、角色CDO父类与模型/AnimBP绑定，没有运行怪物战斗或预览所有动作。只读命令行检查生成了完整报告，但进程因项目原生标签启动ensure和Grux示例蓝图编译错误退出1；不能称为全项目编译通过。具体GA设计为建议，尚未新增技能或改动出怪配置。
