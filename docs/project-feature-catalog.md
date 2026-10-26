# 当前项目主要功能清单

更新于 2026-10-26。本文按当前源码、资产及已有制作记录整理主要功能，不把设计计划当作已经落地的玩法，也不把同一技能的 Actor / Mass 副本重复算作新机制。

「基础」表示沿用 Aura 课程工程中的能力；「扩展」表示本项目增加或改造的系统。它们共同组成当前工程，但不是所有功能都会在每张测试地图中自动启用。这里是功能索引，不表示本文编写时逐项重新完成了运行验收。

[返回首页](../README.md) · [GA 制作与调用全流程](ga-production-and-runtime-guide.md)

## 1. 角色、战斗与成长

| 功能 | 当前实现 | 来源 / 入口 |
|---|---|---|
| 俯视角玩家控制 | 鼠标选点寻路、WASD 移动、目标高亮、技能目标指示与输入分流 | 基础及适配：[PlayerController](../Source/test_25d/Private/Player/MyPlayerController.cpp) |
| Actor 玩家与动画 | PlayerState 承载 ASC / 属性，Pawn 绑定能力信息、Mesh 与动画；修复 Mass 测试角色的移动 / 待机动画绑定 | 基础 + 扩展：[动画记录](2026-10-23-player-animation-and-mass-boundary.md) |
| GAS 属性与伤害 | 生命、法力、属性成长、抗性、护甲、格挡、暴击、受击、死亡与经验事件 | 基础：[AbilitySystem](../Source/test_25d/Private/AbilitySystem) |
| 等级与点数 | XP、升级、属性点与技能点；技能按等级要求解锁 | 基础：[PlayerState](../Source/test_25d/Private/Player/MyPlayerState.cpp)、[LevelUpInfo](../Source/test_25d/Public/AbilitySystem/Data/LevelUpInfo.h) |
| Actor 敌人 | Character / ASC、AIController / 行为树、受击状态；保留近战、远程、召唤等敌人技能资产 | 基础：[EnemyCharacter](../Source/test_25d/Private/Character/EnemyCharacter.cpp)、[敌人 GA](../Content/BluePrints/AbilitySystem/Enemy/Ability) |
| Actor 敌人掉落 | 死亡调用 SpawnLoot；LootTiers 按物品概率、最大数量和等级配置生成掉落候选 | 基础：[LootTiers](../Source/test_25d/Private/AbilitySystem/Data/LootTiers.cpp)；不代表 Mass 死亡已经复刻整套掉落流程 |
| 战斗反馈 | Actor 与 Mass 的伤害数字、命中特效；玩家 HUD 的生命 / 法力与技能显示 | 基础 + 扩展：[Mass 伤害数字](2026-10-23-mass-damage-numbers.md) |
| 传统玩家技能 | FireBolt、Electrocute、ArcaneShards，以及 HaloOfProtection、LifeSiphon、ManaSiphon 等被动资产 | 基础：[玩家 GA](../Content/BluePrints/AbilitySystem/Player/Ability)；这些资产并非全都完成了直接攻击 Mass 的适配 |

## 2. Mass 怪物与 Actor / Mass 混合架构

| 功能 | 当前实现 | 范围 |
|---|---|---|
| 早期怪物管理 | 空间索引、分级管理与处理器，保留 Actor 怪物的管理方案 | 扩展；[Mass 管理记录](2026-10-23-mass-monsters-guide.md) |
| 纯 Mass 实体 | 普通怪物的生命、移动、路径、攻击和状态保存在 Fragment；没有逐怪 Actor / ASC | 扩展；[PureMass](../Source/test_25d/Private/PureMass) |
| 空间查询 | 邻居、范围查询、稳定实体 ID，以及混合目标查询 | 用于实体移动、选敌与技能命中 |
| 导航与移动 | Recast 查询、路径缓存与查询预算；实体移动由 Mass 处理器执行 | 不为每只怪物建立 AIController / CharacterMovement |
| 碰撞与避让 | 数据胶囊、邻居分离、世界 Sweep、滑动、贴地；技能查询考虑世界遮挡 | 拥挤行为仍是原型实现，未宣称完整群体运动质量 |
| 共享渲染 | 按类型维护 InstancedSkinnedMesh，实体独立动画轨道，待机 / 跑动 / 攻击 | 死亡移除实例；没有完整复制旧 Actor 的受击蒙太奇与血条体系 |
| 网络同步 | 服务端权威实体；共享 Crowd Actor 的 FastArray 差量快照，客户端插值 | 共享 Actor 不等于逐怪代理 Actor |
| 实体战斗 | 实体伤害、状态、死亡和一次经验派发；怪物攻击 Actor 玩家 | 不依赖普通怪物自身 ASC |
| 混合技能目标 | `FPureMassCombatTarget` 同时表达 Actor 与实体 ID；范围、投射、追踪、连锁等路径分流伤害 | [混合目标记录](2026-10-23-mixed-mass-actor-skills.md) |
| 原 FireBolt 兼容 | 增加 Mass Sweep 命中、终止与伤害反馈，修复穿过并推开怪物的表现 | [修复记录](2026-10-23-legacy-firebolt-mass-fix.md) |
| 200 Goblin 迷宫 | 6 个生成区域合计 200 个普通怪物；可配置类型、数量、间距和房间 | [关卡记录](2026-10-23-labyrinth-mass-200.md)；目前属于功能验证 |
| Mass 测试技能点 | 新会话每玩家 999 点；消费、重生、换图保留余额 | [MassStartingPoints](../Source/test_25d/Private/PureMass/Extensions/MassStartingPoints.cpp)；普通模式不采用此规则 |

