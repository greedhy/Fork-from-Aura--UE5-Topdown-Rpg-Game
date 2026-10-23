# 多人传送点与出生位置配置

传送点使用项目原有的 `BP_MapEntrance` 楼梯资产。服务器检查当前所有非旁观玩家：全部存活并进入 Sphere 区域，连续停留 3 秒才一起换图。有人离开、死亡或人数变化会重新计时。客户端重叠事件不会自行切换地图。

## 当前关卡

| 来源 | 传送点 | 目标地图 | 目标出生组 |
|---|---|---|---|
| Dungeon | 原有 BP_MapEntrance | Dungeon2 | Dungeon2PlayerStart1 |
| Dungeon2 | Portal_To_Labyrinth | L_DungeonLabyrinth | LabyrinthEntry |
| L_DungeonLabyrinth | Portal_Return_Dungeon | Dungeon | Dungeon1PlayerStart1 |

每张地图配置了 4 个玩家位置，编号 0–3。Dungeon 和新迷宫采用相邻位置，Dungeon2 采用分开的位置。迷宫传送点在北部高台房间，入口出生点在南部。

## 调整出生位置

1. 打开目标地图，在 World Outliner 的 `Travel/Arrival` 文件夹寻找 `TravelStart_..._P1/P2/P3`。它们的类型是 `TravelPlayerStart`。
2. `Player Start Tag` 是出生组名称，同一入口的所有点使用相同名称。
3. `Player Slot` 是玩家编号，从 0 开始。同一组的编号必须唯一，每名玩家需要一个点。编号在这次联机会话中保持不变，并非永久账号编号。
4. 拖动、旋转出生点即可修改位置和朝向。希望出生在一起就将点放在同一区域；希望分开就移到不同房间。各点留出角色胶囊空间，避免完全重叠。
5. 示例保留了地图原来的普通 `PlayerStart` 作为编号 0。普通 `PlayerStart` 在匹配组内视为 0；也可以换成 `TravelPlayerStart` 并显式设置 0。不要在同一组保留两个编号 0。
6. 超过 4 名玩家时，继续添加对应编号的点。找不到某名玩家的点或有重复编号，传送会拒绝执行并记录错误，不会随机选择位置。

`Default Entry Group` 标记该地图直接启动时使用的组。同一地图可以在同一组的多个点上勾选，但不能勾选多个不同的组。通过传送点进入时，以传送点指定的组为准。

## 配置传送点

选择 `BP_MapEntrance`，在 Details 中设置：

- `Destination Map`：目标地图资产。
- `Destination Player Start Tag`：与目标地图的 `Player Start Tag` 完全一致。
- `Required Stay Seconds`：连续集合时间，当前为 3 秒。
- `Sphere`：集合范围；当前示例半径为 260。原资产的 Sphere 位于楼梯上端，移动传送区域请调整 Sphere/MoveToComponent，移动整座楼梯请调整 Actor。

同一目标地图可布置多个出生组，供不同入口使用。设置完成后保存目标地图和来源地图。

## 联机行为与排查

统一通过服务器 `ServerTravel` 和无缝换图保留连接。各玩家的出生编号、等级、经验、技能和当前生命/魔力随各自 PlayerState 转移；输入在重新拥有角色时重新初始化。

传送点提供可供蓝图读取的 `Ready Players`、`Required Players`、`Countdown End Server Time`、`Get Countdown Remaining`、`Travel Error`。当前没有新增倒计时 UI。

若传送被配置校验拒绝，先让至少一名玩家离开区域，修正并保存地图后再重试。日志可搜索 `[PortalTravel]`。出生点必须放在可站立的地面上；不要把传送点本身当成出生点。

编辑器单进程多人 PIE 的无缝换图需要临时启用 `net.AllowPIESeamlessTravel 1`；测试后恢复为 `0`。正式运行不依赖这个 PIE 测试开关。

## 验证脚本

- `Scripts/Travel/test.ps1`：运行项目原生自动化测试，包含集合计时、离开/成员变化重置、出生组缺失/重复和玩家数据复制。
- `Scripts/Travel/validate_party_pie.py`：在 Dungeon 的双玩家 Listen Server PIE 中执行；只修改临时 PIE 对象，验证集合、取消、三次换图、出生位置、独立玩家数据和 Enhanced Input 移动同步。输出 `Saved/TravelValidation/party-pie.json`。
- `Saved/TravelValidation/baseline.json`：修复前的客户端独自开图复现记录。

自动化移动使用真实 Enhanced Input 注入；集合阶段直接设置测试角色位置。它不等同于人工点击菜单或完整走过楼梯的操作测试。

2026-10-22 验证结果：Editor Development 编译成功；52 项项目自动化测试通过（含 5 项传送回归测试）；双客户端完成三次换图，32 项运行时检查通过。三个地图均通过出生组/编号、楼梯站立面和从入口到传送区域的完整导航路径检查。临时 PIE 无缝换图开关已恢复为 0。
