# Roguelike 关卡生成：增量三——房间玩法接入

本增量在已有的主支路关卡上接入战斗、清房奖励、宝箱、商人、休整和 Boss 出口。使用独立宿主 `/Game/RoguelikeGeneration/Maps/L_RoguelikeRun`；原 `L_RoguelikeProbe`、`L_RoguelikeFloor` 继续作为生成与装配回归地图。

**验收状态：集成验证中。** 原生首轮全套测试、保存资产读回和单人首个战斗房已通过；完整单人/双人流程、独立审阅修复后的最终测试仍待更新。下述玩法说明描述当前实现与操作方式，不代表文末所有验收项已经完成。

## 试玩入口与操作

1. 使用完整编译并重新启动后的 Editor 打开 `L_RoguelikeRun`。
2. 停止 PIE 后，在 Outliner 选择 `RG_GenerationRuntime`。单人使用 `Seed = 42`、`Expected Players = 1`，直接 Play。
3. 双人测试将 `Expected Players` 改为 2，并在 Play 设置中选择 2 名玩家、Listen Server。当前验收使用同一编辑器进程内的双人 PIE；人数仍由宿主参数指定。
4. 等待双方完成装配、碰撞与导航检查。入口开门后沿主线前进。重新生成或开始新局需要重新启动 PIE/世界；修改 Seed 不会在已运行的世界内热重建。

移动、攻击、技能槽与背包沿用原 Mass 玩家配置。房间服务点位于房间中央，靠近约 3 米内才允许交互：

| 服务 | 操作与反馈 |
|---|---|
| 宝箱 | 按 **F** 领取个人奖励；界面显示尚未领取的数量。背包满时可以整理后回来领取。 |
| 商人 | 靠近后显示三项商品及购买按钮，列出价格、金币不足或售罄状态。点击明确的商品按钮购买。 |
| 休整 | 按 **F** 恢复生命与法力；每人每个休整房仅能成功使用一次。两项均已满时不消耗机会。 |
| Boss 出口 | Boss 房完成后，中央出口启用；按 **F** 结束本层并返回菜单。终局界面也提供返回菜单按钮。 |
| 状态与小地图 | 显示当前房间、波次、剩余目标、个人金币和交互反馈。小地图只绘制队伍已经访问的房间与连接；当前房间另显示相邻门通向的房型和锁定状态。 |

F 键与复制来的输入映射已做资产读回检查，没有现有映射冲突。实际按键、按钮焦点与双端显示的最终验收见文末状态表。

## 当前房间规则与数值

全局同时运行一个战斗遭遇。第一名存活队员进入未清理的战斗房时进入集结状态，此时可以退回已通过的区域；通向后续房间的门保持关闭。所有当前连接的存活队员进入房内安全区域后，房间关门并生成敌人。倒地队员不参与集结条件。未进入的房间不预先刷怪，已清理房间可自由回访且不重复刷怪或结算。

| 房型 | 当前配置 |
|---|---|
| 普通战斗 | 总计 8～16 个 Mass 敌人，分两波；第一波必杀目标清空后才生成第二波。数量由 Seed 与房间确定，活动目标总量受 30 个上限约束。 |
| 精英 | 1 个既有哥布林长矛 Actor 原型，加 4 个必杀 Mass 敌人；精英等级 2、生命 450。 |
| Boss | 1 个既有恶魔战士 Actor 原型，等级 3、生命 1500；开场另有 2 个必杀 Mass 与 2 个可回收 Mass。 |
| Boss 阶段 | 半血时追加一次 2 个必杀 Mass；有独立的范围脉冲预警，预警 1.25 秒后结算，半径 550 cm、基础伤害 20；冲击后 4 秒启动下一次预警。 |
| Boss 死亡 | 停止追加召唤与脉冲，回收仍存活的可回收目标；剩余必杀目标仍须击败，全部完成后才开出口。 |
| Mass 原型 | 当前专用哥布林配置为生命 100、速度 180 cm/s、攻击伤害 4，复用现有渲染与动画资源。 |

