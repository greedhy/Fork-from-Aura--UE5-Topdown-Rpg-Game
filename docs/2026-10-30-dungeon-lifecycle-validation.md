# 第三阶段：异常生命周期与实际交互验收

用户完成保存后继续；开始时编辑器 PID3604 位于 `L_RoguelikeRun`、PIE 停止、无脏包。本轮使用已准备的请求，每个异常场景均启动独立双人 PIE。

## 双人异常场景

原始报告位于 `Saved/RoguelikeGeneration/run-checks/`，前缀 `lifecycle-prepared-20261030-`。

| 场景 | 动作数 | 结果 |
|---|---:|---|
| gathering-retreat | 19 | 通过。离开取消集结，重新全员进入后正常刷怪、清房；回访不重复发奖，双方各15金币。 |
| required-removal | 10 | 通过。Destroy 必杀目标后两端 Failed / TargetRemovedWithoutKill:A1，目标和待生成队列归零，双方0金币。 |
| clear-revive | 53 | 通过。真实精英GE打倒一人，仅存活队友清房后自动复活，双方各90金币；比对首尾两人 Pawn/ASC 路径均保持不变。 |
| all-down | 51 | 通过。双人全灭后两端 Failed / AllPlayersDown，目标和待生成队列归零；双方各60金币，未发未完成精英房奖励。 |

汇总：`Saved/RoguelikeGeneration/lifecycle-results-20261030.json`。这些是当前同进程 PIE 的真实 GE/销毁与服务器规则证据；移动仍由扫掠路径驱动，不代表键鼠战斗、断线重连或打包运行。

## 单人真实输入

输入通过 computer-use 的 Windows 窗口按键/鼠标完成；验证脚本只准备位置与战斗进度、读取交互后的状态。目标交互没有用 `interact`/Controller 请求代替输入。

- 宝箱：`lifecycle-input-chest-setup-01` 准备到 R03，随后重新定位并核对实际 Controller 的 can_interact（`lifecycle-input-reposition-01`）。画面显示 F 领取提示后实际按 F，界面显示已领取2件物品；`lifecycle-input-chest-key-03` 确认待领0、背包revision1、金币30。
- 重复按 F：`lifecycle-input-chest-repeat-01` 通过，revision仍为1，没有重复发物品。
- 未通过的前置尝试保留：`lifecycle-input-chest-key-01` 对应输入工具拒绝发送；`-02` 未领取且观察到玩家位于交互范围外、Controller can_interact=false。这两份报告均保留失败，不能计为成功。

## 实际输入发现的点击穿透修复

初次商店点击验证了30金币扣款和单次交付，但重复点击售罄按钮触发了场景自动寻路。玩家离开商店中心，后续场景准备报告 `lifecycle-input-rest-setup-01` 因 `WaypointStepTooLarge` 失败；未将该报告当作休整通过。

原因：禁用按钮不处理鼠标事件，而面板 Border 为 SelfHitTestInvisible，未接住冒泡事件。修复限定在 `DungeonRunWidget`：Border 改为 Visible，接住鼠标按下、松开和双击；启用子按钮仍先处理事件，根 Canvas 继续 SelfHitTestInvisible，让面板外保留游戏输入。

新增 `DungeonRunWidgetTests.cpp`，直接经 Slate 事件方法验证禁用按钮及父面板行为。修复前 `ui-input-red/index.json` 中1项用例失败（3个预期断言）；修复后 Editor构建成功，`ui-input-green/index.json` 的42项 Roguelike 原生测试通过（25项无警告、17项带警告），包含本轮UI用例。该测试不替代实际 Slate 命中与路由，仍需真实点击复验。

独立只读审阅无阻断问题，要求额外核对启用按钮、售罄按钮及面板外移动。未修改 GAS资产或房间资产。尚未测试的打包、独立进程、延迟及长期内存回收，仍属于后续阶段。

## 修复后真实输入复验

新编译版本在编辑器 PID22544 中启动新单人局；`lifecycle-ui-fixed-shop-setup-01` 准备到商店。以下报告均在 `run-checks/`，全部通过：

| 报告 | 观察及断言 |
|---|---|
| lifecycle-ui-fixed-buy-01 | 实际点击可购买按钮，金币165→135，背包revision4，商品售罄。 |
| lifecycle-ui-fixed-disabled-01 | 实际双击售罄按钮，金币135、背包revision4不变；玩家XY连续1.5秒保持(0,-7200)，未启动自动寻路。 |
| lifecycle-ui-fixed-rest-key-01 | 真实技能消耗法力后实际按F休整，法力310→320，Controller rested=true。 |
| lifecycle-ui-fixed-rest-repeat-01 | 再次用真实技能消耗法力至310，实际再次按F；法力仍310，休整不可重复使用。 |
| lifecycle-ui-fixed-world-click-01 | 在面板外实际点击地面，观察玩家移动约191.32cm，确认未把游戏区域一起拦截。 |

`lifecycle-ui-fixed-summary.json` 保留位置对比和报告列表。场景准备使用脚本移动/伤害以及技能激活，目标购买、售罄双击、休整和地面移动均来自真实窗口输入。四项双人故障验收发生在本轮UI补丁之前；补丁后重跑42项原生关卡测试和上述单人实际输入，不声称补丁后又完整重跑双人全流程。

最终停止PIE，默认地图仍为 `L_RoguelikeRun`，本轮已恢复单人设置；读回PID22544、dirty=[]。本轮解决了实际输入验收发现的面板点击穿透问题；独立进程/打包联机、Cook资源与长期性能仍未验收。
