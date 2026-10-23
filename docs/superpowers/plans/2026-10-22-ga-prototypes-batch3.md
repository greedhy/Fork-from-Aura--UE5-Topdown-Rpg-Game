# 第三批能力原型

目标：继续扩展可组合的原型库，参考成熟游戏机制并按本项目拆分；可学习GA、数据资产、表现、网络及换图验证全部交付。

设计：
- Cone：施法者/事件位置为原点，鼠标方向为朝向；Radius距离、SpreadDegrees夹角；瞬时每敌人一次，墙遮挡；OnHit/OnExpire。
- Wave：从施法者/事件位置向外扩散，Speed推进，Radius最大半径；首次被波前扫过才命中，不反复伤害、不伤害波前已扫过后才进入的目标；OnHit/OnExpire。
- Returning：直线飞出Range后返回当前施法者；每段每目标一次、两段各至多Count个敌人；DamageFalloff用于回程倍率；墙阻挡，Duration硬寿命；OnHit/OnExpire。
- Emitter：定点周期寻找Radius内最近可见敌人，按目标方向调用OnPeriod子节点；Period间隔、Count成功发射上限、Duration硬寿命；空场不发射不扣次数；无额外MP；OnExpire。是发射行为节点，没有生命值/仇恨/完整召唤AI。

默认：Cone 12MP/3秒/35伤害/350半径/90度；Wave 18MP/4秒/30伤害/500半径/350速度；Returning 15MP/4秒/25伤害/600去程/600速度/回程0.6倍；Emitter 20MP/6秒/6秒寿命/1秒间隔/4次发射，子节点普通火球15伤害。

来源：
- https://webcdn.pathofexile.com/forum/view-thread/3413665/filter-account-type/staff （官方返回投射物支持宝石，抽取往返阶段）
- https://www.leagueoflegends.com/en-us/champions/heimerdinger/ （官方炮台能力，抽取自动选敌发射）
- https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-18-notes/ （官方扇形攻击描述，抽取方向形状）
- https://wiki.guildwars2.com/wiki/Combo （组合场/终结技，启发保持事件接口；不照搬完整跨技能场互动）
- Wave 是将已有Burst拆成空间波前与一次命中记录的本地设计。

步骤：行为测试RED → 实现及全量编译 → MCP资产/目录 → 自动化GREEN → 客机真实输入、子节点与状态复制/清理 → 菜单和三次换图 → 独立只读审查与必要修复。

约束：追加枚举保留旧值；保留现有未提交依赖，不自动提交；原子服务器伤害、费用一次、有限预算；默认不装备。新三项不支持OnPeriod则校验拒绝，Emitter显式要求OnPeriod且禁止无效OnHit。所有变更与测试记录在Saved/GAAuthoring/Batch3。

进度：完成（2026-10-22）。

执行记录：
- 新四项行为测试在Tests-Red均以未实现失败；实现后Tests-Initial完整81项通过，0失败（36项合成World夹具警告）。
- MCP创建4个GA、5个独立配置（含EmitterShot）；目录28条，保留旧条目；资产读回13项通过。
- 客机真实输入26项通过，包含去回状态复制、波前半径复制、4次独立子节点发射与两端清理；菜单4项通过，共19个原型/组合入口。
- 独立审查发现往返帧时间、发射周期补偿、成功发射计数、扇形朝向问题；新增3项测试先失败，再修复通过。原发射器测试改为精确单周期窗口，并检查空场等待不积攒连发。
- Tests-Final全量84项通过，0失败；其中39项含既有资产或合成World夹具警告。完整Editor构建成功。
- 修复后重新通过26项双客户端、13项资产、4项菜单和24项连续换图检查；Dungeon → Dungeon2 → L_DungeonLabyrinth → Dungeon，两位玩家技能类、数量及槽位图标保持一致。
- 测试结束已退出PIE、恢复MainMenu，未保存的资产/地图数量为0。汇总：Saved/GAAuthoring/Batch3/completion.json。