精英和 Boss 复用原有近战 GA、血条与动作；Boss 脉冲由新的房间运行时通过原生 GE 结算。专用敌人副本已设置为允许运行时生成后由 AI 接管。原敌人、共享 GA 和旧验证地图不因本增量而改写资产。

战斗目标账本同时记录 Actor 与 Mass。只有真实击杀才能完成必杀目标；重复死亡通知不会重复结算。必杀目标被异常销毁或回收会产生明确失败，不能将“对象消失”当作击杀而开门。门碰撞、位移检查、怪物活动区域与伤害边界共同约束跨房行为。

### 个人收益

| 项目 | 当前基线 |
|---|---|
| 清房金币 | 普通房 15、精英房 30、Boss 房 50；每位队员独立到账，同一房间只结算一次。 |
| 宝箱 | 从生命药水、法力药水中确定一种，数量 1～2；每人分别领取。部分装入背包时保留剩余数量。 |
| 商店 | 生命药水 30、法力药水 45、QuestRelic 60；每人每项只卖一件且限购一次。QuestRelic 是现有收藏物，没有新增使用效果。 |
| 交易 | 服务器决定商品、数量、价格与结果。余额不足、满包、过期局 ID 或错误房间请求不能扣款或发货。 |
| 休整 | 恢复最大生命与最大法力各 30%，不超过各自上限；每人每房一次。 |

局内金币属于本次 Run 的账本，不写入原金币或技能点字段。以上是本次原型配置，可以在 `/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay` 调整；自动复测脚本中的金币断言使用当前基线，改数值后应同步更新断言。

### 倒地与复活

专用玩家角色倒地后停止移动与技能激活，保留同一 Pawn、ASC、技能等级和背包，等待队友完成房间。清房后在安全位置以最大生命与法力各 30% 复活。恢复此前启用且仍处于装备状态的被动监听，不自动重启攻击开关或已卸下的被动。

全员倒地时本局失败并提供返回菜单入口，不执行原角色的自动重生与技能重建流程。当前倒地表现采用隐藏角色、保留观察相机的原型方式；完整观战相机和美术表现不属于本轮已验证结论。

## 实现分工

| 位置 | 职责 |
|---|---|
| `DungeonRunTypes.h`、`DungeonRunProfile.h` | 房间/局阶段、个人视图、敌人和收益配置。 |
| `DungeonRunModel.h/.cpp` | 与世界无关的集结、门通行、波次、必杀/可回收目标和一次性完成策略。 |
| `DungeonRunDirector.h/.cpp` | 等待 Generation Ready，服务端启动遭遇、生成目标、处理死亡、Boss 阶段、清房、失败与边界。 |
| `DungeonRunPresentation.cpp` | 门与服务点组件、个人交互校验、视图更新、返回菜单和结构化运行报告。 |
| `DungeonPlayerCharacter.h/.cpp` | 本局专用倒地与原地复活生命周期，保留 ASC 和既有配置。 |
| `DungeonRunController.h/.cpp`、`DungeonRunWidget.h/.cpp` | 拥有者 RPC、输入门控、F 交互、商店按钮和共享已探索地图。 |
| `DungeonRunEconomy.h/.cpp` | 服务端个人金币、宝箱余量、限购、休整与事务重入保护。 |
| `PureMassEncounterTypes.h`、`PureMassSubsystem.h/.cpp` | 原因明确的移除通知、房间边界与伤害来源限制；没有注册房间约束的旧场景沿用原行为。 |
| Actor/GAS 接入处 | 目标选择、目标解析和伤害入口检查当前 Run 的战斗规则；专用敌人不额外掉落原随机战利品。 |
| `Private/Tests/Dungeon*Tests.cpp` | 账本、真实 Mass 世界、背包/ASC 事务、角色生命周期和 Actor 战斗边界回归。 |