玩家保持 Actor/GAS。后续精英怪和 Boss 可以沿用 Actor 战斗路径，但「每房间随机精英、词缀、属性增幅、按怪物类型抽取 GA 池」尚未形成完整模式，不能计作已完成内容。

## 3. GA 原型能力清单

前四批有 18 种 `UAbilityPrototype` 行为；Mass 目录提供对应能力副本。第五批增加 3 种机制，并在自己的执行器中实现组合所需的辅助行为。

| 原型 | 能力含义 |
|---|---|
| Projectile | 直线投射物与碰撞命中 |
| Multishot | 多发扇形投射 |
| Burst | 瞬时范围爆发 |
| Beam | 持续引导 / 按住输出、周期伤害与消耗 |
| Surface | 在地面创建有状态效果的区域 |
| Orbit | 环绕火球、补充数量与攻击响应 |
| Field | 固定位置的持续范围伤害 |
| Trap | 预备后触发的陷阱；具体到期行为由配置决定 |
| Homing | 跟踪有效敌人的投射物 |
| Piercing | 按数量上限穿透不同目标，可配置伤害衰减 |
| Chain | 在可见敌人之间依次连锁，避免重复回跳 |
| Cone | 按朝向筛选扇形内目标 |
| Wave | 向外扩散的波前，每目标一次命中 |
| Returning | 飞出后返回；去程与回程分别记录命中 |
| Emitter | 定点周期寻敌并发射子节点，不包含完整召唤物 AI |
| Delay | 延时后执行后续节点 |
| Ring | 带中心安全区的空心环形判定 |
| Line | 按朝向、长度、宽度和高度筛选直线区域 |
| Attach（第五批） | 跟随目标并周期触发，目标死亡后可转移 |
| Stack（第五批） | 按施法者 / 效果 / 目标隔离层数，达到阈值引爆 |
| Displace（第五批） | 牵引 / 击退，包含墙地检查、免疫与位移缩放 |

配置和操作说明：[第一批](2026-10-22-ga-prototypes-guide.md)、[第二批](2026-10-22-ga-compositions-guide.md)、[第三批](2026-10-22-ga-prototypes-batch3-guide.md)、[第四批](2026-10-23-ga-prototypes-batch4-guide.md)、[第五批](2026-10-25-ga-batch5-guide.md)。

## 4. 已制作的组合与独立 GA

| 技能资产 / 名称 | 组合或行为 |
|---|---|
| `GA_FireSeed` / Fire Seed | 火球命中后留下火焰伤害区域 |
| `GA_FrostFan` / Frost Fan | 扇形多发命中后铺冰霜地面 |
| `GA_BrambleMine` / Bramble Mine | 陷阱爆炸并留下藤蔓缠绕区 |
| `GA_StormSeal` / Storm Seal | 雷电区域持续伤害，结束时爆炸 |
| `GA_Aftershock` / Aftershock | 延时 → 环形伤害 → 命中点小爆炸 |
| `GA_FrostFault` / Frost Fault | 直线伤害 → 敌人落点冰霜地表 |
| `GA_RippleMine` / Ripple Mine | 陷阱 → 延时 → 扩散波纹 |
| `GA_HunterSentry` / Hunter Sentry | 发射器 → 追踪弹 → 命中爆炸 |
| `GA_StormBrand` / 雷霆烙印 | 附着 → 周期雷链，可在目标死亡后转移 |
| `GA_FrostParasite` / 寒霜寄生 | 附着脉冲 → 正常结束留下冰霜 |
| `GA_EmberBrand` / 三重焰印 | 火弹 → 三层印记 → 范围火伤 |
| `GA_StormConvergence` / 雷链聚爆 | 雷链 → 各目标独立叠印 → 雷暴 |
| `GA_GravityWell` / 引力塌缩 | 牵引 → 短暂延时 → 爆炸 |
| `GA_BrambleRepulse` / 荆棘震退 | 自身范围伤害 → 击退 → 落点藤蔓 |
| `GA_ArcaneNova` / 奥术新星 | 专用瞬发范围能力，独立消耗、冷却与 Cue；原实现面向 Actor 目标 |
| `GA_OrbitingFireBolt` / 环绕火球 | 装备后默认关闭；按键开关，开启 10 MP、持续 1 MP/s、每 3 秒补充、默认上限 3 个，主动攻击引导火球出击 |

