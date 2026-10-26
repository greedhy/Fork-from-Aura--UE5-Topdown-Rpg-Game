# 原版 FireBolt 与 Mass 命中、伤害浮字修复

## 原因

1. 原 FireBolt 的命中入口是 `AMyProjectile::OnSphereOverlap`，接收 Actor 并查找目标 ASC。纯 Mass Goblin 没有 Actor/碰撞组件，因此不会触发这个入口。
2. 实际 `BP_FireBolt` 先使用 NoCollision，再在 BeginPlay 延迟 0.1 秒开启 QueryOnly；其 Pawn 响应被蓝图覆盖成 Block。Mass 移动使用 Pawn 通道做数据胶囊查询，因此会把火球视为障碍并执行推出重叠位置的处理。
3. 上一版 Mass 浮字直接以隐藏的 PlayerController 为组件 Owner。UE 的屏幕 WidgetComponent 要求 Owner 可见，因而数字对象存在、文本正确，屏幕上却没有显示。

## 修复范围

- 仅在启用了 `UPureMassSubsystem` 的世界，给原版 `BP_FireBolt` 实例挂载 `UPureMassLegacyProjectile`。使用明确的类白名单，避免改变环绕火球等特殊投射物的生命周期。原 `BP_Player`、`GA_FireBolt`、`BP_FireBolt` 及基础框架未修改。
- 监听投射物实际移动产生的 TransformUpdated，在引擎派发该段移动的重叠通知前，对世界障碍、Actor 敌人和 Mass 胶囊进行排序。保留原移动组件的追踪、重力、子步进及 0.1 秒枪口免碰撞时间。
- Mass 最先命中时，服务器只结算一次原技能配置的伤害/灼烧，复用 Mass 抗性、护甲、格挡、暴击、死亡和经验流程，停止并销毁火球。Actor 最先命中时保留原重叠/GAS 处理。
- 火球实例的 Pawn/WorldStatic/WorldDynamic 响应恢复为原生类使用的 Overlap；Mass 的移动、贴地和障碍查询忽略 Projectile 物体类型，避免火球把怪物推走。
- 浮字改由每个本地控制器的一个可见、不复制、无碰撞 Actor 承载，并明确设置 LocalPlayer。继续复用原浮字蓝图与自动回收。没有逐怪 Actor。

## 验证与工具

- 修复前 `Saved/PureMass/LegacyFireBolt/red/index.json` 明确失败：原火球越过 Mass 后 HP 仍为 1000、火球未消失。
- `Saved/PureMass/LegacyFireBolt/tests/index.json`：123 项原生回归，60 成功、63 带原有资源警告成功，0 失败、0 未运行。包括高速扫掠只命中第一个敌人、墙遮挡、敌方火球不伤害 Mass 友军，以及即使投射物阻挡 Pawn 也不会推怪。
- `Scripts/PureMass/verify_legacy_firebolt.py`：双客户端 PIE 中临时让远端玩家使用原 BP_Player，经正常 Enhanced Input 激活原 FireBolt；记录真实扣血、投射物消失、浮字、位置不变，并检查 Actor 怪物的 GAS 伤害和后方 Mass 不被穿透伤害。
- `Scripts/PureMass/verify_damage_numbers.py`：Mass 技能、归属客户端、数值、致死伤害、DOT 合并、房主和组件清理。
- `PureMass.QA.CaptureUI <PIE实例> <名字>`：仅 Editor + 开发测试构建注册，保存指定客户端的 Slate 截图和 `bAddedToScreen` 读回到 `Saved/PureMass/FeedbackUI/`。避免 HighResShot 不含 UI，以及普通 Shot 在多 PIE 视口中捕获到第一个窗口的问题。

联机脚本仅修改 PIE 实例，不保存角色、技能或存档。不要在 Python Slate 回调中直接调用客户端 GAS 激活 RPC；该回调不处于 PIE 游戏世界的调用上下文，可能把 Server RPC 本地执行并递归。脚本使用 Enhanced Input 注入，让实际游戏 tick 执行激活。

最终运行结果：浮字脚本 17 项检查、原版 FireBolt 脚本 12 项检查全部通过。原 BP_Player 的火球让 Mass HP 从 100000 降到 99900，怪物位置未变，投射物消失；另一发命中 Actor Goblin 后其 HP 降到 99958.68，后方 Mass 未受伤。`FeedbackUI/original-firebolt-remote.png` 已实看远端 `100`，`FeedbackUI/remote-quiet-25.png` 已实看远端 `25`。配套 JSON 确认 Owner 可见且组件进入屏幕层。

最终 Editor 编译记录：`Saved/PureMass/LegacyFireBolt/build-final.log`。构建临时对 test_25d 模块关闭 Unity，避开既有测试源文件中的 FWorld 名字冲突；完成后恢复 `Saved/UnrealBuildTool/BuildConfiguration.xml`。未改旧测试文件或 Build.cs。恢复关卡与无脏包读回见 `Saved/PureMass/LegacyFireBolt/restored.json`。

这是原 FireBolt 的兼容接入，不会自动将任意旧的 Actor-only GA 转换为 Mass 技能。玩家和 Actor 精英/Boss 继续使用 Actor/GAS；普通 Goblin 继续使用纯 Mass 数据实体。
