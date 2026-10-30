# Roguelike 地图生成第二增量实施计划

> **For agentic workers:** Use superpowers:executing-plans with independent asset/tooling subtasks. Track steps below.

**Goal:** 在独立地图中生成符合已批准配额的 14～18 房主支路，具有有限回溯、备用布局、可复现摘要、完整装配及双人验证。

**Architecture:** 保留三房间探针。Profile 显式启用 FullFloor，纯 C++ 先生成任务图，再按端口与占位装配。服务端复制最终图，各端沿用加载/物理碰撞/导航/就绪屏障。编辑器工具提供模板制作、离线预览和真实 PIE 验证。

**Tech Stack:** UE 5.8 C++、FRandomStream、DataAsset、动态子关卡、Recast、MCP/Python。

**Spec:** `docs/superpowers/specs/2026-10-28-roguelike-level-generation-design.md`。用户已批准全部推荐基线并要求继续下一阶段；本轮直接执行，无需再次审批。

## Global Constraints

- 主线 10～12，普通战斗 4～6，加入口/宝箱/精英/商人/休整/Boss 六个固定功能房。
- 前两个普通战斗；精英前至少三个普通战斗；宝箱在精英前，商人在精英后休整前，休整紧邻 Boss；连续战斗（含精英）不超过三个。
- 支路 2～3 条，总计 4～6 房，每条 1～3 房；各有宝箱或精英奖励终点。全层宝箱 2～3、主线精英 1、支路精英至多 1。无环路或绕过必经节点。
- 房间平面网格 2400 cm、门宽 800 cm，入口固定；不任意缩放模板以适配。
- 每次最多 2000 次候选尝试、最多 8 次装配尝试；确定性备用图仍需模板/碰撞/导航验证。无无限重试或按机器速度选择成功图。
- 保留上一增量和原项目行为，新增资产只在 `/Game/RoguelikeGeneration` 下；首版仍为单人和双人 Listen Server。
- 本阶段标记功能房用途，不接入战斗、交易、奖励、玩家探索 UI 或发布打包；开发调试图明确不属于玩家地图。

## Review Focus

- 狭窄端口池导致搜索穷尽：有界失败或合规备用，不能删房或伪成功。
- 多支路耗尽奖励配额：所有末端有收益、主线配额不受影响。
- 篡改主支路元数据或边：完整验证拒绝绕路、错序、分叉及孤立节点。
- 物理相邻但无图边的房间：门封闭；重复模板实例不相互混淆。
- 模板排序变化和强制备用：同输入稳定复现，日志字段不影响摘要。

## Task 1 纯生成核心

**Files:** `DungeonGenerationTypes.h`、`DungeonGenerationProfile.h`、`DungeonLayoutLibrary.h/.cpp`、新增 `DungeonFloorGenerator.cpp`、新增 `Private/Tests/DungeonFloorGenerationTests.cpp`。

**Interfaces:** `BuildFloor(Profile,Seed,OutLayout,OutError)` / `ValidateFloor(Profile,Layout,OutError)`；Layout Version=2，增加 MainPathLength，房间增加 MainPathIndex/BranchId（非所属=-1）；布局报告增加 UsedFallback/DiversityRelaxed/PlacementAttempts/SearchSteps。Profile 增加 GenerateFullFloor=false、FloorSettings（数量范围、GridRadius=12、8 次×2000 步预算、AllowFallback=true）。

- [x] 编写 1000 Seed 配额/顺序/树形/空间验证、重复与排序不变、有限失败与备用、篡改拒绝测试，观察 RED。
- [x] 使用独立任务图/空间/模板随机流，有限回溯选择合规布局；模板不足可放宽相邻战斗模板多样性并报告。
- [x] 实现备用直线主干加不重叠支路方案，仍执行全部约束；关闭备用时明确报告预算耗尽。
- [x] 验证 1000 Seed、100 Seed 完整布局唯一率≥90%、图与空间均有变化、正常库备用≤1%、重复 10 次；记录 P95 纯计算耗时。

## Task 2 运行时与内容

**Files:** `DungeonGenerationRuntime.cpp`、新增 `Scripts/RoguelikeGeneration/author_floor.py`；新 `Maps/L_RoguelikeFloor`、`DA_RoguelikeFloor`、`Rooms/L_Floor_*`。

**Interfaces:** Runtime 根据 Profile 模式调用生成与验证；JSON 增加完整 connections、role、main_index、branch_id、fallback、attempts、search_steps、generation_ms。模板库共 11 个用途/几何模板（含固定入口），战斗五种、其他五种动态用途。

- [x] 复用现有控制器/模式及固定入口；创建全部用途模板和足够导航边界。
- [x] 复制完整清单并按所有边检查物理通行与导航，未使用门封闭。
- [x] 单人 20 个固定 Seed、双人 10 个固定 Seed 检查实际世界加载数、逐边通行、Boss/支路可达、摘要一致和清理。

## Task 3 开发调试与交付

**Files:** 新 `verify_floor.py`、`preview_floor.py`、`run_floor_checks.py`，更新使用说明。

- [x] 预览图用稳定 RoomId/角色/主支路/坐标/边展示，导出 JSON 和可查看 HTML/SVG，不暴露为玩家地图。
- [x] 验证强制备用、缺用途/错误端口/预算耗尽、人数不足，保留上一探针回归。
- [x] 完整 Editor 构建和项目自动化，独立全增量审阅，修复重要发现并验证。
- [x] 恢复地图默认配置、核验保存资产，提交本地检查点及证据说明。
