# 第五批原型与组合 GA

## 试玩

打开 `/Game/PrototypeExtensions/Batch5/L_PrototypeLab`，开始游戏，在技能菜单的原型页学习并装备技能。新技能默认不占据按键槽。关卡使用复制的地牢迷宫和 200 个纯 Mass Goblin；玩家保持 Actor、ASC 与动画蓝图。

本批全部新资产位于 `/Game/PrototypeExtensions/Batch5/`。没有覆盖原有地图、角色蓝图、动画或技能资产。

| 资产 | 显示名 | 行为 | MP / CD |
|---|---|---|---|
| GA_Prototype_Attach | 附着脉冲 | 附着敌人并周期触发，可在目标死亡后转移 | 18 / 5s |
| GA_Prototype_Stack | 叠层印记 | 命中叠加印记，三层引爆 | 8 / 0.8s |
| GA_Prototype_Displace | 牵引脉冲 | 将范围内敌人拉向中心 | 16 / 5s |
| GA_StormBrand | 雷霆烙印 | 附着后每秒释放连锁雷电 | 24 / 7s |
| GA_FrostParasite | 寒霜寄生 | 附着脉冲，正常到期留下冰霜地表 | 20 / 6s |
| GA_EmberBrand | 三重焰印 | 火焰投射物叠印，三层范围爆炸 | 8 / 0.8s |
| GA_StormConvergence | 雷链聚爆 | 连锁雷电为各目标叠印，三层爆炸 | 18 / 2s |
| GA_GravityWell | 引力塌缩 | 牵引后延时爆炸 | 25 / 7s |
| GA_BrambleRepulse | 荆棘震退 | 自身范围伤害、击退，在落点留下藤蔓 | 24 / 7s |

## Mass 模式技能点

所有继承 `APureMassGameMode` 的地图（包括现有 Mass 迷宫和新测试关卡）在每个玩家本次游戏会话首次进入时给予 **999 技能点**。服务端发放并复制给客户端；同一会话内消费、重生和换图保留剩余点数，不在换图时补满。

实现是新增的 `UMassStartingPointsSession` 与 `UMassStartingPointsWorld`，没有修改原有角色或 GameMode 文件。新的 PIE/游戏实例重新开始 999 点；仅切换地图不会重新开始会话。这是 Mass 测试模式的规则，普通游戏模式不使用此初始化。

## 组合与扩展

`UExtensionNode` 数据资产通过 `HitChild`、`PeriodChild`、`CompleteChild` 连接。新增 Attach、Stack、Displace 三种机制，并在本批执行器内复用 Projectile、Chain、Burst、Delay、Surface 行为。根节点控制耗蓝、冷却、名称和简短描述；子节点不再次扣蓝。

技能兼容 Mass 实体与 Actor 目标，实际伤害由服务端结算。位移支持按 Actor 类、标签、Mass 类型配置免疫及 Actor 标签减免；使用地面、墙体和导航检查，玩家不受敌方位移节点影响。接受强制位移的 Actor 会中断当前根运动蒙太奇（例如受击或根运动攻击），通过 GAS 同步停止，再由 CharacterMovement 执行位移；免疫目标不受此中断影响。

单次施法最多 64 个运行节点、深度 3、地表 8 块；世界最多 256 条印记记录。印记按施法者、效果标识与目标隔离。达到阈值的致死命中仍在最后确认的位置引爆；施法者死亡、取消或换图清理时不派生爆炸。

施法 GA 为有限瞬发，提交后结束，持续节点由世界管理。需要在施法完成后显式清理时，在服务端调用 `UExtensionWorldSubsystem::CancelCasterEffects(Caster)`（蓝图可调用）。`ASC.CancelAllAbilities` 只取消仍激活的 GA；不会自动撤销已经完成的施法结果。

新测试角色使用独立 `PrototypeExtensions_` 存档命名空间。`PersistentStartupPassives` 默认恢复后台事件监听 GA；需要增加不属于可学习目录的后台能力时，可在新角色蓝图中配置此列表。新 HUD 在已有原型页追加 9 个条目，保留旧目录；描述为三行逻辑文本，按控件宽度自动折行，采用支持中文的字体副本。新动画蓝图复制并重新绑定角色类型，保留移动和待机。

## 验证与证据

资产验证：`Scripts/GA/Batch5/validate_assets.py`；双客户端战斗：`verify_pie.py`；实际菜单：`verify_menu.py`；三次组队传送：`verify_travel.py`。报告在 `Saved/GAAuthoring/Batch5/`，以各文件的 `passed` 和逐项结果为准。

测试脚本只用于编辑器 QA。换图脚本仅创建 `PrototypeExtensions_QA_` 临时存档，并在结束时删除；临时开启的 PIE 无缝换图设置在结束时恢复。`L_PrototypeTravel` 是同一新目录下的换图验证地图。

2026-10-25 验收：Editor 编译成功；完整原生套件 135 项通过（62 Success、73 SuccessWithWarnings、0 失败）；12 个双客户端战斗用例共 89 项检查通过；三次组队传送共 33 项检查通过；换图后菜单学习、选择和描述共 7 项检查通过；资产读回与原文件哈希 84 项检查通过；原 `L_DungeonLabyrinth` 的 999→992 消费与同步 6 项检查通过。截图位于 `Saved/PureMass/FeedbackUI/Batch5_EmberBrand.png` 和 `Batch5_Menu.png`。

构建验证临时对 test_25d 模块禁用了 Unity，以避开原有测试文件合并编译时的符号冲突；测试完成后已按原始字节恢复本地 BuildConfiguration.xml。PIE 已停止，编辑器恢复原迷宫地图，无未保存资产；临时 QA 存档已清除。原框架源码与被复用资产的哈希保持不变。改动保留在 `codex/ga-prototypes-batch5` 工作区，未自动提交或推送。

机制来源及设计依据见 `superpowers/specs/2026-10-25-ga-prototypes-batch5-design.md`，参考了 Path of Exile 的附着烙印、League of Legends 的叠层爆炸和 Warframe 的磁力牵引。数值与实现均为本项目原型配置。
