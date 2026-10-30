# Roguelike 玩法接入第三增量实施计划

> **For agentic workers:** Use superpowers:executing-plans with independently owned Mass/economy subtasks and a fresh whole-increment review. Steps below track completion.

**Goal:** 在独立的可玩宿主中完成房间遭遇、混合敌人、战斗门控、个人清房收益、宝箱、三项商店、休整及 Boss 出口。

**Architecture:** 保留现有生成核心与两个验证宿主。新的 RunDirector 在装配 Ready 后接管玩法门，服务器账本决定房间、目标与个人交易；拥有的 Controller 承担请求及个人状态复制。PureMass 增加可选房间约束和原因明确的生命周期通知，未注册约束的旧场景保持原行为。

**Tech Stack:** UE 5.8 C++、GAS/Actor 与 PureMass、复制 Actor/Controller、UMG、现有背包、MCP/Python。

**Spec:** `docs/superpowers/specs/2026-10-28-roguelike-level-generation-design.md` 第 6～8、12～13 节。用户已经批准全部推荐基线，并要求按进度继续；无需再次批准。

## Global Constraints

- Base `04b0711`，沿用 `codex/roguelike-generation` 及已绑定编辑器的工作区；保留无关素材。
- 仅服务器开启遭遇、登记目标、结算奖励和交易；客户端不能提交价格、数量、完成结果或余额。
- 全局同时最多一个遭遇；所有当前连接且存活队员进入安全区域才关门刷怪。已阵亡者不参与集结，清房复活；全灭结束，不沿用旧自动重生。
- 普通房 8～16 个 Mass，活动普通怪不超过 30；本增量采用两波普通怪。精英与 Boss 使用既有 Actor 原型、血条和攻击，Boss 增加明确的必杀/可回收召唤账本。
- 只有正常死亡完成必杀目标；重复通知无效，异常回收明确失败并提供退出，不冒充清房或无限等待。
- 个人宝箱按剩余数量保留待领；商店每人三项、每项单件且限购一次。原型普通清房 15、精英 30、Boss 50 金币，商品 30/45/60，保证主线可负担最低价。数值为本次实现调试配置。
- 休整每人一次，恢复最大生命与法力各 30%，不超过上限。局内货币不写旧金币/技能点字段。
- 门、出生、玩家位移、怪物目标和伤害遵守当前房间边界；已清房可回访，不重刷。
- 新地图 `/Game/RoguelikeGeneration/Maps/L_RoguelikeRun` 和专用复制 Blueprint/Profile；原 Probe 和 Floor 地图保留用于生成回归。
- 本轮提供可操作的状态/交互界面和共享已探索图；完整断线恢复、独立进程及打包性能仍按第四阶段验收。

## Review Focus

- 最后一名敌人的死亡回调、下一波生成和重复通知重入：只能清房、奖励一次。
- 角色死亡后的旧自动重生定时器：不能绕过全灭或清房复活，不能清空既有技能配置。
- 背包部分接收与同步通知重入：满包不扣款，宝箱不丢失剩余，错误玩家背包不能被使用。
- 位移技能越过关闭门、全局 AI 找到门外玩家、旧投射物跨房：不能跳过遭遇或在门外结算攻击。
- 同一个 Seed 的新局与旧局 RPC：RoomId 相同也不能污染新的领取和商店记录。

## Task 1 可独立验证的账本与底层接口

**Files:** 新 `DungeonRunModel.h/.cpp`、`DungeonRunTypes.h`、`DungeonRunEconomy.h/.cpp`；`PureMassSubsystem.h/.cpp`、新 `PureMassEncounterTypes.h`；新 `DungeonRunModelTests.cpp`、`DungeonEconomyTests.cpp`、`DungeonMassEncounterTests.cpp`。

