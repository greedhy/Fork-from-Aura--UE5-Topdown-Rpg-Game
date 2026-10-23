# 环绕火球（Orbiting Fire Bolt）

使用项目 `skills/build-ga` 流程实现的可学习、可按键切换的持续技能。

## 试玩

1. 打开战斗地图，进入技能菜单。
2. 在主动技能树左列中间、普通 FireBolt 上方选择环绕火球图标，消耗技能点学习。
3. 将它装备到主动技能槽，默认关闭。按对应按键开启，瞬间扣除 10 MP，此后每秒扣除 1 MP。首次等待 3 秒出现一颗火球，9 秒后最多三颗。再次按键关闭；长按或松键不改变开关状态。
4. 用 FireBolt 等主动攻击技能指定活着的敌人。火球开始逐颗追击，命中后造成火焰伤害并消失。
5. 目标仍存活时，新补充的火球也会继续攻击。目标死亡、被移除或超出追击距离时，剩余火球返回头顶盘旋；需要新的主动攻击才能再次锁定目标。
6. 再次按键、换槽、被其他技能替换或死亡时关闭，清理所有火球和计时器。每秒扣费时若不足 1 MP，也会自动关闭；不足 10 MP 无法开启。关闭本身免费。重新装备、保存后读档均默认关闭，需要再次按键开启。

新技能可装备到主动槽，不自动占据按键或加入初始装备。新存档和旧存档都会从技能目录发现此技能；没有技能点时，需要按项目原有升级流程获得技能点。

## 资产与配置

资产目录：`/Game/BluePrints/AbilitySystem/Player/Ability/PassiveSpell/OrbitingFireBolt/`

| 资产 | 用途 |
| --- | --- |
| `GA_OrbitingFireBolt` | 可切换技能、伤害与配置引用 |
| `DA_OrbitingFireBolt` | 开启/持续耗蓝、数量、补充、连射、盘旋与追击参数 |
| `BP_OrbitingFireBolt` | 继承新投射物类，复用旧 `BP_FireBolt` 的 Niagara、声音和组件 |

| 数据资产字段 | 默认值 | 含义 |
| --- | --- | --- |
| `ActivationManaCost` | 10 MP | 每次从关闭切为开启时支付 |
| `ManaPerSecond` | 1 MP | 开启后每一秒支付，支付不足时关闭 |
| `MaxFireBolts` | 3 | 盘旋与飞行中的火球合计上限，支持 1–32 |
| `SpawnInterval` | 3 秒 | 从启用开始，每个间隔最多补充一颗；满额时跳过 |
| `LaunchInterval` | 0.35 秒 | 依次发射间隔 |
| `OrbitRadius` / `OrbitHeight` | 65 / 150 cm | 围绕角色中心的半径与向上偏移 |
| `OrbitDegreesPerSecond` | 90 | 盘旋角速度 |
| `ProjectileSpeed` | 900 cm/s | 飞行和返回速度 |
| `MaxTargetDistance` | 2000 cm | 相对玩家的追击距离 |
| `MaxFlightSeconds` | 8 秒 | 单次飞行超时后返回盘旋，仍有有效目标时可重新发射 |

修改配置后重新装备或重启 PIE。数量不会随技能等级自动增加。伤害与燃烧参数复用原 `GA_FireBolt` 的伤害曲线和 `GE_Damage`，升级会沿用这条曲线；开启和持续费用使用独立即时 GE 由原生逻辑结算，没有额外冷却 GE。

## 代码路径与触发约定

- `MyOrbitingFireBoltAbility`：持续 GA；管理开启扣费、每秒耗蓝、补充/连射计时器、目标死亡委托和退出清理。
- `MyGameplayAbility::IsInputToggleAbility` / `ASC::ServerToggleAbility`：按下时向服务端请求切换，验证能力句柄和当前槽位；Held/Released 不重复激活。
- `MyOrbitingFireBolt`：盘旋、追踪和返回；命中结算复用 `MyProjectile`，已命中的同一投射物不会重复结算。
- `MyProjectileSpell::CreateProjectileDeferred`：新旧 FireBolt 共用的生成、伤害参数和 instigator 设置。
- `MyDamageGameplayAbility::SetOffensiveAttackTarget` / `ReportOffensiveAttack`：缓存攻击目标，成功 `CommitAbility` 后才向 ASC 报告。目标数据先于提交或晚于提交都可处理。
- `MyAbilitySystemComponent::OffensiveAttackTargeted`：仅服务端、本角色的已提交主动伤害技能可广播。被动自身伤害不会递归触发。

鼠标目标任务、FireBolt、Beam 和 `CauseDamage` 已接入。ArcaneNova 选择本次范围内最近的有效敌人作为追击目标。将来增加自定义主动 GA 时，应继承伤害基类并在获取目标时调用上述接口；只播放动画或向空地施法不会凭空选出怪物。

新火球蓝图只复用旧蓝图的表现资源。旧 `BP_FireBolt` 自带的延迟碰撞开启和“停止移动就销毁”的图不适用于盘旋，因此从新副本中移除，原蓝图保留。

服务端生成并移动火球、选择目标、应用伤害；客户端显示复制的 Actor 位置，命中特效通过 multicast 播放。盘旋/返回时关闭碰撞，飞行时仅对当前目标结算。当前实现不根据遮挡另选目标。

## 构建与验证

