# 第四批原型与组合 GA

在技能菜单 → 攻击技能 → Prototypes 中学习并装备。新增项默认不占用按键，沿用技能点、升级、存档和多人流程。

## 三个新原型

| GA / 菜单名 | 行为 | MP / CD |
|---|---|---|
| GA_Prototype_Delay / Delayed Pulse | 原地留下标记，1秒后产生范围爆发，基础伤害30 | 14 / 4秒 |
| GA_Prototype_Ring / Arcane Ring | 内半径100、外半径360的空心环形攻击，基础伤害30，中央安全 | 16 / 4秒 |
| GA_Prototype_Line / Arcane Lance | 按鼠标方向攻击前方长650、宽140的矩形区域，基础伤害35 | 14 / 3秒 |

资产目录：`/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes`，配置为同名 `DA_Prototype_*`。

- Delay：ArmDelay决定等待时间，OnExpire决定触发的子节点。固定在施放/事件位置，不跟随施法者或目标移动；取消、施法者死亡不会派生。要求Duration不短于ArmDelay。自身无伤害，不支持OnHit/OnPeriod。
- Ring：InnerRadius、Radius控制内外边界；目标中心落在两条边界之间才命中。ShapeHalfHeight控制允许的高度差，默认120。支持OnHit/OnExpire。
- Line：Range为前方长度，Width为完整宽度，ShapeHalfHeight为高度容差。根能力从施法者位置向鼠标水平朝向，光标超过Range仍可指定方向；实际命中由服务器按矩形范围和逐目标遮挡判定。子节点从上个事件的位置沿继承朝向。支持OnHit/OnExpire。

两种形状均为瞬时判定，忽略友军和死亡角色，墙体遮挡；不是持续伤害地带。它们不接受OnPeriod配置。子节点共享施法者、等级、取消标记和64节点/3层限制，不额外扣蓝。

## 四个组合

| GA / 菜单名 | 节点组合与效果 | MP / CD |
|---|---|---|
| GA_Aftershock / Aftershock | Delay → Ring → 命中Burst：等待1秒，内100外420环形造成24伤害，命中点再产生半径90、12伤害爆点 | 22 / 6秒 |
| GA_FrostFault / Frost Fault | Line → 命中Frost Surface：650×140裂隙造成22伤害，敌人脚下生成持续3秒的冰霜减速地表 | 20 / 5秒 |
| GA_RippleMine / Ripple Mine | Trap → Delay → Wave：陷阱触发后等待0.6秒，释放半径450、速度400的波纹，基础伤害28 | 20 / 6秒 |
| GA_HunterSentry / Hunter Sentry | Emitter → Homing → 命中Burst：每秒向700内最近可见敌人发射追踪弹，至多3发；弹体18伤害，半径100爆点10伤害 | 24 / 7秒 |

资产目录：`/Game/BluePrints/AbilitySystem/Player/Ability/Compositions`。每个组合都有独立的根配置和子配置，修改组合不会改变独立原型示例。

Aftershock的环形判定保留中心安全区，但命中敌人的小爆点仍可能波及靠近它的其他敌人。RippleMine沿用Trap现有语义：敌人进入触发范围，或12秒自然到期，都会进入后续延迟与波纹。HunterSentry空场不扣发射次数，最多存在5秒，不包含生命值、仇恨或召唤物AI。

数值均指基础伤害，最终伤害仍经过项目抗性、护甲等计算。DamagePerLevel控制升级增量；冰霜减速复用地表系统，直线本身使用已有Damage.Magic。

## 表现与验证

Delay和Ring复用光环；Ring显示内外两圈；Line沿攻击方向排列现有火花；组合复用爆炸、波纹、冰霜地表和追踪弹效果。行为和表现复制分别检查，未以截图作为最终美术质量验收。

本批是对现有时间与空间行为的本地拆分，不新增外部美术资源。运行证据保存于 `Saved/GAAuthoring/Batch4`；最终结果见 `completion.json`。

最终验证：完整Editor构建成功；91项自动化测试通过、0失败（46项含既有资产/合成World夹具警告）；43项双客户端输入与复制、36项资产读回、4项实际菜单构建/选择、24项连续三次换图检查通过。菜单现有26个原型/组合入口。独立审查发现的远光标阻止Line施放问题已由入口测试RED→GREEN验证修复。

联机夹具额外检查真实光标射线命中敌人，避免另一名QA玩家挡住瞄准导致错误判断。测试结束已退出PIE并恢复MainMenu，未修改用户存档。
