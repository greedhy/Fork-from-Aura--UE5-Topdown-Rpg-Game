# 第四批原型与组合 GA

用户目标：沿用已批准的原型→组合→联机验证流程，继续扩展库，并生成可学习的完整 GA。

范围：3个新原型、4个组合，均有独立配置和身份，不初始装备。复用现有GAS、运行体、预算与特效。实现记录和证据在 Saved/GAAuthoring/Batch4。

## 行为合同
- Delay（枚举15）：固定施放/事件位置，等待 ArmDelay 后仅一次 OnExpire；自身不造成伤害。必须有OnExpire，禁止OnHit/OnPeriod，Duration>=ArmDelay且ArmDelay>=0.1。取消、施法者死亡不触发，目标移动不移动标记。大帧跨过时间也只派生一次。
- Ring（16）：瞬时水平空心圆，InnerRadius<=目标中心水平距离<=Radius，高度差不超过ShapeHalfHeight；墙体阻挡，忽略友军/死亡/无ASC；每敌人一次。支持OnHit/OnExpire，不支持OnPeriod。
- Line（17）：水平定向矩形，从原点向前Range、全宽Width、高度差ShapeHalfHeight；目标中心测试、墙体阻挡、每敌人一次。根GA从施法者位置沿鼠标水平朝向，子节点从事件位置沿继承朝向；支持OnHit/OnExpire。
- 原型默认：Delay等待1秒→Burst(30伤害)，14MP/4s；Ring内100外360/30伤害，16MP/4s；Line长650宽140/35伤害，14MP/3s。均有等级增量。
- Aftershock：Delay(1s)→Ring(内100外420，24伤害)→OnHit Burst(半径90，12伤害)，22MP/6s。中心为安全区，命中敌人生成爆点。
- FrostFault：Line(650x140，22伤害)→OnHit Frost Surface(半径130，3秒)，20MP/5s。沿裂隙命中的敌人脚下生成减速地表。
- RippleMine：Trap(半径220，0伤害)→OnExpire Delay(.6s)→Wave(半径450，速度400，28伤害)，20MP/6s。沿用原Trap自然到期也触发的语义，12秒超时会引爆，不宣称仅敌人触发。
- HunterSentry：Emitter(每1秒、3次、5秒寿命、700寻敌)→Homing(18伤害)→OnHit Burst(半径100、10伤害)，24MP/7s。

## 执行与验收
1. 新原型测试先失败；追加枚举/配置/运行时/短描述；全量构建后原型测试通过。
2. MCP创建3原型+4组合、独立子配置、目录；保留旧条目与用户调参；读回图、标签、CD、无初始输入槽和三行描述。
3. 加载真实组合数据进行自动化行为验证；全量回归。
4. 双客户端真实输入7种GA，逐项检查服务器费用、伤害、派生节点及客户端复制、清理；菜单与三次换图保持能力/图标。
5. 一次独立只读审查，重要发现先RED再修复并复跑适当验证；最后恢复MainMenu并记录报告。

## 决策与进度
- Ruling: 原计划前三批已完成，本次作为第四批续写。选择Delay/Ring/Line是现有事件接口的有限扩展，不新增技能图编辑器或新的召唤物AI。代价：其他未指定机制留待后续批次。
- Ruling: 在当前项目原位实现，不自动提交。前序原型/联机/地表代码与资产尚未提交，干净worktree无法复用；每个共享资产修改前备份。
- Pre-flight: Line长度不能使用旧GatherTargets的Radius；新形状统一用水平尺寸和高度，查询包围球后精确筛选。新属性仅对相应Kind额外校验；保留旧枚举0..14。
- Pre-flight: Delay使用既有OnExpire，不能走通用周期路径。OnExpire只由Finish发一次，寿命不得短于延迟；取消不触发。
- 状态：完成（2026-10-23）。
- 原型4项测试Tests-Red均按缺少实现失败；实现后Tests-Initial全88项通过。
- MCP创建3个原型GA、4个组合GA及15份独立配置；目录保留旧28项，扩展为35项。首次目录写入遇到EditDefaultsOnly结构体限制，改用项目已有import_text写法续跑成功，未改动已生成数据调参。36项资产读回通过。
- Tests-Assets全90项通过（45项含既有资产/夹具警告），包括真实4组合的GE伤害、子节点数量、无子费用、7项三行短描述及真实自施放GA单次扣费/CD。
- 已启动一次独立只读审查；联机/菜单/换图验证执行中。
- 首轮联机40项、菜单4项（26入口）、三次换图24项全部通过。
- 独立审查唯一P2：Line沿用光标点3D距离和LOS前置校验，使远光标方向施放被拒绝。Ruling: Line是方向技能，光标仅选水平方向，距离/高度/逐敌人遮挡由ShapePulse负责；代价是Line与旧选点技能的光标规则有意不同。正在补入口RED测试并修复，随后复跑全量和联机。
- Final: fixed Line瞄准入口 — LineCursorOnlySelectsDirection RED→GREEN；Tests-Final全91项通过，0失败，46项含既有资产/合成World夹具警告。首次测试夹具清空控制器导致崩溃，修复夹具并明确断言激活与等待TargetData后才记录RED。独立审查无第二项阻塞问题、无延期小问题。
- 最终网络复跑暴露夹具问题：房主角色胶囊体遮住客机光标射线，实际ECC_Target命中BP_Player_C_1，Line方向(-.806,.592)偏离怪物(-80,+200)且横向距离超过半宽70。将仅QA房主移出镜头，采集真实GetHitResultUnderCursor并断言Line/FrostFault/RippleMine光标命中敌人；未修改产品碰撞或放宽伤害判定。再次验证中。
- 完成：最终二进制通过91项自动化、43项双客户端、36项资产、4项菜单、24项三次换图检查。无失败；菜单26个原型/组合入口，目录35项。已退出PIE、恢复MainMenu，无脏包，QA存档清理；未提交或推送。汇总 Saved/GAAuthoring/Batch4/completion.json，使用文档 docs/2026-10-23-ga-prototypes-batch4-guide.md。
