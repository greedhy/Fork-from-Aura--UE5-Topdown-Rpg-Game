# L_DungeonLabyrinth：200 只纯 Mass Goblin

按本次明确指定的关卡修改 `/Game/levels/L_DungeonLabyrinth`：仅切换 World Settings 的 GameMode 为 `/Game/PureMass/BP_PureMassGameMode`，并增加六个 PureMassSpawnRegion。原地形、传送点和出生点保留；没有修改任何 C++、已有怪物类型、GA、玩家蓝图或全局配置。

| 房间 | Goblin 数量 |
|---|---:|
| Crossroads | 40 |
| WestCrypt | 30 |
| EastGallery | 40 |
| CentralCourt | 40 |
| UpperVault | 25 |
| RaisedSanctum | 25 |
| 合计 | 200 |

在 World Outliner 的 `Mass200/Goblin` 文件夹调整各组 Count。间距为 160 cm；圣殿组已避开返回传送点的实体模型及角柱。编辑状态仅有六个生成区域，点击 Play 后才创建 200 个 Mass Entity，没有 200 个 EnemyCharacter。入口房间不布置怪物。怪物使用既有 DA_MassGoblin 配置：150 生命、200 移速、5 基础攻击伤害。

测试角色和技能来自独立 PureMass 模式，不读取/写入原有角色技能存档。左键 Projectile，右键 Beam，1 Burst，2 Homing，3 Chain，4 Orbit。保留的返回传送点仍指向原 Dungeon；离开本关卡后即不属于这次纯 Mass 测试范围。

## 本次验证

- 200 个出生位置的地面检查及入口到六个房间的完整导航路线通过。
- 单人、Listen Server 双客户端各通过 11 项运行时检查。
- 每个世界均有 200 个实体、200 条动画轨道、一个共享 Crowd Actor、一个实例骨骼渲染组件，EnemyCharacter 数量为零。
- 12 秒采样期间保持 200 个实体；198 个实体位置变化超过 30 cm；未发现跌落到地板以下。
- 通过实体伤害接口击杀一只后，所有世界均同步变为 199 个实体/实例/动画轨道。退出 PIE 后重新启动仍生成 200 只。
- 实际游戏视口截图已检查，Goblin 外观正常；聚集围攻时有明显拥挤，尚未在本任务中改进群体避让。

| PIE 采样 | 平均帧间隔 | 平均 FPS | P95 帧间隔 |
|---|---:|---:|---:|
| 单人 | 15.50 ms | 64.5 | 16 ms |
| 双客户端，同进程 | 20.00 ms | 50.0 | 31 ms |

这些是编辑器 Slate 回调的实际墙钟帧间隔，采样前预热 3 秒、采样 12 秒；不是单独的 Mass CPU 耗时、GPU 时间或打包版性能结论。没有空场景/Actor 方案对照，不能据此推断 Mass 的加速倍数。测试期间临时关闭编辑器后台节流、临时提高运行中玩家生命以避免重生干扰，结束后恢复节流并退出 PIE，没有保存运行时生命修改。双客户端日志出现了 `CreateSavedMove` 队列上限警告；本轮数量和死亡复制通过，但未以此认定玩家移动网络质量已通过专项压测。

## 复现与证据

- `Scripts/PureMass/author_labyrinth_200.py`：幂等布置，预先验证地面和导航，保存指定关卡。
- `Scripts/PureMass/verify_labyrinth_200.py`：在单人或双客户端 PIE 启动后运行，自动记录数量、运动、渲染、死亡及帧间隔。
- `Scripts/PureMass/capture_labyrinth_pie.py`：抓取实际玩家视口。
- `Saved/PureMass/Labyrinth200/authoring.json`、`pie-1.json`、`pie-2.json`：本次通过的报告。
- `Saved/PureMass/Labyrinth200/gameplay.png`：双客户端测试后的游戏视口截图（已执行一次击杀，场上 199 只；截图只显示相机范围内怪物）。
- `Saved/PureMass/Labyrinth200/L_DungeonLabyrinth-before-200.umap`：修改前的本地备份，不纳入 Git。

完成时编辑器已退出 PIE，停留在 L_DungeonLabyrinth；本轮没有提交或推送 Git。
