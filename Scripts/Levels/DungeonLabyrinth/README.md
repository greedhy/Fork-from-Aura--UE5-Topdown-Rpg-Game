# 地牢迷宫：地形初版

关卡资产：`/Game/levels/L_DungeonLabyrinth`。

全部地形网格与材质复用 `/Game/Assets/Dungeon`。主要路线为入口大厅 → 十字厅 → 中央庭院 → 台阶 → 高台圣所。西侧墓室通往曲折回廊、回环与尽头壁龛；东侧展厅通过支路连接上层库室与中央庭院。

- 网格基准 400 cm，主通道宽 800 cm，墙高 280 cm。
- 高台高 200 cm，以 10 级、每级 20 cm 的台阶连接。
- 7 个房间，336 个可达地面网格单元，136 段墙体。
- 使用现有 `BP_MyGameMode`，入口放置 PlayerStart，添加覆盖关卡的 NavMeshBoundsVolume。
- 包含基础照明、地面、基础、墙体、独立墙体阻挡、柱子与台阶。本阶段为地形布局。

所有人工布置的 Actor 带 `DL_Terrain` 标签，并位于 `DungeonLabyrinth` 文件夹。可直接在编辑器中调整。

## 构建与检查

1. 用宿主 Python 执行 `layout.py`，生成 `Saved/LevelAuthoring/DungeonLabyrinth/layout.json`。
2. 通过项目 SOMOLMCP `level_create` 创建并加载新地图。该路径已存在时应直接打开，不能覆盖已有地形。
3. 通过 MCP `console_exec` 执行 `py "<绝对路径>/build_level.py"`。脚本检查目标地图与已有标签，避免重复布置。
4. 通过原生 MCP `navmesh_rebuild` 构建导航。写工具需携带 `world:current` 独占资源锁。
5. 通过 MCP 执行 `validate_level.py`，检查真实世界的地面、接缝、墙体阻挡、台阶和导航路径。报告写入 `Saved/LevelAuthoring/DungeonLabyrinth/latest-validation.json`。
6. 用 `level_save` 仅保存本关卡。切换到另一已保存关卡后再打开本关卡，执行验证脚本确认保存结果。

`refine_level.py` 是本次制作的朝向和照明校正脚本；最终参数已合并进 `build_level.py`，重新构建时不必额外执行。

实现注意：Unreal Python 的 Rotator 使用 `pitch/yaw/roll` 关键字参数。导航边界通过 EditorActorSubsystem 的体积工厂创建，以获得有效的盒形 Brush；单纯 World Spawn 的空 Volume 不足以生成导航。原生 MCP `navmesh_rebuild` 使用导航系统 Build，避免不受支持的 `REBUILDNAV` 控制台命令。
