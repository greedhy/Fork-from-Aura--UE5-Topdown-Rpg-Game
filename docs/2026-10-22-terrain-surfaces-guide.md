# 五种地表纹理与材质

资产目录：`/Game/Art/TerrainSurfaces`。

预览关卡：`/Game/levels/L_TerrainSurfacePreview`，包含原石板与五种新地表的并排展示。原来的 Dungeon、Dungeon2 和迷宫关卡没有替换地板。

| 类型 | 子目录 | 材质实例 | 视觉效果 |
|---|---|---|---|
| 岩浆 | Lava | MI_Ground_Lava | 暗色岩壳、橙红熔岩裂隙、轻微流动和发光脉动 |
| 泥潭 | Mud | MI_Ground_Mud | 湿泥、石粒与积水，不同区域有不同粗糙度 |
| 毒性 | Toxic | MI_Ground_Toxic | 腐蚀石块、黄绿色毒液和荧光斑块 |
| 冰霜 | Frost | MI_Ground_Frost | 蓝色冰面、裂纹和白色霜花，冰面与霜层反光不同 |
| 藤蔓 | Vines | MI_Ground_Vines | 石面上的根茎、常春藤叶片和苔藓 |

## 使用

最方便的方法是将各目录中的 `SM_Ground_类型_4x4` 拖入关卡。这些网格复制自项目的 `SM_Tile_4x4`，两个材质槽均已绑定对应新材质。

也可以把 `MI_Ground_类型` 赋给现有地板网格的材质槽。使用现有实例做变体时，先复制实例再调整参数。

默认采用世界 XY 坐标铺贴，每 400 cm 重复一次纹理；相邻水平地板能维持一致的图案尺寸。大面积地表保留项目原有的石板分块风格。坡面、墙壁或需要跟随网格旋转的表面，设置 `UseWorldUV=0` 使用模型 UV。

## 常用参数

| 参数 | 含义 |
|---|---|
| WorldTileSize | 世界空间单次铺贴尺寸，默认 400 cm；值越大，图案越大 |
| UseWorldUV | 1 使用世界 XY 坐标，0 使用模型 UV |
| UVTiling | 模型 UV 的重复次数，仅 UseWorldUV=0 时生效 |
| ColorTint / Brightness | 整体色调与亮度 |
| DryRoughness | 基底粗糙度 |
| DetailRoughness | 岩浆、积水、毒液、霜层或叶片区域的粗糙度 |
| EmissiveStrength | 发光强度，岩浆默认 3.5，毒性默认 1.8，其余为 0 |
| PulseAmount / PulseSpeed | 发光脉动幅度与速度 |
| FlowSpeed | 发光噪声缓慢平移的速度 |
| NormalStrength | 原石板法线的强度 |
| DetailNormalStrength | 根据新颜色纹理推算的浅表面凹凸强度 |
| MaskBias / MaskContrast | 调整特殊区域遮罩的覆盖量与边界 |

`SurfaceType` 是材质内部识别遮罩的方法：0 岩浆、1 泥潭、2 毒性、3 冰霜、4 藤蔓。单独修改这个值不会生成另一种地形，切换类型请使用对应实例。

## 资产来源与纹理设置

共 27 个新资产：15 张分组纹理、1 张共享噪声、1 个主材质、5 个材质实例和 5 个地板网格。

- `T_Ground_类型_BC`：复制项目原石板纹理后，导入基于它生成的地表覆盖版本。原始 PNG 保存在 `SourceArt/TerrainSurfaces/BaseColor`。
- `T_Ground_类型_N`、`T_Ground_类型_ORM`：复制原石板法线和 AO/粗糙度/金属度贴图，保留基础石板细节。新的裂隙、泥土、霜花和藤蔓浅层凹凸由材质从颜色纹理推算，不是额外雕刻烘焙的法线。
- `T_Ground_FlowNoise`：复制已有 FireBolt 的噪声纹理，用于发光区域变化。
- `M_TerrainSurface`：复制原石板材质并扩展为可调地表材质。

新颜色 PNG 为 1254×1254；Unreal 构建时缩放为 1024×1024。三种分组贴图运行时均为 1024×1024，共享噪声为 256×256。颜色使用 sRGB；法线和 ORM 使用线性数据及对应压缩设置，启用 Mip 与纹理流送。

原项目被引用的源纹理、材质和网格已用文件哈希确认没有被修改。检查记录在 `Saved/TerrainSurfaces/validation.json`，创建清单在 `Saved/TerrainSurfaces/assets.json`。

这批资产实现地表视觉表现；伤害、中毒、减速、滑行或藤蔓束缚等玩法可由后续地形 Actor/GA 配置。

## 重建与验证

`Scripts/TerrainSurfaces/build_assets.py` 导入并配置资产；`build_preview.py` 填充空白预览关卡，`finalize_preview.py` 完成预览设置；`validate_assets.py` 检查材质编译、材质槽、纹理引用、压缩、颜色空间、运行时尺寸和源资产哈希。

脚本只应在已确认的本项目 Unreal 编辑器中通过 MCP 执行。重建会更新上述新资产中的参数；手工制作的变体请另存名称。