前 8 项组合位于[原组合目录](../Content/BluePrints/AbilitySystem/Player/Ability/Compositions)，并有 Mass 副本；第五批 6 个组合与 3 个新原型位于[扩展目录](../Content/PrototypeExtensions/Batch5)。最新实验场目录为 **26 个前四批条目 + 9 个第五批条目 = 35 个条目**，并非全项目 GA 资产总数。

## 5. 技能管理、UI 与进度

| 功能 | 当前实现 | 入口 |
|---|---|---|
| 授予与激活 | 初始技能、启动被动、按身份 / 输入槽定位 Spec，激活条件、消耗与冷却 | [MyAbilitySystemComponent](../Source/test_25d/Private/AbilitySystem/MyAbilitySystemComponent.cpp) |
| 学习与升级 | Eligible / Unlocked / Equipped 状态、技能点消费、等级要求与技能等级 | 原菜单流程与原型页 |
| 装备与开关 | 进攻 / 被动槽位、替换、卸下、开关技能按 Pressed 切换 | 含持续效果清理与被动恢复适配 |
| 原型菜单 | 可滚动技能列表、选择 / 学习 / 装备、图标、当前与下一等级说明 | [PrototypeSpellTree](../Source/test_25d/Private/UI/Widget/PrototypeSpellTree.cpp) |
| 中文描述适配 | 简短三行逻辑文本、按宽度折行；第五批 HUD 使用支持中文的样式副本 | [ExtensionIntegration](../Source/test_25d/Private/AbilitySystem/PrototypeExtensions/ExtensionIntegration.cpp) |
| 基础 HUD / 属性菜单 | 血蓝、经验与等级、属性加点、技能槽、冷却监听 | [UI](../Source/test_25d/Private/UI) |
| 存档槽与角色进度 | 建立 / 选择存档、玩家等级属性、技能类 / 等级 / 状态 / 输入槽、地图与检查点 | [LoadScreenSaveGame](../Source/test_25d/Public/Game/LoadScreenSaveGame.h) |
| 世界状态保存 | 按地图保存实现 SaveInterface 的 Actor 数据，在载入时恢复 | [MyGameModeBase](../Source/test_25d/Private/Game/MyGameModeBase.cpp)；不是任意对象的自动全量快照 |
| 换图技能恢复 | 全员换图后保留技能和装备，重新绑定 ASC、恢复图标与后台监听 | [技能栏修复记录](2026-10-22-skill-bar-travel-fix.md)、[第五批记录](2026-10-25-ga-batch5-guide.md) |

## 6. 背包与世界拾取

| 功能 | 当前实现 |
|---|---|
| 物品定义 | 数据资产配置 ID、名称、图标、模型 / 拾取 Actor、堆叠上限、拾取模式和使用 GE |
| 背包模型 | 槽位、容量、空槽、堆叠与加入结果；界面通过 MVVM 显示 |
| 服务端操作 | 加入、交换槽位、使用、整组丢弃由服务端处理；客户端经 Controller 请求 |
| 网络复制 | FastArray 槽位与容量 / 修订号同步；变更通知驱动本地 UI |
| 消耗品 | 可用物品向玩家 ASC 应用配置的 GE，成功后消耗数量 |
| 拾取 | 自动重叠或交互拾取，检查距离与有效物品；多人共享世界拾取对象 |
| 丢弃 | 整组生成世界拾取 Actor，配置网络可见性与再次拾取 |
| 持久化 | 服务端本地按 PlayerId 保存背包快照，记录容量 / 数量 / 修订号，并管理会话锁 |

源码：[Backpack](../Source/test_25d/Private/Backpack)、[Controller 交互](../Source/test_25d/Private/Player/MyPlayerController.cpp)、[背包 UI](../Source/test_25d/Private/UI/Widget/BackpackWidget.cpp)。开发记录：[联网背包](superpowers/specs/2026-08-19-networked-backpack-design.md)、[拾取与丢弃](superpowers/specs/2026-08-20-world-pickup-drop-design.md)。设计文件用于说明背景，实际行为以源码为准；当前不是互联网账号仓库或交易系统。

## 7. 模式选择、LAN 房间与组队传送

