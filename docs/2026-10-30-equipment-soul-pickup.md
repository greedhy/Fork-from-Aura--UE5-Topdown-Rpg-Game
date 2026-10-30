# 装备 Soul 拾取与装备栏

## 使用流程

打开 `/Game/RoguelikeGeneration/Maps/L_RoguelikeRun`，开始 PIE。出生房间生成完成后会出现五个 Soul：蓝宝石戒指 ×2、红宝石戒指 ×2、铁卫胸甲 ×1。

靠近时显示最近一件装备的名称与 `[E] 拾取`。按 E 通过原有拾取请求进入背包，成功后播放 `NS_SoulPickup`；背包已满或角色不可操作时不移除装备、不播放成功特效。

按 B 打开背包，左侧同步显示装备栏。在背包选中装备后，点击对应装备槽的“装备”或“替换”；“卸下”将装备放回背包。关闭背包也会关闭装备栏。普通药水仍沿用原有使用方式。

## 配置与实现

- `DT_Equipment` 保持装备唯一数据入口。名称、图标、允许槽位、GE、效果等级仍在表中修改；属性数值仍由 `CT_EquipmentStats` 控制。
- 装备行 `PickupActorClass=/Script/test_25d.EquipmentSoulPickup`，`PickupMode=Interact`。同一个拾取 Actor 使用行中的物品 ID 表示内容，不为每件装备复制蓝图。
- `AEquipmentSoulPickup` 复用 `UWorldPickupComponent` 的服务器拾取通路，使用 `/Game/Assets/Effects/Soul/NS_Soul` 和 `NS_SoulPickup`。成功入包后才广播特效并销毁 Actor。
- `UEquipmentPanel` 使用现有 UI 背景资源和背包选中项，按 `EquipmentComponent.AvailableSlots` 生成装备槽；装备操作提交给现有服务器权威装备组件。
- 地图中保存一个 `Equipment_Entrance_SoulSamples` Actor，等待动态地牢出生房间完成后由服务器生成五件测试装备。客户端不会重复生成。删除该测试 Actor 即可移除出生房间测试投放；可在其 `EquipmentNames` 中调整样例。

`Scripts/Equipment/author_soul_pickups.py` 保留装备表原有行与数值，只接入拾取类型并幂等放置样例生成器。UE 导出 JSON 时 `FPrimaryAssetType` 可能为空对象，脚本在重新导入前恢复 `BackpackItem:<Name>`，避免丢失物品身份。

## 验证与验收边界

- `Scripts/test_equipment.ps1 -AllProjectTests`：构建最新模块并执行项目回归；装备测试包含拾取距离、满背包拒绝、重复拾取、实例 ID、装备 GE 和 UI 槽位选择条件。
- `Scripts/Equipment/pie_soul_smoke.py`：专用编辑器真实 PIE 验证出生房间样例、名称、拾取入包、同时显示背包和装备栏、装备/卸下、关闭面板；结束前恢复测试开始时的物品快照。
- PIE 脚本通过延迟的原生请求调用真实 RPC/组件，避免 Python 编辑器脚本保护阻止游戏逻辑。它不模拟物理键盘或鼠标点击，因此快捷键与鼠标手感仍需人工检查。
- 双客户端同时抢同一件装备、远端拾取特效、复制后的装备栏更新仍需双客户端 PIE 验收；单机 PIE 和权威组件测试不能替代该验收。

测试报告位于 `Saved/Automation/Equipment/index.json`、`Saved/Equipment/pie_soul_report.json`；界面截图位于 `Saved/Equipment/`。

## 本次验证结果（2026-10-30）

最终 Development Editor 构建成功。全项目自动化 201 项通过，0 失败、0 未运行，其中装备测试 9 项。最终真实单机 PIE 脚本通过完整流程，并逐字比较恢复后的物品快照与测试前快照一致。已人工查看生成截图，确认装备栏未被裁切，装备图标及中文名称显示正常。输入资产审计确认 IA_Pickup=E、IA_Backpack=B。双客户端及实际键鼠交互仍按上述验收边界检查。
