# 装备与词缀制作流程

更新于 2026-10-31。规范来源：[装备开发规范](equipment-development-standard.md)、[装备接入指南](2026-10-30-equipment-guide.md)。执行入口：[build-equipment](../skills/build-equipment/SKILL.md)。

## 选择制作路径

| 请求 | 配置入口 | 实现边界 |
|---|---|---|
| 固定装备 | DT_Equipment + 专属 GE + CT_EquipmentStats | 静态或曲线加法，Infinite/Channel1；按需新建 GE，不改药剂效果 |
| 随机装备 | DT_Equipment + GenerationProfile + 品质/词缀表 + GE_Equipment_Random | 共用 20 属性 GE，每件独立 Spec；实际数值在服务器生成并保存 |
| 新后缀 | DT_EquipmentAffixes | 名称、权重、适用 Profile、互斥组、Tier、等级范围、属性上下限与精度 |
| 新属性类型 | EquipmentStats 注册表、AttributeSet 与模板/校验/测试 | 当前全部 20 项持久属性已接通；当前资源和伤害/经验元属性不允许 |
| 百分比/总乘/触发能力 | 需要另行设计实现 | 当前制作流程仅加法，不将字段新增误当作运行支持 |

## 从配置到验收

| 步骤 | 要做的事 | 验证点 |
|---|---|---|
| 1. 盘点 | 读取真实表行、GE、图标、槽位与稳定 ID；确认新增还是修改 | 不把已存在固定 ID 改成随机类型；保留已有设计师数据 |
| 2. 配置 | 固定装备配曲线；随机装备配基础范围、品质和后缀 | Tag 来自 EquipmentStats；原字段拼写不随显示名改变 |
| 3. 模板 | GE 持续策略 Infinite、Period=0、Stacking=None、Channel1 AddBase | Tag 对应正确 Attribute；属性不可重复；实例值不能超出模板支持集合 |
| 4. 制作资产 | 反射/原生 Tag 改动先完整构建重启，再执行资产脚本、保存并读回 | 编辑器锁定时先保存关闭；不得依据脚本文件存在宣称资产已制作 |
| 5. 接入 | 目录引用装备表和生成表，配置拾取类与允许槽位 | Soul → E 拾取 → 背包 → 装备；新增样例不重复追加 |
| 6. 数值验证 | 真实基础 GE + 装备，逐属性检查增量、两件独立移除与派生属性 | 卸下还原、资源不超上限、不利用换装补满；恢复不叠加 |
| 7. 实例验证 | 保存 GUID/RollData，经过穿脱、丢弃、复制、存档恢复 | 不重新随机；旧物品不受新抽取范围变化影响 |
| 8. 交付 | 说明资产、表格入口、报告和试玩方式 | 区分自动化、PIE、实际键鼠与联机；尚未执行的阶段明确列出 |

## 可复用脚本

| 脚本 | 用途 | 重跑规则 |
|---|---|---|
| `Scripts/Equipment/author_examples.py` | 固定装备初始化样例 | 缺失资产创建；不是覆盖同步全部策划值的工具 |
| `Scripts/Equipment/author_random_equipment.py` | 三件随机装备与生成表初始化 | 保留已有行，向既有入口生成器追加缺失样例 |
| `Scripts/Equipment/author_all_equipment_suffixes.py` | 20 属性后缀与共用 GE 迁移 | 只补缺失后缀；明确重建共用 GE Modifier 列表，其他 GE 不修改 |
| `Scripts/test_equipment.ps1 -AllProjectTests` | 编译并运行项目原生回归 | 检查新鲜 index.json 和实际测试结果 |
| `Scripts/Equipment/pie_random_equipment_probe.py` / `pie_random_equipment_network_probe.py` | 首版三属性样例 PIE 探针 | 扩展属性后要更新断言以考虑主属性引起的派生加成；不能直接作为全属性验证 |

## 当前技术约定

服务器读取定义与表格，生成 GUID + RollData。装备时将基础属性与词缀按 Tag 求和，填入独立 Spec 的 SetByCaller，然后 Apply 到玩家现有 ASC。每件装备保存自己的 Active GE Handle；卸下只移除对应效果。GE 蓝图是共享模板，不是单件装备数值的保存位置。

完整 20 属性、Tag、后缀及当前运行证据见 [全属性扩展](2026-10-31-equipment-all-attributes.md)。表格原理见 [随机装备指南](2026-10-31-random-equipment-guide.md)。新增后缀使用对应属性的 ExclusiveGroup，Profiles 空数组代表通用词缀；调参后既有实例不重抽。

示例调用：`$build-equipment 新增随机戒指，基础最大生命 20～40，允许力量和火焰抗性后缀，保留旧装备与药水，制作资产并验证穿脱和保存恢复。`
