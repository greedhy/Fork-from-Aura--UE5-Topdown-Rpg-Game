# 随机装备实现计划（2026-10-31）

用户已授权实施上一轮方案。首期支持服务器生成随机基础数值、品质、前后缀及加法属性；不加入特殊触发能力、百分比、洗练或商业掉落系统。

1. 新增 EquipmentRollTypes/EquipmentGenerator：表格配置基础范围、品质权重、词缀等级/互斥组；固定 seed 可复现；结果保存实际数值、词缀显示名、版本。
2. 将统一 RollData 贯通拾取、背包本地模型/FastArray、装备、丢弃、快照及恢复；旧装备 Version=0 保持静态 GE。
3. 新增白名单 SetByCaller GE 模板，Channel1 AddBase；校验固定与随机 GE 的各自约束，按实例数值施加/重建。
4. Soul 名称、背包选中详情和装备栏读取实例词缀与实际属性；不在显示/穿戴时重抽。
5. 新增独立随机样例与三张数据表，保留现有三件固定样例及药水；出生房间追加随机样例用于验证。
6. 自动化覆盖范围/权重过滤/互斥/非法数据/稳定结果、复制与快照、穿脱/丢弃/恢复与真实初始化 GE；单机与联机 PIE 验证。记录已验证和待人工验收项。

文件职责：EquipmentRollTypes.h 为纯数据契约；EquipmentGenerator.h/cpp 为生成和结果校验/显示辅助；既有 Inventory/Backpack/EquipmentComponent 负责生命周期；EquipmentGameplayEffect 负责 GAS 模板与校验；Scripts/Equipment 负责幂等资产制作和真实 PIE；docs/skills 更新制作规范。

采用 subagent-driven-development 技能拆分独立数据生成与 UI 任务；主线程负责实例传输/GAS、构建和集成验收。共享工作区，不提交或覆盖其他修改。

## 实施记录

上述六项已落地。Editor 构建成功；项目自动化 205 项通过、0 失败；真实地图单机及 Listen Server + 远程客户端随机装备 PIE 通过，包含完整 RollData 两端一致性、真实属性增量与卸下还原。资产初始化重复运行成功，出生房间保留 8 项样例。build-equipment 技能已更新并同步安装副本。具体报告路径与待人工验收边界见 `docs/2026-10-31-random-equipment-guide.md`。
