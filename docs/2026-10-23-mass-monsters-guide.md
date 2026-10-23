# Mass 怪物管理：第一阶段

## 设计与范围

本阶段按“先验证功能，不设数量目标”实现。现有怪物继续使用 Character、行为树、GAS、CharacterMovement 和 Actor 网络复制。服务器为每只怪物建立一个 Mass Entity；游戏线程上的 PostPhysics Processor 批量采样位置、更新空间索引和决定活跃状态。客户端不创建这套管理实体。

这层已使用真实 Mass fragment、archetype、entity query 和 processor，但尚未把移动、导航、碰撞或渲染迁移为纯 Mass。每次管理更新仍需遍历已注册怪物，不能据此宣称支持某个怪物数量。后续性能工作应以实际分析结果为依据。

## 资产入口

- 测试地图：`/Game/levels/L_MassDungeonTest`，使用现有 Dungeon 资产制作独立副本。
- GameMode：`/Game/BluePrints/Mass/BP_MassDungeonGameMode`，复制现有 BP_MyGameMode 的默认配置后继承新的原生 MassDungeonGameMode，保留角色、HUD、GAS 数据、存档和传送配置。
- 数据资产：`/Game/BluePrints/Mass/DA_MonsterManagement`。

直接打开测试地图并 Play；联机验证可设 2 个玩家、Play As Listen Server。正式地图要使用本功能，在 World Settings 中将 GameMode Override 指向 BP_MassDungeonGameMode。原有地图的 GameMode 保持原配置。

## 可调配置

| 字段 | 默认值 | 作用 |
|---|---:|---|
| CellSize | 1000 cm | 二维哈希网格单元尺寸 |
| UpdateInterval | 0.2 s | 位置与活跃状态采样周期 |
| WakeRadius | 2500 cm | 任意存活玩家进入该范围即可唤醒 |
| SleepRadius | 3500 cm | 所有存活玩家都离开该范围后允许休眠 |
| DamageWakeSeconds | 5 s | 受伤后保持活跃的时长 |
| PauseDistantAI | true | 为远处空闲怪物暂停行为树并停止当前寻路 |
| DrawDebug | false | 怪物上方绿球代表活跃，蓝球代表休眠 |

Wake/Sleep 使用三维距离，并通过不同阈值避免边界反复切换。无有效玩家时保持活跃，避免登录、换图期间的短暂空窗冻结 AI。正在执行的任意 GA 和受击反应阻止休眠；持续被动 GA 也会触发此保守保护。

配置在 GameMode 初始化时复制为世界内快照，修改数据资产后需重新启动该关卡才能生效。SleepRadius 小于 WakeRadius 时自动提升至 WakeRadius；无效浮点值与范围会被限制。

休眠只管理行为树，不停 GAS/角色组件 Tick、不改变角色复制、不卸载 Actor。状态持续时间、地形伤害等继续运行。只有本系统暂停的行为树才会被本系统恢复；外部已暂停的树不会被接管。

## 查询与扩展

从当前 World 获取 `MonsterManagementSubsystem`：

- `FindMonstersInRadius(Center, Radius, RoomId)`：返回存活怪物。RoomId 为 None 表示不筛选房间；Radius 为 0 表示精确采样位置；无效或负半径返回空。先查 XY 网格，再做三维球形距离判断。特别大的查询退化为扫描已有记录，避免遍历大量空单元。
- `GetStats()`：注册数、活跃数、休眠数、本系统暂停的行为树数、占用网格数、更新次数、是否启用。
- `IsMonsterActive(Enemy)`：管理层的活跃判断。未注册返回 false；PauseDistantAI 关闭时仍计算该状态，但不暂停行为树。

怪物 Actor 和 MyEnemySpawnPoint 新增 `MonsterRoomId`。生成点在 FinishSpawning 前传递房间，动态生成与场景预放置怪物都在 BeginPlay 自动注册，死亡和 EndPlay 注销。房间标识由关卡配置，不会依据墙体自动识别。空间查询使用最近一次采样位置，误差时间上限约为一个 UpdateInterval。

fragment 同时记录具体怪物类名，作为后续类型配置的识别信息。下一阶段可在该基础上增加房间生成规则、精英概率、怪物类型数据资产、额外 GA 池、属性增强及显眼的 GameplayCue/Niagara。第一阶段尚未加入这些精英规则。

## 参考资料

- [Epic MassEntity Overview](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-mass-entity-in-unreal-engine)：fragment/entity/archetype/query/processor 与延迟结构修改。
- [Epic MassGameplay Overview](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-mass-gameplay-in-unreal-engine)：后续表现与 LOD 迁移方向。
- [Megafunk/MassSample](https://github.com/Megafunk/MassSample)：原作者的示例及解释；README 明确提醒部分示例可能落后于引擎版本。

API 以本机 UE 5.8 的 MassCore、MassEntity 与 MassSimulation 源码为准：使用 `ConfigureQueries(const TSharedRef<FMassEntityManager>&)`，实体句柄从 `Mass/EntityHandle.h` 引入。读取 Actor 的处理器限定游戏线程与服务器/单人执行。处理期间产生的实体注册排队至安全 Tick，销毁使用 Mass 命令缓冲。

## 验证记录（2026-10-23）

- Development Editor 完整构建成功。
- 全项目原生自动化：94 项通过、0 失败，其中 47 项带有现有资产/测试角色警告。Mass 的 3 个测试覆盖网格负坐标、迁移、房间、三维筛选、超大查询、状态滞回、真实实体与 Processor、多玩家、外部暂停所有权及世界销毁。
- 双客户端 Listen Server PIE：21 项检查通过。包括自动注册和 Processor 调度、客户端不创建实体、真正暂停/恢复行为树、远端玩家唤醒、网格迁移、角色复制、真实 GAS 伤害唤醒、保护期结束再次休眠、死亡注销。
- 编辑器重启后资产重载校验通过，GameMode 的角色、HUD、GAS、存档与地图默认值和原配置一致。
- 已复现并修复子系统销毁顺序导致 EntityManager 失效的问题。残留实体由 Mass 的世界级生命周期清理，本系统 Deinitialize 只释放自身索引与记录。

结果：`Saved/MassMonsters/Tests-Final/index.json`、`pie.json`、`asset-validation.json`、`build.log`。脚本入口为 `Scripts/Mass/author_assets.py`、`verify_pie.py`、`validate_assets.py`。PIE 脚本只应在测试地图运行，会移动测试玩家并替换 PIE 中的怪物；不会保存这些运行时修改。

未进行数量压测、打包性能测试或纯 Mass 表现验证。精英怪生成、GA 池、强化属性和特效仍属于下一阶段。
