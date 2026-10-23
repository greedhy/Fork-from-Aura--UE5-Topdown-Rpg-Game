# 换图后技能栏为空修复

双客户端实际复现：Dungeon → Dungeon2 后，服务器与客户端的技能数量均保持 5 个，但两端技能栏图标全部为空。技能授予和槽位保存仍存在，问题发生在 UI 初始化通知。

## 修改

- `AddCharacterAbilitiesFromSaveData` 原先设置 `bStartupAbilitiesGiven` 并广播 `AbilitiesGivenDelegate`，而 HUD 使用的是 `bStartupAbilityGiven` / `AbilitiesGiven`。统一为 HUD、初始授予、客户端复制共同使用的一套状态和事件，同时迁移被动特效的就绪判断。
- `OverlayWidgetController` 在绑定依赖时只订阅事件；初始技能快照移至 `BroadcastInitialValues`，由 HUD 在 `SetWidgetController` 完成后触发。这样技能先到和界面先到两种顺序都能填充技能栏。
- 客户端 `OnRep_ActivateAbilities` 等待所有技能引用解析后再发布就绪事件，并对后续复制更新重新广播。GAS 在引用未解析时会安排重试，原先只广播一次的逻辑会吞掉重试和稍后到达的槽位信息。
- 不重新授予技能、不改装备槽位或用户存档。

## 验证

- 修复前实际 PIE 报告：`Saved/TravelValidation/SkillBar/aaddb2aec30b4c60ba97a39d95d7936f.json`。技能数量检查通过，两端图标检查失败。
- 完整 Editor 构建：`Saved/TravelValidation/SkillBar/build-final.log`。
- 63 项自动化测试全部通过（19 项有既有测试场景警告），包括新增的 `test_25d.UI.SkillBar.RestoredAbilitiesNotifyReadyWithSlots` 与 `ReplicationWaitsForAbilityReferencesAndRefreshesLaterUpdates`：`Saved/TravelValidation/SkillBar/Regression-Final/index.json`。
- 双客户端回归脚本：先在 LoadMenu 开启两个 Standalone PIE 窗口，运行 `Scripts/Rooms/verify_pie_travel.py` 创建独立 QA 存档并加入同一房间；进入 Dungeon 后运行 `Scripts/Travel/verify_skill_bar_travel.py`，通过真实传送点依次前往 Dungeon2、L_DungeonLabyrinth、Dungeon。比对服务端/客户端技能数量及实际技能栏 Image_SpellIcon 的资源引用，报告写入 `Saved/TravelValidation/SkillBar/`。结束时删除本次 `RoomPIE_*` 临时存档。
- 最终实际运行通过：`Saved/TravelValidation/SkillBar/f3441d77df454e11851f127115ccc7c3.json`，3 次传送的 15 项技能数量/图标检查全部通过。客户端最终仍显示 FireBolt 与 ArcaneNova 的原槽位图标。
