# StoneGolem 实现与 PIE 验收

更新：2026-10-30。遵循 [怪物开发规范](monster-development-standard.md) 和已确认的 [正式设计](stone-golem-elite-design.md)。当前为传统 GAS 首版，自动化通过，等待用户最终验收。

## 已实现

使用 `AEnemyCharacter` 的 ASC、属性、伤害、AI、死亡和对象池流程；专属 `AStoneGolemCharacter` 配置模型、锤盾和预警。三个 GA 共用原生执行流程，各自有独立配置和冷却。沿用 `BTT_Attack` 的 `Abilities.Attack` 标签，通过选择器按距离、冷却和权重选技能。

资产根目录：`/Game/BluePrints/Characters/StoneGolem/`。

| GA / 调参资产 | 预警与范围 | 时间（从激活起，秒） | 初始数值 |
|---|---|---|---|
| `GA_StoneGolem_HeavyHammer` / `DA_SG_HeavyHammer` | 感叹号 + 前方偏移圆，半径180 | 动画0.20开始，0.35锁定，约0.90命中，1.60结束 | 基础伤害×1.5，冷却4，权重3 |
| `GA_StoneGolem_Quake` / `DA_SG_Quake` | 感叹号 + 自身圆，半径450 | 立即锁定，动画0.70开始，约1.40命中，2.40结束 | 基础伤害×1，冷却9，权重1 |
| `GA_StoneGolem_ShieldBash` / `DA_SG_ShieldBash` | 前方80°扇形，半径220 | 动画立即开始，0.20锁定，约0.833命中，1.333结束 | 基础伤害×0.6，冷却5，推力350，权重2 |

单位为UE厘米。`DA_StoneGolemElite` 配置模型、专属AnimBP、锤盾、移动速度150、基础伤害40、伤害GE、行为树及三个GA。最终扣血仍经过现有物理伤害、护甲和抗性计算。

重锤、地震使用 `Animations/AM_SG_Slam_Contact`；盾击使用 `Animations/AM_SG_ShieldBash`。实际蒙太奇位置是唯一命中时钟，未播放、提前中断或跳过命中容差窗口会取消，不补发延迟伤害。命中容差目前0.034秒，低帧率场景需在PIE中特别观察。数据资产改值只影响下一次攻击，已开始攻击使用参数快照。

## 预警、特效及生命周期

红色网格和伤害共用投影后的三角形区域，锁定后固定。墙体遮挡、无地板和超高差区域被排除；被裁掉的红区不会仍然造成伤害。当前按目标脚底中心点判定，不按胶囊边缘；仅支持静态地面和静态遮挡，移动平台等动态场景未覆盖。

三个 `NS_SG_*` 从 Free_Spells Shockwave 派生，源资源未修改。实际活动发射器为CPU世界空间；禁用Spiral1，Scale_All分别为0.65、1.5、0.35，烟尘改为土色。冲击粒子是装饰，不代表半径450的扩散伤害；地震在命中时刻一次结算整个红区。重锤/地震取右手锤插槽投影点，盾击取左手盾插槽投影点。特效在命中时出现，正常攻击结束或取消时清理，另有最长2秒的到期清理；当前不会让粒子尾迹跨越攻击结束。

死亡、眩晕及回收立即撤销预警并作废攻击代次；计时回调再检查存活、代次和生命租约。旧生命不能结束或伤害新生命。唤醒恢复控制器转向，按配置重新授予且不重复授予技能。复制侧生命状态更新会重新协调预警，防止通知顺序导致新生命提示缺失；此项尚未进行多人实机测试。

首版没有普通受击中断动画；普通伤害不打断，眩晕、死亡和蒙太奇中断可取消。沿用可恢复布娃娃和附件保留流程，未复制资源包的销毁/溶解蓝图。当前精英不占普通怪对象池，复用兼容性通过隔离测试验证。

## 游戏接入

`/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay` 的 `EliteClass` 已设为 `BP_StoneGolemElite`。原精英血量450、普通怪名单、人数、血量、池容量12、尸体保留时间和Boss配置保持原值。原配置的二进制备份及字段对照见 `Saved/GAAuthoring/StoneGolemBuild/integration.json`。

专属AnimBP的ShouldMove按实际速度大于3判断，避免AI直接设置速度但没有输入加速度时滑行。原资源包AnimBP没有修改。

## 已执行验证与边界

- Editor目标完整编译、链接成功，新编辑器已加载反射类型。
- `ReviewRegression/index.json`：10/10通过。包含StoneGolem参数、圆/扇形边界、共享三角形裁剪、墙后/无地板/楼层、死亡/眩晕失效、两次生命及旧回调隔离，以及6项既有对象池回归。
- `IntegrationRegression/index.json`：接入精英配置后4/4通过，覆盖普通怪组成/配额和房间加载、活动房间战斗边界。
- `combat-probe.json`：三个真实GA各造成一次扣血，友军与范围外目标不受伤；重复激活被拒绝，提示结束后清理。
- `runtime-regression.json`：7/7通过。三个GA的实际Niagara生成/清理和结束后冷却拒绝，三个蒙太奇前摇中断不补伤害，以及真实致死GE后的取消。
- `ai-runtime.json`：实际速度150时走路状态为真；沿用现有BTT攻击标签触发选择器、红区及真实伤害。该测试调用任务使用的标签入口，未代替完整地牢导航追逐测试。
- `final-readback.json`、`fx-space-*.json`、`fx-configured.json`：独立配置/插槽/蒙太奇/特效引用、世界空间、用户参数及Niagara编译读回。
- 既有姿态验证：计划0.70秒锤面离地约1.50厘米，运行时附件姿态约1.4996厘米；无角色根位移。静态侧面证据为 `corrected-contact-side.png`，不是运行时游戏镜头。

