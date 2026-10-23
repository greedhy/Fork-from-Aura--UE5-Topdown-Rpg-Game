# 验证、完成标准与恢复

根据变更范围执行，不把每种 GA 都强塞进同一套 Nova 测试。发现阻塞时继续独立可完成工作，并准确保留未验证项。

## 证据分层

| 层 | 实际证明 | 不能替代 |
| --- | --- | --- |
| C++ 构建 | 当前 Editor target 编译/链接成功 | 当前编辑器新类已加载、蓝图配置正确 |
| 资产验证 | GA/GE/Cue 可加载、CDO/目录/输入/UI 图读回符合构建记录 | 实际激活、真实键鼠和 UI 操作 |
| 自动化 World | 实际 GA 与 GE 的业务规则、状态和伤害结果 | 多客户端复制、渲染/视觉质量 |
| 单人 PIE | 真实角色授予、ASC 激活、资源/冷却、Cue 组件 | 键盘输入（若仅 ASC 调用）、菜单交互、联机 |
| 输入/UI 验收 | 实际按键/点击触发与正确状态 | 远程客户端权威一致性 |
| 联机验收 | 客户端发起、服务端仅一次结算、远端收到表现 | 专用服务器/延迟条件（若未测试） |

工具返回“按键被拒绝”应列为未验证；不能用 CDO 映射正确替代输入成功。NullRHI 不用于视觉验收。

## 资产检查最少项

核对实际目标 GA 的父类、身份标签、等级数值、Cost/Cooldown 引用、GE Mana modifier 属性/运算/曲线、冷却 Component 标签、网络策略、阻挡标签和生命周期入口。Cue Tag、资源、搜索目录一致。注册行唯一；授予和槽位符合请求；技能树标签与控制器/选择委托连接存在。

运行报告采用唯一目录或新的 run_id；断言文件不是前次遗留。不能把 authoring 脚本自身的 configured=true 作为唯一验证。

## 行为测试选择

新技能复用 `Source/test_25d/Private/Tests/ArcaneNovaTests.cpp` 的测试 World/ASC 初始化方法，加载**本次保存的真实 GA/GE**，只保留相关测试设施。不要替换 ArcaneNova 的测试文件或继续断言旧数值。

- 瞬发范围：边界内外、自身/友军/死亡/无ASC排除、碰撞去重、等级伤害、空放、一次扣费、多目标、冷却重复拒绝、资源不足、阻挡状态、正常结束。
- 伤害：真实 GE_Damage/ExecCalc 扣血；可控属性下校验抗性/护甲等实际通路，避开随机暴击等未控制因素。
- 投射物/近战：每次命中次数、动画中断、目标丢失、服务端生成/结算、残留碰撞/任务清理。
- 持续/被动：重复激活/装备、松键/取消/卸下、死亡/离开范围、GE/计时器/委托/Cue 清理，读取存档不重复叠加。测试 load→卸下/替换→重装→再次存取；已学 Spec 不能因 ActivateOnce 结束而消失，旧被动不能因残留 Equipped 而复活。
- 接入：旧存档已有 Spec 等级、状态和槽位保持；新增条目按等级 Eligible；重复扫描不重复授予；技能点学习、升级、装备、保存恢复。
- 参数微调：真实 CDO 数值和实际扣费/冷却，涉及共享资产时确认其他引用不变。

ArcaneNova 测试样例创建瞬态 World、注册 AttributeSet、设置 ActorInfo、控制属性并使用 FEditorScriptExecutionGuard。它跳过 AI BeginPlay，不是完整战斗场景，不掩盖这层局限。

## 自动化执行

确认已有新编译产物与保存资产后，给本次测试选择唯一报告目录、精确测试前缀和明确的预期测试名称。以下变量先根据当前构建记录赋值；不要硬编码 Nova 的四项测试数量：

```powershell
& (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') $ProjectFile `
    -unattended -NullRHI -nosplash -nop4 `
    "-ExecCmds=Automation RunTests $TestPrefix" `
    '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$ReportPath" "-abslog=$LogPath"
if ($LASTEXITCODE -ne 0) { throw "Unreal test process failed: $LogPath" }
$Report = Get-Content -Raw -LiteralPath (Join-Path $ReportPath 'index.json') | ConvertFrom-Json
$ActualNames = @($Report.tests | ForEach-Object { $_.fullTestPath })
if (-not $Report.tests -or $Report.failed -ne 0 -or $Report.notRun -ne 0) { throw 'Tests incomplete or failed' }
foreach ($ExpectedName in $ExpectedTests) {
    if ($ExpectedName -notin $ActualNames) { throw "Test missing: $ExpectedName" }
}
if (@($Report.tests | Where-Object { $_.state -ne 'Success' }).Count -gt 0) { throw 'Non-success test state' }
```

确认本引擎报告的 fullTestPath/state 字段；有 schema 差异先读报告再调整解析。记录测试名称、数量和状态。进程退出0但零测试/旧报告/遗漏用例都不能算通过。更改共享 ASC/标签/存档逻辑时，补跑受影响原有能力与存档回归；范围明确的配置修改不重复无关大型测试。

## PIE/联机

真实角色测试选择使用正确 GameMode 的战斗图。参考项目 Dungeon 能生成 BP_Player；NewMap 基础 GameMode 不能替代。使用新启动的隔离 PIE/测试存档，事前确认角色存活、资源/冷却状态，不写回用户存档。

验证真实授予的能力，而非临时 GiveAbility 绕过接入；如果为了独立单元测试临时授予，说明范围。演示实际按键和菜单动作；无可用输入工具时列出最小人工验收步骤，并继续其他自动检查。

要求多人时至少验证 Listen Server 的远程客户端发起、服务器只扣一次资源/伤害、其他客户端可见 Cue、取消/被动退出同步；按任务需要加延迟和 Dedicated Server。记录角色网络角色和实际观测，不能仅凭 ServerOnly 配置宣称联机通过。

## 恢复与交付

- MCP pending：保存 job_id，继续查询；不要重发 mutation。未知提交：先对照回执、服务器任务和资产状态。
- Python/编译失败：定位失败资产，修复后从缺失步骤续跑；以独立读回决定哪些已完成。
- 共享资产部分写入：保留其他用户修改，按变更清单定点修复；只有确定无后续编辑时才考虑恢复对应备份。
- 工具不可用：交付已完成代码、可执行资产/验证脚本、精确续跑命令，明确“资产未生成/编译未验证”等状态。

最终报告包含：实现规则与用户可见行为；源文件和资产清单；入口/键位/学习装备方法；构建/资产/测试/PIE/联机各自证据；未覆盖项目和下一步。不要报告笼统的“全部通过”。
