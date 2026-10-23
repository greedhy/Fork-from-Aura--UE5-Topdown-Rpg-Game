# 地形效果与特效

把 `/Game/BluePrints/Actor/Terrain` 中的 `BP_Terrain_Lava`、`BP_Terrain_Frost`、`BP_Terrain_Toxic` 或 `BP_Terrain_Vines` 拖入关卡，即可同时获得地板外观、作用区域和特效。上一批 `SM_Ground_*` 仍是纯外观网格，单独放置它们不会施加状态。

## 默认行为

| 地表 | 效果 | 离开地表后 | 表现 |
|---|---|---|---|
| 岩浆 Lava | 每秒 8 点灼烧伤害 | 再持续 2 秒 | 火焰、橙色火星 |
| 冰霜 Frost | 移速降至原来的 60% | 约 0.3 秒内解除 | 蓝白冰晶与霜粒 |
| 毒性 Toxic | 每秒 4 点中毒伤害 | 再持续 3 秒 | 绿色毒气、毒液粒子 |
| 藤蔓 Vines | 缠绕 2 秒，禁止移动但仍可攻击/施法 | 本次缠绕自然结束 | 绿色叶片环绕 |

藤蔓每次解除后有 3 秒恢复窗口，仍站在上面时可再次缠绕，避免永久困住角色。相邻地块采用约 0.3 秒接触宽限，灼烧/中毒实际消退时间可能比配置多出这段宽限。

同类地表只保留一个状态：伤害取最高值，冰霜取最强减速；不同类型可以共存。伤害沿用项目异常状态的 `IncomingDamage` 通路，为固定周期伤害，不计算暴击、格挡或护甲，也不会每秒打断角色动作。环境击杀没有玩家归属，不发放自杀经验。

默认同时影响项目玩家和怪物（继承 `BaseCharacter` 且具有 ASC）。按脚底位置和地表高度判断接触，要求角色着地；空中经过不会新增状态，已经获得的状态按剩余时间消退。泥潭维持原有外观，本次没有额外赋予效果。

## 调整参数与摆放

每类配置位于 `/Game/BluePrints/Actor/Terrain/Data/DA_Terrain_*`，可调整 `DamagePerSecond`、`ExitDuration`、`MovementMultiplier`、`EntangleDuration`、`EntangleRecovery`，以及地板网格、地表粒子和角色粒子。想制作不同强度的同类区域时，先复制配置资产，再赋给对应地形 Actor。

Actor 的 `SurfaceSize` 控制覆盖尺寸（厘米），`ContactHeight` 控制脚底高度容差；`bAffectPlayers`、`bAffectEnemies` 控制对象，`bRequireGrounded` 控制是否要求着地。Actor 原点就是地板顶面的中心，默认尺寸为 400×400 cm。通常用 `SurfaceSize` 修改面积，保持 Actor 缩放为 1。这些是关卡编辑配置；未实现运行时向客户端同步配置资产替换或启用开关。

地形 Actor 自带可站立地板。替换已有装饰地板时，应避免让两个地板在完全相同高度重叠。原 Dungeon、Dungeon2、迷宫的地板没有自动替换。

## 试玩与特效

打开 `/Game/levels/L_TerrainEffectsTest` 并运行 PIE，可以走入四块区域体验。地图有两个明确的玩家出生点，可使用两玩家 Listen Server 验证。该测试图独立于原来的地表材质预览图。

`/Game/Art/TerrainSurfaces/Effects` 包含 8 个 Niagara System（每类各有 `Surface` 地表表现和 `Status` 角色表现）、8 个材质实例，以及 `M_TerrainParticle` 主材质。粒子复用项目 Fire、Embers、Stars 的运动结构，使用独立的程序化火焰、冰晶、毒液和叶片材质；源资产保持原样。冰霜和缠绕使用短时状态粒子，配合预热尽快显示冰晶和环绕叶片；地表粒子也设置了预热。

## 网络与生命周期

`TerrainSurface` 由服务器每 0.2 秒查询一次脚底接触。每个角色的 `TerrainStatusComponent` 汇总接触来源，维护原生 GameplayEffect 的句柄、持续时间和缠绕恢复窗口。重复扫描不会重置伤害计时器，也不会为相邻地块多算伤害。

角色状态、减速倍率及特效资产引用复制到客户端，各客户端本地播放 Niagara；专用服务器不创建表现组件。视觉组件不参与伤害结算。角色死亡、销毁或退出世界会移除本组件创建的 GE；已销毁或禁用的地表来源会在后续扫描中清理。受击、眩晕和缠绕限制优先于冰霜减速，限制结束后恢复当前正确移速。

主要源码在 `Source/test_25d/Public/Terrain` 与 `Private/Terrain`。资产重建脚本为 `Scripts/TerrainSurfaces/build_effect_assets.py`，随后运行宿主脚本 `compile_effects_mcp.py` 完成 Niagara 本地空间、预热和编译设置。重建只针对本批指定路径，手动变体请另存名称。

## 验证记录

- `Saved/TerrainSurfaces/Regression-20261022/index.json`：56 项项目自动化测试通过，0 失败；其中 19 项伴随测试角色缺少骨骼网格/插槽等警告。4 项地形测试组覆盖脚底/着地筛选、周期伤害与去重、减速/眩晕/缠绕组合，以及销毁/死亡清理。
- `Saved/TerrainSurfaces/effect_pie_validation.json`：双玩家 Listen Server，34 项检查通过；真实玩家、怪物和地形扫描，验证服务端伤害、拥有者与观察者的状态/特效、血量复制和离开清理。测试用位置传送准备接触，未模拟人工 WASD 操作。
- `Saved/TerrainSurfaces/effect_compiles.json`：8 个 Niagara System 编译检查。
- `Saved/TerrainSurfaces/effect_validation.json`：资产配置、材质引用、角色组件及源特效文件哈希检查。
- `SourceArt/TerrainSurfaces/EffectsPreview.png` 与四张 `*Close.png`：PIE 实际场景捕获，未更改粒子组件的位置或模拟时间。

本次没有验证独立专用服务器、丢包或高延迟网络。
