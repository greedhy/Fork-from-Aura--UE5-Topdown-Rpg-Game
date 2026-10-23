# 纯 Mass 怪物：独立、增量接入

本实现只增加文件和 `/Game/PureMass/` 资产。没有修改原有源码、Build.cs、uproject、Config、关卡、技能目录或角色资产。原有混合 Mass 模式和 Actor/GAS 怪物玩法继续独立存在。迁移前 2440 个文件的 SHA-256 基线保存在 `Saved/PureMass/original-files.json`，核验脚本是 `Scripts/PureMass/verify_preservation.py`。

## 试玩

打开 `/Game/PureMass/Maps/L_PureMassDungeon`，运行 PIE。多人验证选择两个玩家、Listen Server。地图来自 Dungeon 的新副本，内有两个 `PureMassSpawnRegion`，各生成 4 个实体。旧怪物、旧生成点和地图入口仅在副本中移除。

默认测试装备：

| 输入 | 新技能 |
|---|---|
| 左键点怪物 / Shift+左键 | Projectile |
| 右键按住 / 松开 | Beam / 停止 |
| 1 | Burst |
| 2 | Homing |
| 3 | Chain |
| 4 | Orbit 开关 |

左键点地面仍可寻路移动；WASD 仍使用原输入映射。测试玩家使用新的初始装备，不导入或写入原有角色技能存档。死亡后在此地图重生，不按旧存档切回 Actor 地图；HUD 和 PlayerState ASC 保持单份初始化。

`/Game/PureMass/Abilities/` 包含 18 个原型 GA 和 8 个组合 GA 的副本。新 GA 父类是 `UPureMassAbility`。26 个副本使用独立技能目录 `DA_MassAbilityInfo`；HUD 使用原有 WidgetController 蓝图的**新子类**，保留旧控件中的类型转换并读取新目录。技能身份标签和数值配置沿用原定义；没有向原目录登记这些替代类。

## 怪物配置与架构

`DA_MassGoblin` 配置血量、移速、数据胶囊半径/半高、攻击伤害/距离/间隔、护甲、抗性、经验和渲染资源。调整关卡中的 `PureMassSpawnRegion.Count / Spacing / RoomId / MonsterType` 可修改实体生成组。`DA_MassQAGoblin` 是联机测试使用的静止高血量类型，不用于地图的正常生成组。

| 职责 | 新实现 |
|---|---|
| 数据 | `FPureMassFragment` 保存位置、速度、路径、血量、攻击与状态计时；每只怪物是实际 Mass Entity |
| 调度 | `UPureMassProcessor` 在服务器/单机游戏线程处理已启用世界；旧地图不会自动启用 |
| 空间查询 | 复用只读的空间索引实现；查询结果使用稳定 ID，ID 不复用，不向客户端暴露 Mass handle |
| 导航 | Mass 处理器调用 Recast 导航查询、缓存路径，每帧最多 8 次寻路；没有 AIController/行为树/CharacterMovement |
| 碰撞 | 实体数据胶囊、空间邻居分离、世界胶囊 sweep/滑动/贴地；投射物按实体命中时间和世界遮挡时间排序 |
| 渲染 | 一个 `APureMassCrowd`，每种类型一个 `UInstancedSkinnedMeshComponent`；每个实体独立动画轨道；组件关闭碰撞 |
| 网络 | 共享 Actor 的 FastArray 差量快照，约 10 Hz；客户端插值、拾取查询；客户端不能生成权威实体或改血 |
| 玩家战斗 | 玩家保留 GAS 消耗、冷却和输入；新 TargetData 将稳定实体 ID 和命中点送给服务器，再验证范围、目标和遮挡 |
| 敌人战斗 | 实体直接维护血量和状态；攻击玩家使用稳定原生瞬时 GE，不为怪物创建 Actor、ASC 或代理组件 |
| 效果 | 技能效果可以有运行时 Actor/Niagara 组件；这些属于施法节点，不是逐怪物 Actor |

