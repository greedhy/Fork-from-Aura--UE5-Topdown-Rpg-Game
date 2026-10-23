# 组合 GA 与第二批原型

技能菜单 → 攻击技能 → Prototypes。列表可滚动，技能默认可学习、未装备；学习后通过原有装备流程放入技能栏。没有替换存档中的已有技能。

## 四个组合 GA

资产目录：`/Game/BluePrints/AbilitySystem/Player/Ability/Compositions`。

| GA / 菜单名 | 组合 | 默认 MP / CD |
|---|---|---|
| GA_FireSeed / Fire Seed | 火球命中 → 半径180的火焰区域，持续4秒，每秒伤害 | 18 / 4秒 |
| GA_FrostFan / Frost Fan | 3发扇形投射物，每次命中在地面铺4秒冰霜，减速敌人 | 20 / 5秒 |
| GA_BrambleMine / Bramble Mine | 地雷预备0.75秒，触发后爆炸 → 4秒藤蔓缠绕地面 | 20 / 5秒 |
| GA_StormSeal / Storm Seal | 半径250的雷电区域，持续3秒，结束后爆炸 | 22 / 6秒 |

对应 `DA_<名称>` 是根节点，后缀 Field / Ground / Burst 是子节点。可修改伤害、范围、持续时间及 OnHit / OnPeriod / OnExpire。节点只在根 GA 激活时扣费，子节点不重复扣 MP；技能地面只影响敌人。

OnExpire 表示正常结束，包括投射物命中、地雷触发和自然超时。Bramble Mine 无人触发时也会在6秒到期后爆炸并留下藤蔓。取消/死亡清理不会触发 OnExpire。Field 在到期前每周期执行一次；3秒区域的1秒周期在第1、2秒造成伤害，第3秒执行结束爆炸。

所有地表节点（包括命中派生的节点）都会向下寻找地面；找不到支撑面时不创建悬空地表。现有原型使用项目粒子资源，数值属于原型调试值。

## 验证记录

结果位于 `Saved/GAAuthoring/Compositions`。第二批原型必须在 `stage1-gate.json` 通过后开始实现。

第一阶段门禁：完整自动化72项、双客户端组合25项、菜单4项通过后才开始第二批。最终自动化77项全过（32项含合成测试世界的夹具警告，0失败）；组合联机25项、新原型联机22项、资产22项、菜单4项及连续三次换图24项（含能力类逐项对比）的最终结果由 `completion.json` 汇总。

## 第二批：三个新行为原型

资产目录：`/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes`，每项包含 `GA_Prototype_<名称>` 和 `DA_Prototype_<名称>`。

| 原型 / 菜单名 | 行为与可调参数 | 默认 MP / CD |
|---|---|---|
| Homing / Homing Bolt | 必须点选敌人；Speed=600，HomingTurnRate=360度/秒，最远路径1200，最多4秒。目标失效或碰撞后结束 | 12 / 3秒 |
| Piercing / Piercing Bolt | 直线穿透最多Count=3个不同敌人；每个目标只伤害一次，DamageFalloff=0.8；墙会阻挡 | 15 / 3秒 |
| Chain / Chain Lightning | 点选首个敌人后，寻找Radius=450内最近且可见的敌人；共Count=3个，间隔Period=0.4秒，DamageFalloff=0.75，不回跳 | 20 / 4秒 |

穿透与连锁的第N个目标伤害为 `DamageAtLevel × DamageFalloff^(N-1)`，最终还经过项目原有伤害计算。Count包含首个目标。Range限制首段射程/投射物累计路径，Duration是硬性寿命；连锁还需要足够的Duration来完成跳转。

可以继续将新原型的 OnHit 接到已有 Burst / Field / Surface，例如“追踪弹命中铺毒地”“穿透弹每次命中爆炸”“连锁命中生成冰面”。根 GA 负责一次扣费和冷却，所有节点共用施法者、等级、最多64个运行节点与最多3层派生的预算。追踪和连锁作为子节点时，需要上游提供有效敌人目标；不能将它们接到一个没有目标的任意空间事件上并期待自动寻敌。

新三个原型支持 OnHit、OnExpire；OnPeriod 尚不支持，配置校验会拒绝该连接。连锁的 OnExpire 使用最后命中位置及最后命中的目标。根地表技能找不到落点时直接取消，不扣 MP、不进入冷却。

美术复用项目已有火球、爆炸、奥术、光环和雷电束 Niagara。当前验证覆盖网络 Actor/端点复制和实际菜单构造；未将截图渲染质量作为自动化通过条件。
