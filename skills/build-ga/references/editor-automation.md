# 编辑器自动化

## 工程与构建前置

1. 读取 `.uproject`、目标 `Source/*Editor.Target.cs`、模块 Build.cs、`.mcp.json`。引擎路径通过当前安装/引擎关联确认；不固定机器用户名。当前参考工程模块/目标分别是 test_25d/test_25dEditor。
2. 编辑新 UCLASS/USTRUCT/UPROPERTY 或原生标签后，先保存本次资产，正常关闭对应编辑器、完整构建、重新打开工程。检查其他未保存工作；不能强杀编辑器或擅自丢弃用户修改。若不能安全关闭，完成源码和资产脚本，明确待重启阶段。
3. 构建示例（先把变量赋成已核实的绝对路径/目标）：

```powershell
& (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') `
    $EditorTarget Win64 Development "-Project=$ProjectFile" -WaitMutex -NoHotReloadFromIDE
if ($LASTEXITCODE -ne 0) { throw 'Editor build failed' }
```

正常启动项目后重新握手；旧 instanceUuid 不能跨重启复用。通过只读 Unreal Python 验证 `/Script/<Module>.<Class>` 可加载及新标签可请求，再写依赖资产。不能把 DLL 编译成功等同于当前编辑器已加载它。

## MCP 通道

优先使用环境已提供的 SOMOLMCP 工具。只提供本地 HTTP 端点时，随附辅助脚本可直接调用；Python 3.10+ 标准库即可。脚本显式接收工程根目录，核对 initialize 返回 projectPath/instanceUuid，将回执写入唯一的 `Saved/GAAuthoring/<Ability>/<uuid>/receipts/`。

从工程根目录运行（若技能在用户目录，替换脚本为实际绝对路径）：

```powershell
python -B skills/build-ga/scripts/mcp_call.py --project . --ability ArcanePulse call tool_catalog
```

默认空参数返回工具分组。将工具请求写成 UTF-8 JSON 文件，再传 `--file`，避免 PowerShell 对引号、美元符号的二次解释。例如工具发现文件内容：

```json
{"mode":"schemas","names":["blueprint_get_execution_flow","dataasset_get_property","console_exec","asset_duplicate","blueprint_compile","asset_save","umg_widget_tree_list","umg_widget_tree_inspect_properties","umg_widget_tree_set_widget_properties"]}
```

```powershell
python -B skills/build-ga/scripts/mcp_call.py --project . --ability ArcanePulse call tool_catalog --file $SchemaRequest
```

缺少工具时按 catalog 的 names/query 查找，并按 next_cursor 翻页；不取完整 tools/list。参数以本次 schema 为准。

已验证的项目工具形状（仍先发现 schema）：

```json
{"source_asset_path":"/Game/SourceGE","destination_asset_path":"/Game/TargetGE"}
```

```json
{"command":"py \"C:/absolute/project/Scripts/configure_ability.py\""}
```

```json
{"asset_path":"/Game/Tree","widget_name":"VerifiedEmptyWidget","properties":{"AbilityTag":{"TagName":"Abilities.Arcane.ArcanePulse"}}}
```

以上路径/控件是形状示例，须替换成已读回目标。只对明确资产清单执行编译和保存。

脚本退出码：0=工具完成；2=任务仍待完成/查询中断；1=失败、阻塞、工程不匹配或提交结果未知。退出码 0 不保证 console 内部 Python/编译或业务验收成功。

```powershell
python -B skills/build-ga/scripts/mcp_call.py --project . --ability ArcanePulse --wait 0 job $JobId
```

`job` 只调用 jobs/get，不重提原操作。每次查询记录回执。job 属哪个编辑器实例需对照 binding 回执；重启后找不到旧 job 时核对已保存资产再决定下一步。若提交 HTTP 超时没有 job_id，检查已保存 request/unknown 回执、工具目录中的作业查询能力、编辑器日志和资产状态。**不要直接重跑整段创建脚本。** blocked/failed 时定位具体原因，修复后仅继续缺失步骤。

## 本能力的资产脚本

让自动化代码放在 `Scripts/GA/<Ability>/` 或项目既有合适目录。将配置、读回验证拆为独立执行阶段。运行时参数/结果用本次唯一目录，结果包含 run_id、目标资产列表、每项检查及总状态，避免旧报告假阳性。

开始前检查资产清单、源模板存在、目标同名资产的真实父类/身份、共享引用、输入槽/树位置；保存必要备份。备份应是本次运行的新快照，不能复用数天前 Saved 中的同名备份。编辑器中的未保存状态与磁盘备份不同，先处理待保存修改再操作。

重入规则：不存在则创建；存在且身份/父类一致则按目标值更新并验证；身份不一致则停止该项。数组按标签/类键更新或追加，保留其他行和数组成员。写后独立读回；部分失败保留已完成清单，不自动覆盖整份共享二进制备份。

### Blueprint/CDO

```python
import unreal