原型运行时覆盖 Projectile、Multishot、Burst、Beam、Surface、Orbit、Field、Trap、Homing、Piercing、Chain、Cone、Wave、Returning、Emitter、Delay、Ring、Line；子节点沿用深度不超过 3、共享施法最多 64 次生成的预算。Orbit 的火球是效果运行时内的数据记录，通过实体 sweep 命中；生成、目标切换和耗蓝均在服务器进行。

地表读取现有 `ATerrainSurface` 配置，对实体应用岩浆/毒性伤害、冰霜减速和藤蔓缠绕。新原型创建的地表仍使用原有表面特效。敌人身上的旧 Character 附着 Debuff Niagara、受击蒙太奇、血条和伤害数字 UI **没有自动迁移**；当前共享骨骼渲染播放 idle/run/attack，死亡直接移除实例。

伤害顺序为抗性→格挡→暴击→护甲，读取既有平衡曲线。新路径对概率和最终减伤做边界限制；Pure 标签正确跳过抗性。保留旧 EffectiveArmor 曲线参与暴击抵抗的数值约定。这不是逐位复刻旧 ExecCalc 的随机分布或历史拼写问题。敌人的类型级 XPReward 可配置，实体死亡仅派发一次玩家经验事件。

## 新渲染资产

`Rendering/SKM_MassGoblin` 和 `M_MassGoblin` 是原网格/材质副本，开启 OptimizeForInstancing 与 InstancedSkinnedMesh 材质用途；原网格、材质没有改动。新 AnimBank/ASTP 引用既有 Idle_Spear2、Run_Spear_fix、Attack_Spear 动画。网格偏移为 Z=-60、Yaw=-90。

渲染器只接受 `/Game/PureMass/` 下的网格、材质、动画 Provider，避免引擎自动材质用途更新误改原资产。增加其他怪物时，先复制资源并建立匹配 Provider，再创建新的类型数据资产。

## 验证与复现

- `Saved/PureMass/build-9.log`：Editor target 编译日志。
- `Saved/PureMass/Tests-Final3/index.json`：全项目原生回归结果，包含 PureMass 新测试。
- `Saved/PureMass/asset-validation.json`：新目录、26 个 GA、渲染资源、模式/输入/HUD 和地图引用读回。
- `Saved/PureMass/pie.json`：双客户端实体/渲染/移动、真实远端输入、扣蓝、伤害同步、死亡回收和玩家重生验证。
- `Saved/PureMass/channels.json`：远端 Beam 松键和 Orbit 开启、生成、攻击触发、关闭、停止耗蓝。
- `Saved/PureMass/standalone.json`：单人启动、8 个实体、共享渲染和处理器运行检查。
- `Saved/PureMass/preservation.json`：对迁移前文件的内容哈希核验。

最终结果：107 项原生测试通过（60 项无警告、47 项带既有测试警告，0 失败）；43 项资产检查、23 项双客户端基础检查、14 项持续技能检查和 8 项单人检查全部通过。2440 个已有文件内容哈希保持一致。编辑器已退出 PIE，停留在新测试地图。当前没有做截图级外观验收，渲染验证依据运行时实例/轨道数、动画状态、资源配置和双端同步。

编辑器资产脚本为 `Scripts/PureMass/author_assets.py`，只保存新目录包；Native 类型有变化时需要完整编译和重启。运行资产脚本之前须退出 PIE。脚本通过项目已有 MCP bridge 调用；console 接收回执不代替上述 JSON 结果。

这一版是独立的功能验证路径，不会把原地图或存档中的所有 Actor GA 自动替换为 Mass GA。尚未做数量压测、打包构建、长时间网络丢包验证，也未接入精英词缀/怪物技能池。后续应继续只新增类型、处理器和资产，在新 GameMode 下扩展。

参考：Epic [MassEntity 概览](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-mass-entity-in-unreal-engine)、[MassGameplay 概览](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-mass-gameplay-in-unreal-engine)，以及本机 UE 5.8 的 MassEntity、InstancedSkinnedMeshComponent、AnimSequenceTransformProviderData 源码。导航使用 Mass 调度的 Recast 查询，不要求修改现有模块依赖来接入 MassNavMeshNavigation。