上述报告均在 `Saved/GAAuthoring/StoneGolemBuild/`。隔离PIE使用专用测试GameMode，不走玩家存档路径。无模型测试靶的通用受击GA会产生缺少蒙太奇提示，未用于判断StoneGolem播放是否正常。早期致死夹具在PIE中使用EditorAssetLibrary加载GE失败，修正为直接加载类并断言致死后，完整7例已重跑通过。

尚未验证：多人客户端/延迟复制、完整地牢导航与门口拥堵、动态地形、低帧率观感、盾击对真实玩家的推开距离，以及游戏镜头下特效完整度、红区清晰度与混合手感。原生对象池回归不等于这只精英已经参加普通怪池生产调度。

## 用户 PIE 验收

1. 打开 `L_RoguelikeRun`，开始新的PIE局，进入精英房；应出现带锤盾的StoneGolem，血量沿用450。
2. 靠近并保持在身前，分别观察重锤、盾击；拉开到近战之外、地震距离以内观察地震。权重选择可能需要等待冷却和多次攻击。
3. 重锤/地震先显示感叹号与红区；盾击显示扇形红区。锁定后绕到侧后方，范围不能继续追踪。红区外和墙后不应被命中。
4. 观察下砸锤面与地面、命中冲击同步；盾击特效来自盾侧。特别检查粒子在后摇结束时清理是否显得突兀，红色地面是否在当前光照下足够清晰。
5. 在预警期间击杀/眩晕，应立即停止提示且不出现迟到伤害；盾击命中真实玩家应推开，普通受击不应随机中断精英。
6. 检查追逐走路、转向、攻击恢复移动，以及死亡后锤盾和布娃娃表现。若需要调数值，退出PIE修改三个攻击DataAsset后重新开始；全局精英血量在DA_DungeonGameplay中调整。

当前编辑器已恢复原地图与视角，停止本任务的模拟并恢复后台节流设置。最终视觉与玩法验收由用户完成；没有自动提交Git或标记用户已验收。


## 2026-10-30 PIE反馈修复：移动、地图方向与血条

- 移动根因：BlendSpace中虽有Idle/Walk/Jog样本，但原样本创建工具未执行ResampleData，运行时没有有效插值数据。速度150和ShouldMove=true不足以证明动画在播放。修复使用引擎BlendSpace编辑器重采样并保存，新增finalize_locomotion.py；后续通过工具写完样本必须执行此步骤。
- 实际姿态验证：修复前移动期间左脚XYZ位移范围均为0；修复后以及重新启动编辑器后，前后约73厘米、上下约16厘米。verify_locomotion_pose.py同时检查状态和组件空间骨骼变化。原生RuntimeLocomotionSamples从磁盘加载资产，验证0/150/300速度能取得归一化的对应动画权重。
- 小地图根因：原HUD把世界+X映射到右方、+Y映射到上方，与实际摄像机yaw=0时的屏幕轴不一致。现在房间和连接线使用实际摄像机朝向投影；旋转后的边界用于缩放布局，标签保持正立。没有修改WASD、玩家出生或镜头朝向。MapCameraOrientation覆盖默认方向、四个正交方向及37度方向。
- 血条根因：WBP_EnemyHealthBar使用BP_EnemyBase强制转换且失败后Sequence仍继续绑定；StoneGolem原生子类不属于该蓝图。共享血条现使用EnemyCharacter类型的BoundEnemy，仅成功转换后赋值和绑定。原BP_EnemyBase派生怪物继续兼容。
- StoneGolem组件配置补齐：Screen空间、DrawAtDesiredSize、相对高度130。原来World空间和角色中心位置的默认值不适合头顶血条。author_gameplay_assets.py同步保存这些配置，避免重跑丢失。
- 验证：本轮Editor编译/链接通过；NativeTests中6/6通过；StoneGolem和GoblinSpear真实GE扣血后，血条绑定、当前/最大生命、前景进度、受伤后显示均通过。满血仍按原有规则隐藏。未将Ghost拖尾、完整地牢视觉验收或多人验证算作本轮通过项。
- 证据：Saved/GAAuthoring/StoneGolemMovementFix/ 下的pose-before.json、pose-probe.json、map-before.json、NativeTests/index.json、healthbar-runtime.json及healthbar-fixed-graph.json。旧共享血条和StoneGolem配置均已备份。

复测请新开PIE：观察StoneGolem追逐时腿部走动；按W/D时确认小地图的上/右与主视角一致；攻击StoneGolem后确认头顶出现并更新血条，且不再出现BP Enemy Base为空的绑定错误。