cls = unreal.EditorAssetLibrary.load_blueprint_class(asset_path)
assert cls, asset_path
defaults = unreal.get_default_object(cls)
# 使用从实际对象确认的 editor_property 名称；执行目标变更。
bp = unreal.load_asset(asset_path)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False), asset_path
```

创建新蓝图优先用 schema 已确认、当前版本可用的工具。项目 SOMOLMCP 3.13.5 + UE5.8 记录过 blueprint_create 预建空包后误报已存在；只在该问题实际出现时，先查资产状态，再用 `BlueprintFactory` 的 parent_class + `AssetToolsHelpers.get_asset_tools().create_asset`（参考现有 create_arcane_nova_blueprints.py）。不改插件源码来绕过一次资产创建问题。

### Cost GE

- 从兼容现有 GE 复制后，读 modifiers 的属性和运算，确认目标是 MyAttributeSet.Mana、Additive，不能只检查 `len==1`。
- 固定耗蓝20对应 Instant、ScalableFloat=-20；清除该 magnitude 的 CurveTable 与 RowName，保留其他明确需要的 modifier。
- 为零消耗技能可以没有 Cost GE，匹配其 CanActivateAbility 规则。

`configure_arcane_nova_assets.py` 展示了 ModifierMagnitude.import_text 的局部结构赋值。按真实字段类型构造，写后再读所有关键字段，确认部分导入没有重置属性或运算。

### Cooldown GE（当前 UE 5.8 项目）

- HasDuration，duration_magnitude 与等级规则一致。
- 在 `ge_components` 找到 `TargetTagsGameplayEffectComponent`，配置 `InheritableGrantedTagsContainer` 的 Added/Removed/CombinedTags；确认源冷却标签不再遗留。
- 不能只写旧 InheritableOwnedTagsContainer。最终以 ASC 持有新冷却标签、过期后移除为准。
- 从父类继承旧标签时需要正确 Removed，不能把 CombinedTags 写成目标值就假设继承语义正确。无合适 component 时先确认当前引擎的添加接口或改用有正确 component 的模板。
- 只有需求明确共享冷却时才沿用其他技能的标签。

### GA/Cue 与接入

- GA：AbilityTags、StartupInputTag（需要时）、DamageType/Damage/成长、DamageEffectClass、Cost/Cooldown 类、ActivationBlockedTags、网络策略及原型专用参数。
- 复用基类默认值也要读 CDO；蓝图序列化值可能覆盖新 C++ 默认值。原生完整执行的 GA 不再添加第二套 Activate/Commit 蓝图流程。
- Cue：Tag→GC 映射、配置路径、资源引用、生命周期；专用服务器跳过视听。Static Cue 适合一次脉冲，持续效果考虑生命周期明确的 Cue/组件。Cue 内不执行伤害。
- 目录、授予、输入、树位置、旧档按 [项目地图](project-map.md) 完成。只保存本次明确触碰资产。

## 执行完成信号

每个作者脚本成功到达末尾才写 `authoring-result.json`，包含本次 run_id 与成功资产。异常时输出失败项，不伪造 configured=true。之后独立验证脚本从真实 CDO/数组/图读取结果；两份报告均属于本次运行才进入运行时测试。
