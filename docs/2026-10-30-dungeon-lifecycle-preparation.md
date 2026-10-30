# 第三阶段：异常生命周期与交互验收准备

后续执行已完成四项双人异常场景及单人实际交互，并修复售罄按钮点击穿透；详见 [执行与修复记录](2026-10-30-dungeon-lifecycle-validation.md)。以下保留当时的准备状态，不作为最新执行结果。

## 本轮范围

沿用现有计划推进异常生命周期和实际输入验收。开始时编辑器 PID43004 处于 `L_RoguelikeRun` 且无脏包；随后另一项石像鬼测试切换到了临时地图。用户明确选择让石像鬼测试先完成，本轮转为离线准备，不再操作编辑器。

初次 `lifecycle-removal-20261030-01.json` 最终为 `RequestTimeout`，没有执行任何场景动作（receipts 为 0）。只读探针确认实际 PIE 地图为 `/Temp/UEDPIE_0_Untitled_1.Untitled`，没有关卡 Director/Generator。本次没有通过游戏内生命周期验收，也没有执行实际按键或点击验收；不把该超时归因于游戏清房逻辑。

## 已完成修改

- `verify_run.py` 新增 `expected_map`，默认完整包路径 `/Game/RoguelikeGeneration/Maps/L_RoguelikeRun`。去除 UE 的 PIE 实例编号后比较完整路径，避免另一目录下的同名地图混淆。
- 实际 PIE 地图不匹配时，在玩法动作执行前明确报 `UnexpectedPIEMap`，输出期望与实际路径。没有 PIE 时继续等待；正确地图尚未生成 Director 时仍可等待初始化。既有最后一步 EXIT 的结束判断保持在地图校验之前。
- 这不是编辑器独占锁，不能解决同地图、并行使用同一 PIE 的所有竞争；正式验收仍需明确使用顺序。
- 新增地图校验回归（先观察失败，再实现后通过），新增四类场景的离线契约测试。补充 EXIT 结束顺序回归后，共 12 项测试通过；测试覆盖不等于游戏运行结果。

执行离线回归：

```powershell
& C:/ProgramData/anaconda3/python.exe -m unittest discover -s Scripts/RoguelikeGeneration/tests -p 'test_*.py'
```

## 已生成、尚未执行的请求

目录：`Saved/RoguelikeGeneration/LifecyclePrepared/20261030-01/`。`manifest.json` 记录来源布局、请求标识、动作数量、SHA-256 和 `prepared_not_executed` 状态。全部基于 Seed42，期望双人；每项必须使用全新的 PIE 局，不能在已修改的旧局继续播放。

| 请求 | 动作数 | 关键验证 |
|---|---:|---|
| gathering-retreat.json | 19 | 一人进房后退出，取消集结；全员进入再刷两波；回访不重复奖励。 |
| clear-revive.json | 53 | 精英真实 GE 打倒一人，存活队友清房后自动复活；禁止直接调用复活 fixture。 |
| all-down.json | 51 | 两人均由真实伤害打倒，明确 AllPlayersDown；清空目标和生成队列，不发未完成精英房奖励。 |
| required-removal.json | 10 | 真正 Destroy 必杀 Actor，明确 TargetRemovedWithoutKill；消失不能当作击杀，金币不增加。 |

离线测试额外保证所有伤害/销毁前等待生成队列清空，默认场景不使用 Mass 或直接复活动作。待生成期间取消队列是另一项专门场景，此四项不声称覆盖该竞态。

## 编辑器空闲后的顺序

1. 重新核对编辑器地图、未保存内容、当前是否 PIE，明确独占使用；不要沿用本轮开始时的状态。
2. 加载 `L_RoguelikeRun`，临时配置双人，逐项创建新局并执行对应请求。已执行过的 request_id 不能重用；若需修订请求，使用新标识并保留原回执。
3. 复活场景额外比对同一玩家首尾 Pawn/ASC 标识；每项读取服务端、客户端结果，以及对象池和生成队列，而非只看工具返回成功。
4. 实际输入验收：进入宝箱房前后记录背包版本/待领数量，用拥有者窗口实际按 F；重复按键不得重复领取。商店实际点击购买按钮，核对只扣一次款；休整通过实际 F 验证一次性状态。脚本位移和伤害可用于准备场景，但不能替代这几项真实输入。
5. 停止本轮 PIE，恢复 Seed42/单人，核对测试产生的临时改动与用户内容；分别记录通过项和未验证项，再决定是否进入打包/独立进程阶段。

游戏 C++、怪物资产和地图资产本轮均未修改；没有重新声称原生全项目测试、PIE 异常场景或键鼠/UI 验收通过。

独立只读审阅通过，无阻断问题；所建议的 EXIT 顺序回归已补充并通过。
