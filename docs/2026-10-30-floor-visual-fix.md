# 生成房间地板与 Dungeon 照明对齐

用户授权：先消除地板重面，再对齐原 `/Game/levels/Dungeon` 的地板风格和照明。

## 修复

- 原 `SM_Tile_4x4` 是近乎零厚度平面，位于 Z=0，与可见地基顶面重合。入口和所有模板的可见地板改为 Z=1，保留地基和隐藏连续碰撞底板。
- 每房间使用 2×2 块 `SM_Tile_6x6`，每块1200×1200厘米、比例1，覆盖原2400×2400厘米范围。使用与原 Dungeon 主地板相同的 `M_Tileset1`，不更改共享网格、材质、纹理。
- 删除生成房间和入口的彩色 PointLight、原宿主18/6强度的双色方向光。三个宿主从 Dungeon 读取主光、天空光、天空大气、雾、云和后处理参数；主光方向及强度1、白色、6500K等与源一致。
- 环境仅存在于持久宿主，流送房间不重复生成全局灯光。组件采用 Movable 以适应运行时拼接；后处理设为 Unbound 覆盖整层，避免只覆盖原地图的小范围。
- 共15张生成地图：3个宿主、2个早期探针模板、10个整层模板。原 Dungeon 地图哈希未变。
- `author_probe.py` 与 `author_floor.py` 同步更新，后续生成不再恢复重面或彩色房间灯。
- `floor_visual_style.py` 共享配置/校验；`repair_floor_visuals.py` 支持只读检查、限定地图迁移、备份、保存和重开核验。输入位于 Saved/RoguelikeGeneration/floor-style-request.json；apply=false 为只读。

## 证据

Saved/RoguelikeGeneration/ 下：

- `floor-style-red.json`：修复前15张地图被检测出重面、旧地板与灯光差异。
- `floor-style-green.json`：15张地图修复后与保存重开均通过；记录原地图未变和环境基准值。
- `VisualBackups/20261030-125644/`：修改前15张地图备份。
- `floor-visual-geometry-02.json`：在正确的 `L_RoguelikeFloor` 宿主运行，220项检查通过，包括整层生成、地板碰撞、门洞与导航连通。
- `floor-game-after.png`：通过运行中的玩家控制器 HighResShot 获取的实际 PIE 画面，已查看。编辑器视口辅助线截图不作为游戏照明验收。
- `floor-fix-finish.json`：停止PIE，无未保存内容，返回 L_RoguelikeRun，保留原编辑器实例。

## 验证限制与异常

- 首轮 `floor-visual-generation` 把纯几何门洞检查用于含战斗门的 L_RoguelikeRun，断言失败；改用几何宿主后通过。
- `floor-visual-solo-01` 错用双人集结条件，已保留失败记录；修正条件后的 `floor-visual-solo-02` 成功移动进入第一战斗房、生成混合怪物，但在 GE_Damage 杀怪检查处出现 ActorGroupNotKilled。本轮未定位该伤害问题，不声称清房或整局战斗回归通过，未修改战斗实现来绕过失败。
- 静态截图只能核对外观；移动镜头长时间观感仍需用户试玩。几何间隔已用资产数值和重开验证确认。
- 本轮没有 C++ 改动，没有重新编译用户当前其他开发工作。