**Interfaces:** `FDungeonEncounterLedger` 管理波次/必杀与可回收目标；`FDungeonRunModel` 管理房间集结/完成、门开放规则与有界网格移动检查。`UDungeonRunEconomy` 以 RunId 初始化并提供 CreditClear/ClaimChest/Purchase/Rest；交易结果含成功、交付、剩余、错误。PureMass 暴露 `OnMonsterRemoved(Id,Room,Reason)`、`RemoveMonster`、`SetRoomBounds`、`ClearRoomBounds`；Killed 只由真实伤害产生。

- [ ] 测试与可编译空实现先行，完整构建并观察新增前缀 `test_25d.Roguelike.` 的 RED。
- [ ] 实现纯状态机、显式波次窗口、去重及异常失败；验证集结撤销、前进门与回访、跨格跳过关闭门拒绝。
- [ ] 实现 Mass 生命周期和可选边界；真实 Mass 世界测试含客户端拒绝、外部销毁与缓存路径越界。
- [ ] 实现真实背包/ASC 事务：个人隔离、部分领取、满包/余额不足、重入、归属、休整上限、新局隔离。
- [ ] 新增测试全部 GREEN，原有测试继续通过。

## Task 2 运行时与可操作内容

**Files:** 新 `DungeonRunProfile`、`DungeonRunDirector`、`DungeonRunController`、`DungeonPlayerCharacter`、`DungeonRunWidget`；最小 Actor AI/伤害边界适配；新 `author_run.py` 和 `/Game/RoguelikeGeneration/Gameplay` 专用资产。

**Interfaces:** Director 消费 GenerationRuntime 的清单/Ready，只在其后创建玩法门；复制房间进度、遭遇剩余和局状态。Controller 请求包含 RunId/RoomId/Action/OfferIndex，服务器验证控制器归属、位置、存活及状态；个人视图单独复制。`GetRunReport` 返回结构化状态和错误供 MCP 验证。

- [ ] Ready 后初始化房间；未访问不刷怪，全员集结、分波、Actor/Mass 共用账本、正常清房开门与发币。
- [ ] 复用可辨认的近战精英及 Boss 资产、血条；Boss 召唤登记原因，死后停止追加且清理非必杀目标。
- [ ] 专用角色倒地/复活保留 ASC 与背包，玩家及敌人活动受玩法门约束；全灭与异常销毁显示明确结束状态。
- [ ] 实现 F 互动、个人三项购买按钮、宝箱待领与休整反馈、局状态和已探索/相邻门提示；Boss 胜利后提供出口和返回菜单。
- [ ] 制作并保存独立宿主和配置，重开逐项读回；不改旧验证地图或共享 GA 资产。敌人复用现有 GA，按 build-ga 的资产/效果读回规则验证。

## Task 3 实际验证与交付

**Files:** 新 `verify_run.py` / 辅助验证脚本、第三阶段使用文档；Saved 下保存独立报告。

- [ ] 至少一局单人和一局双人完整主线，覆盖所有房型进入、完成和回访，支路奖励也单独覆盖。
- [ ] 验证门外等待、取消集结、两波计数、Actor/Mass 混合、必杀召唤、Boss 死后回收、玩家倒地/清房复活与全灭；验证服务器实际伤害与客户端操作。
- [ ] 同时/重复交互、跨房/过期 RunId 请求、余额不足、满包与重入不重复发货、不错误扣款。
- [ ] 真实门碰撞/位移边界、双方房间/个人状态复制、已探索 UI 与未探索图形不泄露；重复开始结束检查清理。
- [ ] 完整 Editor 构建、全项目自动化及前两阶段回归；独立全增量审阅并处理重要问题。
- [ ] 恢复宿主默认 Seed42/单人、停止 PIE、核验保存资产，交付使用说明和可核查结果。

## 用户优先级调整 2026-10-29
默认波次和召唤全部 Actor/GAS Blueprint，Mass后续仅少数怪物使用。覆盖上文混合基线；先改默认生成、普通怪配置、可回收Actor账本，再更新验证驱动并重新验收。旧混合报告不作为新方案完成证据。
