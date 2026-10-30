# Roguelike 关卡生成增量一实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 在独立测试地图中运行可复现的三房间装配，验证固定入口、真实导航和双人服务端就绪屏障，建立后续完整生成器的运行时基础。

**Architecture:** C++ 数据配置与布局描述不依赖编辑器；服务端确定三房间布局，复制最终清单，各端加载子关卡并验证导航，客户端通过拥有权控制器报告就绪。新资产位于 `/Game/RoguelikeGeneration`，编辑器脚本仅制作和测试资产。

**Tech Stack:** UE 5.8 C++、DataAsset、FRandomStream、ULevelStreamingDynamic、Recast、Actor replication、Unreal Automation、Python/MCP authoring。

**Spec:** `docs/superpowers/specs/2026-10-28-roguelike-level-generation-design.md`，用户已批准全部推荐基线及增量开发。

## Global Constraints

- 当前项目 UE 5.8；保留现有地图、玩家蓝图、PureMass 和 GAS 行为。
- 运行时生成不依赖 Python 或 MCP；服务端输出布局，客户端不独立随机。
- 同 Seed、配置、算法版本产生相同规范化布局；RunId 和加载耗时不进入摘要。
- 全层正式目标仍为主线 10 至 12、总计 14 至 18 房；本增量只验证三个房间，不以此替代完整目标。
- 房间功能、商店、战斗门控、完整主支路、探索地图、局内奖励和打包全流程在后续增量实施。
- 当前编辑器不在运行。沿用当前目录的本地素材；创建 `codex/roguelike-generation` 功能分支，不移动未跟踪资产。
- 任务完成记录及构建/运行报告放在 `Saved/RoguelikeGeneration`；实现结束后独立审阅。

## Review Focus

- 模板缺失或无效端口不能默默产生半张地图：Task 1 配置拒绝测试，Task 3 缺模板失败验证。
- 客户端迟到或回报旧生成 ID 不能提前放行：Task 2 就绪账本测试与 Task 3 双人屏障检查。
- 逻辑连通但真实门槛/导航断开不能判为就绪：Task 3 对每条边完整路径检查。
- 重复模板实例和结束 PIE 不能遗留跨局状态：Task 3 连续启动检查。
- 房间旋转、负向位置和未使用门不能出现越界出口：Task 1 邻接/端口测试与 Task 3 碰撞检查。

## Task 1 可复现布局与配置验证

**Files:**
- Create: `Source/test_25d/Public/Roguelike/DungeonGenerationTypes.h`
- Create: `Source/test_25d/Public/Roguelike/DungeonGenerationProfile.h`
- Create: `Source/test_25d/Public/Roguelike/DungeonLayoutLibrary.h`
- Create: `Source/test_25d/Private/Roguelike/DungeonLayoutLibrary.cpp`
- Test: `Source/test_25d/Private/Tests/DungeonGenerationTests.cpp`

**Interfaces:**
- `UDungeonGenerationProfile`: 房间中心间距、入口定义、动态房间模板数组、生成超时。
- `FDungeonRoomPlacement`: RoomId、Role、TemplateId、Level、Cell、QuarterTurns、bPersistent。
- `FDungeonRoomConnection`: From、To。
- `FDungeonLayout`: Seed、Version、Rooms、Connections。
- `UDungeonLayoutLibrary::BuildAssemblyProbe(Profile, Seed, OutLayout, OutError) -> bool`。
- `UDungeonLayoutLibrary::ValidateLayout(Profile, Layout, OutError) -> bool`。
- `UDungeonLayoutLibrary::CanonicalLayout(Layout) -> FString`；规范化字符串用于摘要与调试。

- [x] 编写并运行测试：三节点两条边、相邻网格、无重叠、入口静态且原点固定，缺模板及无兼容门被拒绝；先观察真实失败。
- [x] 实现独立随机流的三房间探针生成：起点不动，两个后续节点在相邻网格中有限尝试，不产生环路；合法旋转匹配模板门。
- [x] 测试重复 Seed 一致、100 Seed 有空间变化、颠倒模板输入顺序不改变结果、篡改布局被拒绝。
- [x] 使用 UE Automation `test_25d.DungeonGeneration` 验证通过，记录报告。

## Task 2 权威装配与就绪屏障

**Files:**
- Create: `Source/test_25d/Public/Roguelike/DungeonGenerationRuntime.h`
- Create: `Source/test_25d/Private/Roguelike/DungeonGenerationRuntime.cpp`
- Create: `Source/test_25d/Public/Roguelike/DungeonGenerationController.h`
- Create: `Source/test_25d/Private/Roguelike/DungeonGenerationController.cpp`
- Test: `Source/test_25d/Private/Tests/DungeonGenerationTests.cpp`

