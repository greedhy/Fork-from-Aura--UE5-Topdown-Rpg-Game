# 第三批：方向、波前、往返与自动发射

入口：技能菜单 → 攻击技能 → Prototypes，滚动列表学习并装备。新技能默认不占用槽位。

资产目录：`/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes`。

| GA / 菜单名 | 行为 | 默认 MP / CD |
|---|---|---|
| GA_Prototype_Cone / Flame Arc | 按鼠标方向打击前方90度、350范围内可见敌人，每个一次35基础伤害 | 12 / 3秒 |
| GA_Prototype_Wave / Arcane Wave | 以施放位置为中心扩散，速度350、最远500，波前扫过造成一次30基础伤害 | 18 / 4秒 |
| GA_Prototype_Returning / Returning Bolt | 鼠标方向飞出600后返回当前施法者位置，速度600；去程25基础伤害，回程60%，每段至多3个不同敌人 | 15 / 4秒 |
| GA_Prototype_Emitter / Arcane Sentry | 在施放位置留下定点发射器，每秒寻找700范围内最近可见敌人，最多发射4次，最多存在6秒 | 20 / 6秒 |

每项都有同名 `DA_Prototype_<名称>`。伤害沿用等级增量和项目已有伤害计算，可修改 Damage / DamagePerLevel。全部由服务器结算，其他客户端接收表现和状态；子节点不重复扣MP。保持原有64节点/3层派生限制。

## 调整与组合

- Cone：Radius决定距离、SpreadDegrees决定夹角（0至180度内，不能为0）；OnHit可接爆炸、地表或领域。射程外可以空放；视觉使用项目爆炸效果排成扇形。
- Wave：Speed控制波前速度，Radius控制终点，Duration是硬寿命；波前已经经过后才走入内部的目标不会补受伤害。墙体遮挡，命中后不会重复伤害。使用原有光环效果随复制的半径扩展。
- Returning：Range控制去程距离，Speed控制飞行速度，Count控制每段不同目标数，DamageFalloff控制回程倍率。墙会终止整个投射物；去程与回程各只能命中同一敌人一次。施法者移动后会追向其当前位置，Duration限制总寿命。去程空放仍会返回。
- Emitter：默认在自己位置部署。Radius是寻敌范围，Period为检查/发射间隔，Count是发射上限。没有可见敌人时不发射、不扣次数，仍受Duration限制。OnPeriod连接独立 `DA_Prototype_EmitterShot`，默认普通火球，可换成Homing、Multishot、Chain等节点。子节点获得选定敌人和面向该敌人的方向；空间位置使用发射器位置。它是可组合的发射行为，不包含生命值、仇恨或召唤物AI。

前三项支持 OnHit / OnExpire，禁止无效的 OnPeriod。Emitter必须配置OnPeriod、禁止OnHit，也可配置OnExpire。取消或施法者死亡不会触发OnExpire。瞬发GA结束后有限寿命节点继续运行，换图由旧World清理。

低帧率时，Returning会把抵达折返点后剩余的帧时间用于回程；Emitter按经过的周期补发，但仍受成功发射次数、持续时间和节点预算限制。空场或子节点创建失败不消耗成功次数，也不会积攒待发队列。Cone的判定、表现和子节点统一使用水平朝向。

## 参考来源与本项目拆分

- [《流放之路》官方3.22说明](https://webcdn.pathofexile.com/forum/view-thread/3413665/filter-account-type/staff)：返回投射物支持宝石启发往返阶段拆分。本项目自行定义两段命中集合、回程倍率和墙体处理。
- [《英雄联盟》黑默丁格官方介绍](https://www.leagueoflegends.com/en-us/champions/heimerdinger/)：炮台能力启发定点自动发射。这里抽取自动选敌与子节点发射，不复刻完整炮台角色。
- [《英雄联盟》官方26.18说明](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-18-notes/)：龙形态扇形攻击的描述启发方向范围筛选。
- [《激战2》官方Wiki组合说明](https://wiki.guildwars2.com/wiki/Combo)：场与终结技的组合方式启发继续保持事件与效果分离。本批没有实现其跨技能场识别系统。
- Wave是从本项目Burst拆出的“传播空间范围＋一次命中”行为。

验证报告：`Saved/GAAuthoring/Batch3/`。网络验证检查远端输入、服务器扣费/伤害、子节点、波前半径和往返阶段复制；未用截图作为美术质量验收。

最终验证：完整Editor编译成功，84项自动化测试通过（39项含既有资产/测试夹具警告），0失败；26项双客户端、13项资产、4项菜单、24项连续换图检查全部通过。修复后的新二进制已重新完成联机验证。详见 `Saved/GAAuthoring/Batch3/completion.json`。
