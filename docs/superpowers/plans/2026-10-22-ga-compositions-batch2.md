# GA 组合验证与第二批原型

用户目标：先用已有原型组合一批可学习 GA 并测试；通过后开发下一批原型。

## 实施与验收
1. 四个组合：FireSeed（Projectile→OnHit Field）、FrostFan（Multishot→OnHit Frost Surface）、BrambleMine（Trap→OnExpire Burst→OnExpire Vines Surface）、StormSeal（Field→OnExpire Burst）。各自身份、冷却、数据资产、目录及菜单；不默认装备。
2. 组合地表落地校正、短描述、菜单滚动；自动化验证真实节点及伤害、取消、地表高度；双客户端真实输入验证每个组合伤害与子节点复制，清理后无残留。成功结果写入阶段门禁。
3. 仅门禁通过后：Homing（追踪投射物）、Piercing（穿透且每目标一次）、Chain（有限跳数、最近可见敌人、衰减、禁止回跳）。复用现有事件接口和预算，独立 GA 样例。
4. 第二批同样进行自动化、双客户端施放、菜单和换图回归，独立代码审查，交付使用说明。

## 约束与记录
- Ruling: 在当前工作区执行且不自动提交；依赖前序未提交的 GAS、地表、联机实现，不能以干净 checkout 替代。
- 测试报告使用 Saved/GAAuthoring/Compositions；资源修改前备份，已有配置保留。
- Stage 1: pending. Stage 2: gated.
- Pre-flight: Surface 的落地仅存在根 GA，子节点直接 Spawn，需统一到运行时；菜单固定八项需从目录生成并限制高度。新原型枚举追加，保留旧序列化值。

- Stage 1 complete: stage1-gate.json 记录完整72项自动化、25项双客户端组合检查和4项菜单检查通过。地表 RED Z90→GREEN Z2。Stage 2 gate opened.
- Stage 2: 三原型、独立GA/配置/目录已创建；Tests-Batch2 75项全过，双客户端22项（含三目标连锁和数值端点）、目录22项、菜单15入口、连续三次换图15项通过。
- Final review: 独立只读审查确认根Surface无地面仍扣费。新增测试先发现LocalPredicted夹具未激活，已改为ServerOnly模板且显式断言激活，不能用未运行的路径宣告通过。
- Final: Ruling: 新三个Kind的OnPeriod静默无效按组合功能缺陷修正，配置校验直接拒绝；本批支持OnHit/OnExpire，避免无效果的有效配置。若需要飞行周期事件，需后续明确扩展。
- Final: Ruling: Chain.OnExpire明确在最后命中点、传最后命中目标，不能传未命中的预选目标；按组合功能缺陷修正并补RED→GREEN。其他原型的既有结束语义不变。
- Final: fixed 落地失败扣费、无效周期连接、连锁终点；Tests-GroundRed/Tests-ReviewRed均复现失败，Tests-Completion全77项通过（32夹具警告，0失败）。最终二进制的4组合25项与3新原型22项联机复跑通过。
- Complete: 最终资产22项、菜单4项（15入口）、三次换图24项（逐个能力类及图标）通过；汇总 Saved/GAAuthoring/Compositions/completion.json。编辑器回到MainMenu，无PIE、无脏包；QA存档清理，未提交。任务完成，无待修复审查问题。