| 功能 | 当前实现 |
|---|---|
| 单人 / 多人选择 | 存档选择后展示模式页面；单人进入默认地图，多人进入创建 / 加入流程 |
| LAN 房间创建 | OnlineSubsystemNull 会话；显示房间密码、密码设置与当前玩家 |
| 密码匹配加入 | 输入密码搜索局域网会话，匹配后加入，失败显示提示 |
| 房主开始游戏 | 房主操作后全员随服务器进入关卡，保留玩家进度衔接 |
| 房间状态管理 | 忙碌状态、错误提示、离开房间、成员变化与启动条件 |
| 组队传送点 | 全部玩家在触发区域内持续 3 秒后一起切图；条件失效时取消倒计时 |
| 配置出生位置 | 目标地图通过 TravelPlayerStart 的分组与玩家槽位分配出生位置，可集中或分散布置 |
| 多次换图恢复 | 玩家身份、技能、装备与 UI 恢复；对应实际组队换图测试 |

入口：[RoomSubsystem](../Source/test_25d/Private/Online/RoomSubsystem.cpp)、[房间说明](2026-10-22-lan-rooms-guide.md)、[传送点说明](2026-10-22-party-portal-guide.md)。当前目标为同一局域网，未接入互联网账号、在线匹配或公网中继服务。

## 8. 地形、特效与关卡资产

| 功能 | 当前实现 |
|---|---|
| 地表视觉 | 基于已有资源制作岩浆、泥潭、毒性、冰霜、藤蔓地表材质 / 纹理效果 |
| 岩浆 | 接触灼烧与持续伤害、对应视觉 |
| 冰霜 | 减速与对应视觉 |
| 毒性 | 中毒持续伤害与对应视觉 |
| 藤蔓 | 缠绕 / 移动限制与对应视觉 |
| 接触与叠加规则 | 数据资产配置范围、高度、接触、强度与持续时间；状态来源聚合和清理 |
| 混合战斗接入 | Actor 状态组件与 Mass 状态适配，技能可派生地表 |
| 迷宫设计 | 利用现有地牢资产布置墙体、通道、房间，配置导航、传送与怪物生成区域 |

泥潭目前是视觉资源，未单列已完成的泥潭战斗状态。详见[地表制作](2026-10-22-terrain-surfaces-guide.md)与[地形效果](2026-10-22-terrain-effects-guide.md)。

| 关卡 | 主要用途 |
|---|---|
| `/Game/levels/Dungeon`、`Dungeon2` | 原有地牢与地图流程 |
| `/Game/levels/RoomLobby` | LAN 房间大厅 |
| `/Game/levels/L_TerrainSurfacePreview` | 地表视觉预览 |
| `/Game/levels/L_TerrainEffectsTest` | 地形状态测试 |
| `/Game/levels/L_MassDungeonTest` | 早期怪物管理方案验证 |
| `/Game/PureMass/Maps/L_PureMassDungeon` | 小规模纯 Mass 战斗验证 |
| `/Game/levels/L_DungeonLabyrinth` | 200 Goblin 的迷宫功能测试 |
| `/Game/PrototypeExtensions/Batch5/L_PrototypeLab` | 第五批组合技能实验场 |
| `/Game/PrototypeExtensions/Batch5/L_PrototypeTravel` | 技能与组队换图验证 |

## 9. 制作工具与验证能力

- [build-ga skill](../skills/build-ga/SKILL.md)：按需求定位原型、实现、制作资产、接入菜单与存档、验证并交付。
- [MCP 调用辅助脚本](../skills/build-ga/scripts/mcp_call.py)：工程 / 实例绑定、工具发现、文件参数、异步任务查询与回执记录。
- [GA 作者脚本](../Scripts/GA)与 [Mass 作者脚本](../Scripts/PureMass)：创建、配置、保存、读回资产；部分脚本固定批次，不能作为无参数通用工具反复覆盖工程。
- [原生自动化测试](../Source/test_25d/Private/Tests)：背包、联机流程、GA、地形、Mass 及混合目标等核心行为。
- PIE 脚本：远程实际输入、Actor / Mass 战斗、伤害数字、菜单学习、技能点同步、组队换图与存档恢复。
- 验证文档与实机截图：记录历史结果和范围；`Saved/` 的运行报告与缓存不上传。最新批次历史验收见[第五批记录](2026-10-25-ga-batch5-guide.md)。

## 10. 当前未完成或不能据此推断的内容

- 完整暗黑式精英生成规则、词缀池、怪物专属随机 GA 池和完整 Boss 玩法。
- 所有传统 Actor GA 无修改即可攻击 Mass；目前有专门适配和明确的混合执行器。
- 万级怪物性能保证、与 Actor 的同条件性能基准、打包 Shipping 验收。
- 互联网账号、跨公网匹配、中继和商业化联机服务。
- 所有原型跨执行器任意连接、Emitter 等同完整召唤 AI、泥潭已经具备独立战斗状态。
