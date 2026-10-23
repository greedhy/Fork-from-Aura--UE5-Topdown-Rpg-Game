# 模式选择与局域网房间

## 玩家流程

1. 正常进入存档选择，选择已有存档并点击“开始”。现在先打开模式选择，不立即换图。
2. **单人模式**：进入 `BP_LoadScreenGameMode.DefaultMap` 配置的默认地图，当前为 Dungeon。
3. **多人模式 → 创建房间**：进入大厅，自动生成 6 位房间密码。大厅显示当前密码、玩家列表，以及房主的“设置密码”“开始游戏”按钮。
4. **多人模式 → 加入房间**：输入房主提供的密码，搜索同一局域网内的房间并连接。匹配失败、房间已满、密码已修改或连接失败会弹出中文提示，可以关闭提示后重试。
5. 房主开始游戏时，所有房间成员一起进入默认地图。大厅 UI 被移除，恢复游戏输入。

密码可以修改为 6–12 位英文字母或数字，区分大小写。修改后已加入的成员保持连接，新成员需要新密码。相同密码匹配到多个房间时会提示房主改密，不会随机加入其中一个。

默认容量为 **2 人**，与现有 Dungeon 出生点配置一致。房主可以单独开始。其他成员只能等待或离开，不能修改密码或开始游戏。房主关闭房间后，其他成员回到模式选择并收到提示。

编辑器内从主菜单体验时，可以使用两个独立游戏进程，也可以设置 PIE 为 `Play Standalone`、2 个玩家（同一进程），然后分别通过游戏界面创建/加入房间。PIE 预先设置成自动连接的客户端会绕过这套正常的菜单登录流程。

`Config/DefaultEngine.ini` 的 `[ConsoleVariables]` 已配置 `net.AllowPIESeamlessTravel=1`。大厅与关卡传送依赖无缝换图保留现有连接；UE 默认在单进程 PIE 禁用此功能，会退回断线重连流程，导致房主进图而其他玩家掉线。此设置随编辑器启动加载，仅影响 PIE 的换图限制，不改变独立游戏的联机规则。

## 资产与配置

| 内容 | 项目路径 |
|---|---|
| 模式/多人/密码/大厅页面 | `/Game/BluePrints/UI/Rooms/WBP_ModeAndRoom` |
| 大厅地图 | `/Game/levels/RoomLobby` |
| 存档 HUD 页面入口 | `/Game/BluePrints/UI/HUD/BP_LoadScreenHud.RoomMenuWidgetClass` |
| 大厅地图引用 | `/Game/BluePrints/Game/BP_MyGameInstance.RoomLobbyMap` |
| 单人和房主默认目标地图 | `/Game/BluePrints/Game/BP_LoadScreenGameMode.DefaultMap` |

页面控件树由原生 `RoomMenuWidget` 构造，复用了现有红色按钮和背景素材；蓝图作为可配置类入口。布局和页面行为位于 `Source/test_25d/Private/UI/Widget/RoomMenuWidget.cpp`。

容量由 `RoomSubsystem` 的 Game 配置读取。需要增加人数时可在 `Config/DefaultGame.ini` 添加：

```ini
[/Script/test_25d.RoomSubsystem]
MaxPlayers=4
```

增加容量时也需要为目标关卡配置足够的 `TravelPlayerStart` 玩家槽位，或配置共享出生点。默认没有更改现有地图的出生点和传送点规则。

多人世界仍沿用现有项目的房主存档规则，本次没有增加远端角色存档文件上传或云同步。各客户端保留自己的存档选择和显示名；背包通过已有服务端身份与持久化流程初始化。

## 实现约束

- 使用 `OnlineSubsystemNull` 的 LAN 会话发现，需要连接同一局域网；不提供跨互联网匹配。
- 搜索广播包含项目协议标识、密码指纹和是否允许加入。真正建立连接时服务端再次检查密码、容量和开始状态。这是局域网房间口令，不是互联网账号认证。
- 创建、搜索、加入、改密、销毁都有操作状态和超时，操作中禁用重复点击。异步委托在完成、退出和销毁时清理。
- 游戏开始后停止匹配新成员；房间内已有成员通过 ServerTravel 一起进入地图。
- 新大厅地图通过 GameInstance 蓝图的软引用进入资产依赖，避免只有字符串换图路径而漏掉打包依赖。

## 验证与重建

- `Scripts/Rooms/author_assets.py`：编辑器内创建/检查本次资产并设置入口。
- `Scripts/Rooms/check_runtime_classes.py`：确认编辑器已加载新增原生类。
- `Scripts/Rooms/launch_probe.ps1` 与 `verify_network.py`：用独立游戏进程验证真实 LAN 发现、连接、UI 按钮委托和地图切换。
- `Scripts/Rooms/verify_pie_travel.py`：在 LoadMenu 开启两个 Standalone PIE 窗口后，通过编辑器 Python 执行。验证存档选择、创建/匹配、双人进图、角色控制和移动同步；报告在 `Saved/Rooms/PIE/`，临时 `RoomPIE_*` 存档测试结束后删除。脚本不设置换图 CVar，验证的是项目实际加载的配置。
- 开发验证桥仅在 `WITH_DEV_AUTOMATION_TESTS` 下编译，并需要显式的 `-RoomProbe` 与 `-RoomProbeRun` 参数；正常游戏和 Shipping 构建不启用。
- 验证使用独立 `RoomQA_*` 临时存档，正常退出时删除，不覆盖用户存档。截图由实际游戏视口生成。

最终验证结果：

- `Saved/Rooms/Regression-Final/index.json`：61 项自动化测试通过，0 失败。19 项包含既有测试角色骨骼网格/插槽等警告。
- `Saved/Rooms/Network/r20261022d/validation.json`：三个独立游戏进程完成 27 项检查，覆盖单人默认地图、正确/错误密码、满房、服务端直接连接校验、改密与旧密码失效、进出/重建房间，以及双人进入 Dungeon。
- `Saved/Rooms/asset_validation.json`：页面类、HUD 入口、大厅打包引用、默认地图及未保存内容检查。
- `SourceArt/Rooms/ModeSelection.png`、`Lobby.png`、`JoinFailure.png`：实际游戏界面截图。

2026-10-22 PIE 换图修复复验：重启编辑器后确认自动加载 `net.AllowPIESeamlessTravel=1`，两个 Standalone PIE 窗口通过 LAN 密码匹配后一起进入 Dungeon，两端各有角色且大厅 UI 已关闭。通过 Enhanced Input 注入移动并核对服务端位移与客户端同步，结果通过：`Saved/Rooms/PIE/1161c5f90b4442d4bdf9358d5864c78a.json`。开始换图由游戏定时器调用，避免编辑器 Python 的 `FEditorScriptExecutionGuard` 将网络 RPC 强制变成本地调用。

本次 LAN 验收在同一台电脑的独立进程之间完成，使用真实 UDP 会话发现和网络连接；未使用两台物理电脑验证路由器隔离或防火墙设置。按钮由开发验收工具调用实际 UMG 点击委托，未模拟人工鼠标操作。