**Interfaces:**
- `ADungeonGenerationRuntime`: 复制 Layout、GenerationId、Phase、Error；读取 Profile，生成并本地加载；`GetGenerationReport() -> FString` 输出 JSON。
- `ADungeonGenerationController : APureMassPlayerController`: 仅向自己的服务器控制器报告 `(GenerationId, LayoutDigest)`，服务器核对当前布局和参与者。
- `FDungeonReadyBarrier`: `Reset(GenerationId, Digest, ExpectedPlayers)`、`Acknowledge(PlayerId, GenerationId, Digest)`、`IsReady()`；拒绝无效和重复身份计数。
- 首增量人数由独立测试地图的 `ExpectedPlayers` 明确配置，默认为 1；双人验证设为 2。后续接入组队入口时从实际旅行名单获得人数。

- [x] 先测就绪人数不足、重复确认、旧 GenerationId、错误摘要不能放行，再实现账本。
- [x] 服务端构造布局后复制；各端依清单加载两个动态房间，固定入口留在 PersistentLevel。
- [x] 使用稳定实例名加载，等待 Level 可见、碰撞和导航路径通过；导航未完成时重试直至超时。
- [x] 未使用门加阻挡；入口通往动态区的安全门不影响导航的几何验证，但在全队就绪前阻止玩家越过。
- [x] 接收真实客户端拥有权 RPC，所有预计玩家通过后服务器进入 Ready；缺资源或超时进入 Failed 并返回具体错误。
- [x] 运行自动化测试并检查编译无新增错误。

## Task 3 独立模板 地图与真实运行验证

**Files:**
- Create: `Scripts/RoguelikeGeneration/author_probe.py`
- Create: `Scripts/RoguelikeGeneration/verify_probe.py`
- Create: `Scripts/RoguelikeGeneration/editor_bridge.py`
- Create: `Scripts/RoguelikeGeneration/prepare_probe.py`
- Create: `Scripts/RoguelikeGeneration/verify_movement.py`
- Create assets only under: `Content/RoguelikeGeneration/`
- Create: `docs/2026-10-28-roguelike-generation-increment1.md`

**Interfaces:**
- 固定入口与模板使用同一房间尺寸、四向 800 cm 门、400 cm 素材网格；碰撞采用已验证的地牢资产或独立阻挡体。
- 新模板地图、Profile 资产、继承新控制器的副本和复制原模式配置的独立 GameMode，宿主为 `L_DungeonGenerationProbe`。
- 验证脚本只查询 PIE 世界，输出各端布局摘要、加载数、导航及屏障状态到 `Saved/RoguelikeGeneration`。

- [x] 编译与启动后确认新类可用；执行验证脚本在未制作资源状态下得到明确失败，再创建模板与宿主。
- [x] 制作仅含静态环境的两个模板地图和固定入口；配置真正的 NavMeshBoundsVolume Brush 与 Dynamic 导航。
- [x] 复制现有 PureMass 控制器/模式配置到新目录，不修改原资产；设置 Profile 软引用并保存新地图。
- [x] 单人 PIE：两个动态房间均加载、入口到各房间真实导航通过、未使用门封闭、Ready 后可移动。
- [x] 双人 PIE：复制布局完全一致、双方各加载两个实例、两个真实控制器均已报告、服务器最后才 Ready。
- [x] 检查至少两个 Seed、重复启动清理、缺模板错误及超时路径；保存运行报告和截图。
- [x] 运行项目 `test_25d` 自动化测试；记录任何既有失败，不将其隐去或扩大修复范围。
- [x] 独立代码审阅、修复重要问题并重跑受影响验证；更新使用说明、下一增量范围和本计划进度。

## 执行说明

用户已授权采用推荐方案并开始增量开发，因此计划完成后直接实施，不增加一轮方案审批。第一增量只交付运行时装配与联机基础，必须明确报告完整主支路及房间玩法仍待后续增量。实现常规细节由执行者决定，涉及已批准玩家体验的改变再回到设计确认。

## 完成记录

完整 Editor 构建通过；新增自动化红→绿（4 项），最终项目自动化 66/66。真实单人/双人 PIE、两种 Seed、重复启动、缺资源、人数不足超时及物理门口阻挡均已验证。独立审阅唯一 Important 项已以门口 Pawn 胶囊扫掠和接缝支撑检查修复，并有红→绿 PIE 报告。双人移动输入注入及服务器位置复制通过。最后重新加载资产校验通过，无未保存包，宿主恢复 Seed 42 / ExpectedPlayers 1。详细证据见 `docs/2026-10-28-roguelike-generation-increment1.md`。
