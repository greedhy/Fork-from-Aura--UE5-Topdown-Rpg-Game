# 多类型普通怪增量

用户授权继续开发并增加每层怪物种类，沿用既定 Actor/GAS、服务器权威和整层生命周期。

本轮基线：复用长矛哥布林、弹弓哥布林、食尸鬼；精英/Boss 不变。普通怪总数不增加。
以种子、房间索引、组序号驱动均衡洗牌袋，每组数量足够时覆盖所有类型；小组取洗牌后的前几种。
配置表包含稳定 ID、软类引用、生命值和池资格；空表保留旧配置兼容。加载阶段一次异步预载全部配置类。
池总容量仍为12，按可池化类型均分配额，余数按配置顺序分配；不回收正在使用或同房间隔离的对象。
相比纯加权随机，本轮优先保证类型可见；相比动态淘汰闲置类型，固定配额避免切房间时额外销毁抖动。

执行记录：
- 使用现有 feature 分支和工作区，保留既有修改；不提交。
- 原生测试先验证组合可重复、覆盖、数量和坏配置拒绝，再接入队列、配额和诊断。
- 接入专用关卡配置，仅更新声明的地牢资产；读取共享怪物蓝图，不修改共享 GA。
- 验证构建、自动化、真实资产和可执行的联机场景，记录未验证边界。

## 当前实现和配置

- 测试地图：`/Game/RoguelikeGeneration/Maps/L_RoguelikeRun`。
- 配置：`/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay` 的 `NormalRoster`。
- 当前三项：`GoblinSpear`（长矛近战）、`GoblinSlinger`（弹弓远程）、`Ghoul`（食尸鬼近战），生命值均100，均允许池化。
- 复用原蓝图及职业配置的 GA：前两种职业分别为 Warrior/Ranger，食尸鬼为 Warrior。技能来自 CharacterClassInfo，角色自身 StartupAbility 数组为空不代表未授予技能。
- 精英、Boss 的蓝图和数值不改；它们的普通增援也消费该表。普通房间两波总量仍为8–16。
- 修改 Seed 后重新开始 PIE；同种子、同配置和同房间/组序号重现相同组合。组合在排队阶段决定，不受加载时间、导航尝试次数或对象池命中影响。
- 每个洗牌袋包含每种类型一次。普通波次4–8只，当前三种全部出现；Boss 的两只小组取两种。增加到更多类型时，数量小于种类数的波次不会包含全部类型。
- 配置最多16种，ID和类均不能重复，类不能为空，生命值必须为有限正数。空表兼容旧 NormalClass/EliteClass 回退。
- `NormalPoolCapacity` 仍限制整层总池量；当前12均分为4/4/4。容量不足类型数时，前面的类型优先分到余数，未分到名额的类型使用普通创建/销毁；关闭某项 PoolEligible 后剩余类型重新分配名额。
- `GetRunReport().targets` 新增 `class`、`archetype`、`pool_lease`；`performance.pool_by_type` 提供各类型 quota/total/idle。池台账仅服务器持有，客户端计数为0；客户端表现从复制的实际 Actor 采样。
- `author_enemy_roster.py` 仅更新上述配置资产；`inspect_enemy_roster.py` 只读核对配置和有效技能引用。

## 验证记录

- `roster-red/index.json`：新增组合测试先失败，包含数量、三类型覆盖和坏配置诊断断言。
- `roster-final-build.txt`：完整 Editor target 构建成功，不再需要旧的 DLL 后缀绕行。
- `roster-suite/index.json`：185项项目自动化全部通过（94项干净，91项带既有或测试场景警告），0失败。包含组合确定性、配额总量、三种真实蓝图的两轮布娃娃/休眠/唤醒。
- `author-enemy-roster.json`、`inspect-enemy-roster.json`：资产写入/读取和职业技能引用核验通过；没有保存共享怪物蓝图或 GA。
- `run-checks/roster-duo-01.json`：双人两个普通房间，22步通过，双方各30金币，10次池命中；结束时11个池对象（3/4/4），均闲置。
- `roster-duo-evidence.json`：10项检查通过。四个波次均含三种怪；服务器及客户端均观察到三种怪的可见布娃娃、复用后正常激活、武器保持挂载。
- 独立只读审阅没有发现需阻断的问题。
- 单人首轮 `roster-solo-full-01` 在 Boss 房第109步因 Windows 拒绝替换历史 JSON 回执中断，保留原记录，不能记作通关。验证器现在对原子替换最多尝试5次，每文件最多额外等待100ms，只重试I/O、不重放游戏操作；历史记录仍写不进去则终止。`roster-receipt-red.txt` / `roster-receipt-green.txt` 记录先复现后通过的2项测试（短时占用恢复、永久占用停止）。镜像回执长期占用仍可暂缓，历史记录为权威结果。
- 全新单人 `run-checks/roster-solo-full-02.json`：119步全部通过，17个房间全部 Cleared，最终 Victory，87次池命中；终局池4/4/4且全部闲置。覆盖精英与Boss普通增援，不能用该脚本代替真实玩家战斗平衡验收。
- `roster-cleanup.json`：停止PIE，Seed42/ExpectedPlayers1已恢复，正常退出测试编辑器，没有保存临时测试地图状态。
- 独立 Python commandlet 从磁盘重开后 `inspect-enemy-roster.json` 再次通过（12:27:51），确认三项和有效技能引用已保存；但该进程退出码为1，`roster-reopen.log` 报既有测试类构造时 `Abilities.Attack` 未注册的 GameplayTag ensure，不能记为干净的 commandlet 通过。本轮未修改这项既有启动初始化问题；Editor构建、185项自动化结果与PIE结果分别按上文记录。

## 性能及验收边界

固定池总量并不保证与单类型相同的内存：新增骨骼网格、动画、材质及技能引用会增加常驻资源。需要相同路线、种子、玩家数下重新采样，不能把旧单类型的耗时直接当作本轮性能结果。

自动化通过实际 GE_Damage 杀怪，未逐一验收每种怪物实际攻击动画、投射物命中及战斗平衡；未覆盖打包、独立 Dedicated Server、弱网和长期泄漏。旧池的跨租约持续外发 GE 来源隔离限制仍存在，本轮没有引入新的持续 Buff/召唤怪。
