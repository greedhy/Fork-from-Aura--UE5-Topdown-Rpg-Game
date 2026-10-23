# Mass 怪物管理第一阶段

用户目标：先验证功能，不设数量目标；为后续暗黑式房间精英怪、类型 GA 池和新 GameMode 建立基础。

设计：服务器拥有一只怪物一个 Mass Entity；自定义 fragment 保存 Actor 弱引用、位置、房间、活跃状态。PostPhysics Processor 在游戏线程批量读取 Actor，增量更新二维哈希网格，查询再做三维距离精筛。附近任意玩家都可唤醒怪物，进入/退出距离存在滞回。远处只暂停本系统接管的行为树，GAS、移动组件、复制仍按原逻辑工作；受伤立即唤醒，活动 GA 阻止休眠。无玩家时保持活跃以避免初始化/换图空窗冻结。

接入：独立 MassDungeonGameMode 在 InitGame 配置 WorldSubsystem；原 GameMode 不启用。配置数据资产控制网格、更新周期、距离与受伤保护。敌人 BeginPlay/Die/EndPlay 管理注册，SpawnPoint 传递 RoomId。房间和类型仅为后续精英系统预留，不在本阶段随机授予 GA。

实施顺序：
1. 编写空间索引和状态策略回归测试，并完成底层结构。
2. 实现 Mass subsystem/processor、GameMode 和生命周期接入。
3. 完整编译，运行原生测试；制作独立测试配置、GameMode 和地图。
4. PIE 验证自动 Processor、动态生成、移动、休眠/唤醒、死亡和清理；记录真实结果与限制。
5. 完成一次集中代码审查、修复必要问题、编写使用指南。

边界：这不是纯 Mass 移动/导航/表现系统；不移除 Character，不宣称支持某个怪物数量。地形效果、GAS 和多人复制沿用原有链路。空间索引位置最多滞后一个配置周期。活动 GA（包括持续被动）可使怪物持续活跃，这是保守战斗保护。

资料：Epic MassEntity Overview、Megafunk/MassSample；API 以本地 UE 5.8 MassEntity/MassSimulation 为准。

执行记录：已有设计与实施授权，直接执行；工作目录包含大量用户既有未提交资产与背包代码，原地进行最小修改，不清理/回滚/提交它们。

进度记录：
- 已完成原生 Mass 管理、GameMode、生命周期和房间字段接入。
- UE 5.8 要求显式依赖 MassCore；独立测试调用 Processor 需 Processor execution context。
- 第一轮完整回归 94 项通过（含原有资产警告）；双客户端 PIE 21 项功能检查通过。
- 资产生成改用 LevelEditorSubsystem.NewLevelFromTemplate，通用 DuplicateAsset(World) 会留下未保存世界对象。
- 集中审查发现世界子系统销毁顺序风险；新增未 BeginPlay 但已注册实体的销毁测试，已复现 EntityManager 已被销毁导致的断言。修复为只清本地记录，全部世界实体由 Mass 自身销毁，不在 Deinitialize 跨子系统访问或恢复 AI。
- 外部暂停所有权通过原生 BehaviorTreeComponent 状态验证；运行中的行为树暂停/恢复由真实双客户端 PIE 验证。
- 完成：销毁修复后的全套 94 项原生测试通过（0 failed/notRun/inProcess），最终构建成功；重启后双客户端 21 项再次通过，保存资产重载校验通过。测试结束恢复 LoadMenu。