新增地图与 8 个专用 Gameplay 资产均位于 `/Game/RoguelikeGeneration` 下。玩家动画蓝图也单独复制为 `ABP_DungeonPlayer`，其 EventGraph 的角色类型引用已指向 `BP_DungeonPlayer`，避免复制玩家后仍然向旧 `BP_MassPlayer` 转型。

## 调试与 MCP 复测

优先读取实际世界中的两个 JSON 接口：

- `ADungeonGenerationRuntime::GetGenerationReport()`：布局、Seed、摘要、装配阶段、导航/碰撞检查与就绪错误。
- `ADungeonRunDirector::GetRunReport()`：RunId、局阶段、活动/集结房间、门状态、每房波次与剩余必杀数、玩家位置/生命/法力/金币/交互记录、背包数量与修订号，以及服务端目标明细。

先区分“几何尚未 Ready”和“玩法阶段失败”。例如 `AllPlayersDown` 表示队伍全灭；`WaveSpawnFailed` 表示遭遇生成失败；`TargetRemovedWithoutKill:<目标>` 表示必杀目标未经击杀被移除。保留 RunId、Seed、房间 ID 和具体错误，便于复现。客户端报告中的玩家控制器与个人视图只对应其拥有者；服务端报告用于核对全队和目标账本。

| 脚本 | 用途 |
|---|---|
| `author_run.py` | 在停止 PIE、原生类型已完整编译的编辑器中创建并保存独立资产；完整输出已存在时只重新读取验证，部分输出或外部脏包会报错。 |
| `retarget_run_animation.py` | 外部 Python 通过绑定的 MCP 修正专用动画副本的角色引用，保留回执并校验原资产哈希。完成后重新运行 author 脚本读取保存结果。 |
| `inspect_run_assets.py` | 读取输入映射、专用角色/敌人、动画、GA/GE 引用和共享 GA 哈希，不修改资产。 |
| `verify_run.py` | PIE 内按请求执行有界动作与断言，采集双方真实世界状态；支持位移、Mass/GE 伤害、真实技能激活、拥有者交互及异常移除场景。 |
| `make_run_scenario.py` | 外部 Python 从捕获的布局生成完整单人/双人请求；先遍历支路，最后进入 Boss。它只生成 JSON，不启动编辑器或执行玩法。 |
| `editor_bridge.py` | 绑定当前工程与编辑器实例，序列化当前世界操作并保存 MCP 回执。 |

最小只读采集请求写入 `Saved/RoguelikeGeneration/run-check-request.json`：

```json
{
  "request_id": "capture-run-001",
  "expected_worlds": 1,
  "expected_players": 1,
  "timeout": 90,
  "actions": [{"action": "capture"}]
}
```

随后在当前 PIE 的 Unreal Python 环境执行 `Scripts/RoguelikeGeneration/verify_run.py`。通过 MCP 时使用 `console_exec` 的 `py "脚本绝对路径"` 命令，经 `editor_bridge.py` 提交。结果写入 `run-check-response.json`，并保留在 `run-checks/<request_id>.json`。每次新请求使用新的 ID；相同 ID 的已有回执不会重放可能已经执行的操作。结果未知时先检查既有回执与 PIE 状态，不要换 ID 盲目重发。

完整流程请求可以在项目根目录生成：

```powershell
python Scripts/RoguelikeGeneration/make_run_scenario.py `
  --capture Saved/RoguelikeGeneration/run-checks/solo-initial.json `
  --party 1 --request-id solo-full-001 `
  --output Saved/RoguelikeGeneration/run-check-request.json