- `Scripts/GA/OrbitingFireBolt/author_assets.py`：在 UE 内创建或更新三项技能资产和技能目录；保留已调整的数据资产数值。
- `Scripts/GA/OrbitingFireBolt/integrate_ui.py`：主机 Python 经 SOMOLMCP 使用主动技能树已确认空闲的 `_1` 按钮，验证控制器、选择和取消选择事件，移除旧被动树按钮；保留其他按钮。
- `Scripts/GA/OrbitingFireBolt/validate_assets.py`：独立检查默认配置、继承、伤害引用、目录和初始装备。
- `Scripts/GA/OrbitingFireBolt/test.ps1`：运行 `test_25d.Abilities.*` 自动化，并回归 ArcaneNova。
- `Scripts/GA/OrbitingFireBolt/verify_pie.py`：在战斗地图 PIE 中激活目录已授予的技能，检查真实 BP_Player 头顶的三颗火球与 Niagara 组件，不写入存档。
- `Scripts/GA/OrbitingFireBolt/verify_toggle_pie.py`：真实 BP_Player 的目录授予、装备默认关闭、切换 RPC、立即扣费及关闭清理检查；不写入存档。
- `Scripts/GA/OrbitingFireBolt/verify_network_input_pie.py`：双人 Listen Server 中，在服务端准备学习和装备，通过远程客户端的 `IA_Input4` 注入检查真实输入事件、切换 RPC、扣费和火球复制；仅临时关闭测试角色的法力回复，不修改资产或存档。

资产修改前的副本、工具回执及独立读回结果位于 `Saved/GAAuthoring/OrbitingFireBolt/<run-id>/`；每轮自动化报告写入 `Saved/Automation/OrbitingFireBolt/<run-id>/`。

自动化覆盖定时补充与上限、修改上限、顺序发射、真实 GE 伤害、ProjectileMovement 碰撞命中、目标死亡/销毁、玩家死亡、结束清理、提交与选目标的先后顺序，以及读档和装备替换。测试中的临时世界不会保存玩家进度。多人客户端表现与实际菜单点击需要独立 PIE 验证，不能从这些服务端测试推断已通过。

2026-10-21 切换版本验证：Editor Win64 Development 完整构建成功；13 项能力自动化全部通过（包含 4 项 ArcaneNova 回归），覆盖按下/长按/松开、开启 10 MP、逐秒 1 MP、资源不足、关闭后停止扣费、换槽和新旧存档恢复。17 项资产独立检查通过，两棵技能树编译为 0 错误、0 警告。

此前 Dungeon PIE 的服务端 BP_Player 检查覆盖装备默认关闭、开启立即扣 10 MP、约 9.7 秒后三颗头顶火球、关闭免费且火球全部清理。该脚本直接调用服务端逻辑，不能作为远程输入或网络传输的证据。

2026-10-22 联机排查发现共享 `FMyGameplayEffectContext` 的两个序列化问题：`GetScriptStruct()` 返回了基类，且复制标记使用了 0–19 位却只写出 19 位。已改为返回实际派生结构并序列化 20 位；新增具体类型与径向参数往返测试，先复现失败，再验证修复。

同时修复 `ServerOnly` 技能的装备元数据复制：UE 默认的 `MarkAbilitySpecDirty` 路径会跳过此类技能已有 Spec 的更新，导致远程客户端保留旧槽位。学习、升级、装备和替换时现在明确要求复制元数据。新增回归覆盖学习、装备、升级、换槽、被替换后的复制标记，修复前五项断言均失败。修复后 Editor Win64 Development 构建成功，16 项能力自动化全部通过，资产独立检查为 17 项通过。

测试脚本注意：UE 的 Python 调用受 `FEditorScriptExecutionGuard` 包裹，`AActor::GetFunctionCallspace` 会因此强制本地执行。不能将客户端 Python `call_method('Server...')` 视为真实远程 RPC。联网测试在服务端准备装备，再将输入注入排到后续游戏帧，使开关 RPC 经过正常网络通路。`InputActionValue` 的原生字段也不适合经过 Python 反射复制，因此使用 `inject_input_vector_for_action`。

修复后的双人 Listen Server PIE 实测通过 16 项检查：客户端收到装备槽位、默认关闭、远程输入开启、长按/松开保持开启、服务端与客户端均有三颗火球、首次只扣一次 10 MP、随后逐秒扣 1 MP、法力复制、再次按下关闭、长按不重新开启、双端清理及关闭后停止扣费。记录的扣费序列为 `10, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1`。新编辑器会话中未再出现 `ClientEffectApplied` RPC 读取不匹配或 FastArray 非法字段终止错误。

此联机脚本在服务端准备学习和装备，客户端通过 Enhanced Input 注入触发正常游戏帧中的事件；没有模拟实体键盘或点击菜单。实体键盘/菜单点击、多人下的完整追击命中特效、专用服务器及延迟/丢包场景仍未独立验收。追击、伤害、目标死亡返回和补充由原生自动化覆盖。

验证记录汇总：`Saved/GAAuthoring/OrbitingFireBolt/delivery-validation.json`。

本次调整保留原资产路径及 `Abilities.Passive.OrbitingFireBolt` 身份标签，以兼容旧存档；目录类型已改为 `Abilities.Type.Offensive`。旧存档中的被动槽会解除，技能保持已学习及原等级，重新装备到主动槽后可按键开启。