```

双人改为 `--party 2`，并匹配宿主的 Expected Players 和 PIE 人数。从入口开始新局后再执行生成的请求，不能直接接在一局已清过房间或有背包物品的状态上。`--dry-run` 只检查并输出规划；`--rest-mode skip` 会明确省略休整使用验证；默认在休整前激活真实的自身 Burst 技能消耗法力，再测试休整。`--exit` 才会在最后触发队伍返回菜单，默认停在胜利状态供检查。

Seed42 的脚本规划覆盖 17 个房间，生成单人 95、双人 127 个动作；按当前基线，每人清完所有房间并购买一件最低价商品后应剩余 200 金币。该数字是脚本断言目标，不能代替运行结果。脚本采用胶囊扫掠路径与实际伤害 API；按键手感、技能动画、按钮焦点仍需另外验证。调用回执成功也不等于玩法成功，必须检查业务报告的 `passed`、`error`、逐步 `checks` 和最终世界状态。

## 验证记录

以下为文档草稿时已存在并读取的证据；最终审阅修复后应更新这一表，不能将旧版本报告当作新版本验收。

| 项目 | 当前证据与状态 |
|---|---|
| 首轮完整 Editor 构建 | `Saved/RoguelikeGeneration/run-green-build.txt`：成功。 |
| 首轮全项目原生自动化 | `Saved/RoguelikeGeneration/run-green/index.json`：173/173 通过。涵盖既有功能及本轮新增模型、Mass、事务、倒地/复活、战斗边界测试。 |
| 新资产保存后读回 | `authoring-run.json`：`passed=true`、`animation_retarget_required=false`、无脏包；完整输出重新读取验证通过。 |
| 输入、动画与共享 GA | `run-asset-inspection.json`、`run-animation-retarget.json`；F 映射无冲突，专用动画引用已修正。 |
| 单人实际战斗房 | `run-checks/solo-room1-r3.json`：通过；实际两波 Mass 战斗、清房、开门和 15 金币结算。 |
| 完整单人主线与支路 | **待最终运行报告更新。** |
| 完整双人、个人交互与复制 | **待最终运行报告更新。** |
| 倒地/清房复活、Boss 阶段、失败注入、真实输入与 UI | **待最终场景验收记录更新。** 原生测试通过不替代这些场景结果。 |
| 独立审阅修复后的构建与全套回归 | **待最终报告更新。** |

第四阶段继续覆盖独立进程/打包联机、断线与重连恢复、旅行队伍动态管理、资源 Cook 与性能验收。本轮的同进程 PIE 与原生测试不能替代这些结论。

## 2026-10-29 用户调整：Actor/GAS 优先

本要求覆盖此前混合怪物基线。普通怪、精英、Boss、必杀和可回收召唤全部优先使用挂载 GAS 的 Blueprint；Mass 保留底层实现，后续仅用于少数怪物，默认不生成。

普通怪新增 NormalClass / NormalHealth 配置，暂未指定 NormalClass 时复用专用 GAS 哥布林 Blueprint，普通生命100、精英450、Boss1500。Boss身份显式区分，召唤怪不会覆盖Boss引用。可回收Actor单独记账。

此前solo-full-02与duo-full-03通过的是旧混合方案，不能替代新方案验收。待办：Actor版验证驱动、完整单人/双人PIE、故障场景及最终资产读回。当前构建结果见 Saved/RoguelikeGeneration/run-actor-build.txt。

## 2026-10-29 动态怪物第一增量

已接入异步加载怪物软类引用（整局预加载，尚非相邻房间按需卸载），持续持有加载句柄并在EndPlay取消/释放；加载失败及超时明确失败。默认生成全部Actor/GAS。

服务器生成队列每帧默认至多2个、生成预算1ms（单次Spawn不可抢占）；预先登记必杀目标，待生成也阻止清房。请求记录RunId/房间，过期失败，团灭/退出清空队列；Boss死亡取消未生成的可回收目标。正常尸体仍沿用原寿命销毁，尚未实现对象池或销毁预算队列。

GetRunReport新增 pending_enemy_spawns、last_spawn_ms、last_spawn_count。配置见DungeonRunProfile的SpawnsPerFrame、SpawnBudgetMs、EnemyLoadTimeout。

构建证据：run-stream-tests-build.txt。原生回归：run-stream-tests/index.json（以实际结果为准）。新增PendingSpawnReservations验证先击杀已出现目标不提前清房。尚需真实PIE刷怪/首次资源加载性能、全Actor单人和双人完整流程、新验证驱动，以及生命周期清理全面验证。对象池在数据证明必要后接入。

关卡本身：主支路布局、全层房间装配和就绪检查已有实现与前阶段验证；基于玩家距离逐房流送/卸载没有完成，不能把怪物异步加载视作房间流送完成。

## Actor流程验收（2026-10-29，续）

验证驱动新增kill_actor_group，通过真实GE伤害清除当前账本Actor；每次批量击杀前等待pending_enemy_spawns归零，Boss半血召唤及必杀/可回收计数保持独立断言。Windows状态镜像文件被读锁占用时不再中断玩法验证，权威身份回执写入失败仍报错。

actor-solo-02：118动作通过，全部17房间完成，最终200金币；采样未出现Mass，观察到待生成队列，采样单帧生成数最大1，生成耗时最大约3.665ms。后者表明1ms是不可抢占的调度预算，并不是单次Spawn耗时上限；采样不是完整性能trace，也不是打包性能验收。

双人同一局完成：actor-duo-01在第131步位移已执行后达到300秒总时限；检查RunId和完整位移回执，actor-duo-01-continuation仅复核该位置再执行132步之后的剩余流程，19动作通过，最终两端17房Cleared、双方200金币。旧报告保留passed=false（超时），不伪称单请求完整通过。

本轮只修改验证脚本，实际操作使用GE伤害和胶囊扫掠，非键鼠战斗验收。全Actor方案普通波次、精英、Boss半血必杀增援、可回收随从、远端宝箱/商店/休整与奖励同步已经获得上述PIE证据。异常销毁、团灭/复活及完整首次加载性能仍需专门场景，房间流送尚未实现。

## Actor异常生命周期验收（2026-10-29）

本轮仅修改验证脚本，游戏C++未改动。

- actor-removal-01：必杀Actor真实Destroy后明确Failed/TargetRemovedWithoutKill，目标与待生成队列清空，金币0；没有把消失当作击杀。
- actor-revive-01：双人53动作通过，一人由精英真实GE打倒，仅存活队友清房后自动复活；首尾Pawn和ASC路径一致，双方存活、各90金币。没有调用直接复活fixture。
- actor-all-down-01：双人全灭后AllPlayersDown，活动目标与待生成队列清空，未发精英房奖励。
- actor-pending-cancel-02.json：观察到尚有4个待生成请求时异常销毁必杀Actor，随后Failed、队列0、目标0，并继续观察2秒不再刷怪。初版探针遍历无World的默认对象报错，保留actor-pending-cancel.json，不计通过。

报告均位于Saved/RoguelikeGeneration，前三项在run-checks/中。测试使用真实GE/Destroy API而非键鼠战斗，仍不代表打包/独立进程、断线重连或性能验收。普通背包/技能完整保留由既有原生回归覆盖，此次PIE额外确认Pawn/ASC实例没有替换。

当时已恢复测试宿主Seed42/单人并停止PIE；原MCP编辑器地图恢复/Game/levels/Dungeon，无脏资产。当时建议的逐房加载/卸载及延后对象池，已被后续用户决策覆盖：采用整层创建、整层销毁，并已接入常见怪物有限对象池，见 `2026-10-29-dungeon-enemy-pool.md`。

## 2026-10-30 战斗闭环复核

地板修复后优先复核上次伤害断言失败，并补齐失败回执。当前编辑器首房真实伤害及完整单人流程通过，旧失败根因尚未确认；本轮结果、性能采样边界及剩余计划统一记录在 [战斗验收记录](2026-10-30-dungeon-combat-acceptance.md)。历史测试数量和旧混合方案结果不作为当前版本新验收证据。
