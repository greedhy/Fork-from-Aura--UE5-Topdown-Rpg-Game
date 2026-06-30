# Fork-from-Aura--UE5-Topdown-Rpg-Game
@ -1,823 +1 @@
该项目参考原作者史蒂夫，以及CSDN暮志未晚NAN，github ShinyRuo学习笔记

该项目是基于GAS编写的地牢风格RPG游戏，俯视角模式，支持网络同步。

**<font style="color:rgb(24, 25, 28);">原始链接：</font>**

[Just a moment...](https://www.udemy.com/course/unreal-engine-5-gas-top-down-rpg/?couponCode=IND21PM)

**<font style="color:rgb(24, 25, 28);">原项目地址：</font>**

[GitHub - DruidMech/GameplayAbilitySystem_Aura: Online repo for Gameplay Ability System Course](https://github.com/DruidMech/GameplayAbilitySystem_Aura)

**视频演示：**


# 项目与引擎配置
## 资源管理类
![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722701474889-7b57f28b-3c10-4af3-bc6f-c1026fec9807.png)



<font style="background-color:#E7E9E8;">UAuraAssetManager</font> 继承 UAssetManager 在初始化引擎加载时 调用 <font style="background-color:#E7E9E8;">FAuraGmaeplayTags::InitNaviveGameplayTags</font> 添加标签并且为 单例结构体 <font style="background-color:#E7E9E8;">FAuraGmaeplayTags</font> 的成员赋值，为了方便直接通过 <font style="background-color:#E7E9E8;">FAuraGmaeplayTags</font>  设置 Tag 和使用 Tag

## 渲染与效果
卡通画风，项目素材却是4096级别，统一限制在512级别，我觉得甚至可以256级别

修改纹理流送池

```cpp
[/Script/Engine.RenderSettings]
r.TextureStreaming=True
r.Streaming.PoolSize=1000
```

## 指定GameplayCueNotify的目录
UE警告不指定目录在大型项目下可能因为遍历所有目录而导致性能损耗，因此进行指定

```cpp
[/Script/GameplayAbilities.AbilitySystemGlobals]
+GameplayCueNotifyPaths=/Game/Blueprints/AbilitySystem/GameplayCueNotify
```

## 最大RPC数量
默认两个有点不够用，参照lyra的10个

```cpp
[ConsoleVariables]
#最大RPC更新数量
net.MaxRPCPerNetUpdate=10
```

## 高亮描边
后期处理添加处理材质

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1728441216223-868d258a-3216-4c22-a189-8ee1b719fe82.png)

网格体有以下功能，开启即可高亮

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1728441119917-78a9e684-eeed-4138-ad76-2a25548bebcb.png)

## 存档
奥拉项目主要存档内容是四大属性值，技能点、属性点，技能Tag(以此判断是否学习了某个技能)、角色状态信息，当然还有地图和坐标



# Actor
## AAuraEffectActor
进行某些GAS相关的触发

定义的其他辅助类型

+ <font style="background-color:#E7E9E8;">EEffectApplicationPolicy</font> <font style="background-color:#E7E9E8;">EEffectRemovalPolicy</font> GE的应用时机和移除时机
+ <font style="background-color:#E7E9E8;">FEffectWithPolicy</font>  GE的结构体，存在GE的类，GE的应用和移除时机，是否销毁Actor

组件

+ 静态网格体（根）
+ 碰撞（用做重叠检测）
+ <font style="background-color:#E7E9E8;">FEffectWithPolicy</font> 结构体数组

# Character类
![画板](https://cdn.nlark.com/yuque/0/2024/jpeg/36214189/1721324949717-935992ed-8cf4-43bc-8a19-3fce385f55c4.jpeg)



项目所有Character都继承**AAuraCharacterBase**,并由其分出敌人和玩家类



函数：

+ <font style="background-color:#E7E9E8;">InitializePrimaryAttribute</font> 通过GE初始化部分属性，在 <font style="background-color:#E7E9E8;">InitAbilityActorInfo</font> 中调用

## AAuraEnemy
不同哥布林建立了不同的蓝图类（枪哥布林，弹弓哥布林...），而不是同一蓝图类因为武器不同而状态不同



因为所有敌人动画逻辑一样，资源不一样，因此建立了动画模板**ABP_Enemy**，子类不同的敌人类型动画蓝图只需对其继承，更改不同的动画资源即可

### 接口IEnemyInterface
游戏是俯视角游戏，不少操作需要鼠标指针交互，因此需要设计鼠标悬浮的响应

鼠标悬浮至不同的对象，需要其做出不同的反应，因此设计一个接口，响应被鼠标悬浮的事件

+ 高亮和取消高亮

### 接口 ICombatInterface
通过这个接口处理一些战斗的接口交互

+ <font style="background-color:#EFF0F0;">GetPlayerLevel</font> 获取实例的等级
+ <font style="background-color:#FBF5CB;">GetCombatSocktLocation</font> 获取插槽位置，用于定位生成的技能
+ <font style="background-color:#FBF5CB;">SetFaceingTargetLoc</font> 用 BlueprintImplementableEvent 宏修饰，旨在蓝图中覆盖，实现设置运动扭曲的相关配置

## AuraCharacter
因为俯视角游戏，镜头默认不旋转，因此不能让角色旋转继承控制器的旋转了，而且摄像机也一样，禁用控制器的旋转

函数

+ <font style="background-color:#EFF0F0;">InitAbilityActorInfo</font> 初始化GAS的 Onwer 和 Avatar, 初始化UI的控制层

### PlayerState
切换角色，角色重生**<font style="color:#DF2A3F;">不希望重写构造设置一些内容</font>**，因此将角色的部分内容放置到该类中

保存玩家状态，包括将Gas挂载到这个下面

成员变量

+ 等级 Level : 没必要放入Attribute，非浮点，不需要和GAS其他强互动，但是部分属性依赖此进行计算

### 遮挡相机的Actor进行透点蒙版透明化
设置下列值，连接Mask即可

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1726424519159-967285b6-936c-4eb8-9c82-8379ef0dcc4f.png)

直接而简单的添加碰撞盒，如果存在重叠，则通知对象调整材质节点的值进行透点化

![遮挡碰撞盒](https://cdn.nlark.com/yuque/0/2024/png/36214189/1726424577164-900beb91-daf9-4a7b-af19-c0d331b2eba1.png)

### 等级经验与升级
项目中，升级需要考虑升到下一级所需经验，升级给的点数，因此用一个DateAsset进行管理——<font style="background-color:#E7E9E8;">ULevelUpInfo</font> 

经验和等级的变化会设置 <font style="background-color:#E7E9E8;">AAuraPlayerState</font> 中的值,并且由其进行广播通知各类需要改变的内容



**如何为目标GAS添加XP的：**

+ 将添加经验视为一种被动的能力，不结束,直接等待相应的事件触发
+ 一开始便启用这种监听事件的GA(角色初始的被动能力)，GA等待事件Tag之后回调触发
+ 击杀对应的敌人后（<font style="background-color:#EFF0F0;">UAuraAttributeSet</font>::<font style="background-color:#FBF5CB;">PostGameplayEffectExecute</font> 中判断血量和伤害处），发出相应的事件Tag(<font style="background-color:#E7E9E8;">UAuraAttributeSet</font>::<font style="background-color:#FBF5CB;">SendXPEvent</font>)
+ GE应用后会修改XP这个属性(该属性是Meta类，类似Damage)，在Attribute的 <font style="background-color:#FBF5CB;">PostGameplayEffectExecute</font> 中捕捉XP的变化，并且设置给<font style="background-color:#EFF0F0;">PlayerState</font>的XP

**如何将属性点升级的:**

+ 角色开始便启用了被动监听GA(<font style="background-color:#E7E9E8;">GA_ListenForEvent</font>),该GA会等待<font style="background-color:#FBF5CB;">TagEvent</font>的信息进行执行
+ GA收到信息执行时，根据Tag注册对应的<font style="background-color:#E7E9E8;">Magnitude</font>，并且应用GE
+ GE内有各种<font style="background-color:#E7E9E8;">SetByCall</font>的<font style="background-color:#E7E9E8;">Magnitude</font>，根据标签能够设置其值，并且加上属性值

## 部分功能流程
### 死亡
应用伤害后调用接口类的 <font style="background-color:#FBF5CB;">Die</font> 函数，AuraCharacterBase中 <font style="background-color:#FBF5CB;">Die</font> 转调 <font style="background-color:#FBF5CB;">MulticastHandleDeath</font>（<font style="background-color:#E6DCF9;">服务器进行广播执行</font>）并且 取消武器的 绑定至网格

<font style="background-color:#FBF5CB;">MulticastHandleDeath</font> 中开启布娃娃，并且替换溶解材质，调用蓝图重载的函数，改变材质参数

## 角色类型与配置
面对不同的角色类型，要怎样进行配置与初始化?

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723740767688-7550a0ed-5d8a-4b9c-a420-ecebdebf6ad2.png)

+ 创建 `UCharacterClassInfo` 数据资产。
+ 创建 `ECharacterClass` 枚举。
+ 为**属性**创建曲线表。

        - a. `CT_WarriorPrimaryAttributes`（战士主要属性）

        - b. `CT_RangerPrimaryAttributes`（游侠主要属性）

        - c. `CT_ElementalistPrimaryAttributes`（元素师主要属性）

+ 为主要属性、次要属性和关键属性创建 GE（Gameplay Effect，游戏效果）

        - a. 主要属性不同 次要属性和关键属性靠同一GE计算

+ 有共享技能和效果。
+ 使用数据资产初始化属性的函数。

# Player
操控**AuraCharacter**的子蓝图类

## 控制器
建立**<font style="color:#DF2A3F;background-color:#E7E9E8;">AAuraPlayerController</font>**类作为玩家的控制器类该类主要进行：

+ 设置增强输入系统，添加增强输入操作
+ 默认显示光标
+ 设置输入模式，使得鼠标不被锁定到窗口，窗口不隐藏鼠标
+ 添加移动输入，由于控制器旋转跟随视角，且项目为俯视角，因此需要获取控制器的Yaw旋转，并且以此获取向前和向右向量来添加移动输入
+ 重写**仅有玩家输入才tikc**的事件，在里面进行调用检测鼠标悬浮的对象，以达成鼠标悬浮交互的功能
+ 使用 资产管理(DataAsset) 进行**数据驱动输入操作**

        - 存在 资产数据 <font style="background-color:#EFF0F0;">InputConfig</font> 选择相应的输入操作资产

        - 存在 <font style="background-color:#FBF5CB;">按住 按下 松开</font> 三种操作的回调函数，绑定到 <font style="background-color:#EFF0F0;">增强输入操作系统(UAuraInputComponent)</font> 

        - 该绑定将 tag 和 回调函数进行了绑定，输入操作之后调用回调时，会把tag进行参数传入

### 增强输入操作组件 AuraInputComponent
![设置增强输入类型](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722964429074-edc321c3-de41-4c86-908a-232f8f0b45cf.png)主要是 模板函数 <font style="background-color:#FBF5CB;">BindAbilityActions</font> 

+ 接受不同的函数类型，来<font style="color:#DF2A3F;">进行输入操作和回调函数的绑定</font> ;
+ 接受 资产数据 <font style="background-color:#EFF0F0;">InputConfig</font> 将资产数据内的**<font style="color:#DF2A3F;">标签</font>****作为参数绑定到回调函数**

### 按住移动
**按下之后**

+ 判定相关的操作Tag是否为 InputTag_LMB 左键
+ 按下的时鼠标悬浮下不存在可交互物品

**按住时**

+ 如果不存在交互物品
+ 按住的是鼠标左键
+ 朝向点击位置和角色位置形成的向量移动

### 按下移动值目标
**释放按钮后 **<font style="background-color:#FBF5CB;">AbilityInputTagReleased</font> 

+ 获取释放的是否为左键，并且为短按
+ 使用导航网格获取路径点，并且把每个点加入样条线组件，将最后一个点存至目标点
+ 开启 bAutoRunning 表示处于移动状态

PlayerTick 调用 <font style="background-color:#FBF5CB;">AutoRun</font> 

+ 在样条线上获取距离玩家最近的点，以及该点的切线向量<font style="color:#8A8F8D;">（用作平滑移动）</font> 
+ 向切线方向移动
+ 移动到距离最终目标给定的距离则停止移动

### 伤害飘字UDamageTextComponent
应用伤害之后（<font style="background-color:#FBF5CB;">PostGameplayEffectExecute</font>），由控制器在目标身上添加控件组件，播放飘字动画

# GAS
![GAS挂载对象](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721468623784-ef3919bf-4ac4-4bce-8ebd-c298ea25b105.png)

敌人类直接装载GAS相关组件

但是玩家有其他需求，比如重生，切换，此时**<font style="color:#DF2A3F;">不希望GAS相关的组件被销毁之后由新的实例创建，而是希望保持</font>**，因此采用<font style="color:#DF2A3F;">挂载到</font>**<font style="color:#DF2A3F;">playerState</font>**<font style="color:#DF2A3F;">的方式</font>

因此，会存在**<font style="color:#DF2A3F;background-color:#E7E9E8;">OwnerActor</font>**和**<font style="color:#DF2A3F;background-color:#E7E9E8;">AvatarActor</font>**的区别，设置时需要区别

![GAS获取所有者](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721490576558-f8351f1e-200b-4f72-bdc7-680626f3d21d.png)

如上图，因为玩家类的GAS挂载到PlayerState上，因此两个Actor的值不同。



那么，什么时候设置组件的拥有者呢？AI那边自然是简单，因为GAS就在其Character上，因此BeginPlay时，设置必定有效。

但是，玩家这边GAS的**OwnerActor**是**PlayerState**，**AvatarActor**是Character，而且还有网络复制，同步模式为`<font style="color:rgb(31, 35, 40);">Mixed</font>`<font style="color:rgb(31, 35, 40);">（详情见该模式注意事项）</font>

<font style="color:rgb(31, 35, 40);"></font>

<font style="color:rgb(31, 35, 40);">首先，要清楚，</font>**<font style="color:#DF2A3F;">客户端的实例和服务器上的实例不会完全同时一样</font>**<font style="color:rgb(31, 35, 40);">，因此在客户端上调用对象返回的内容和服务器上调用对象的返回</font>**<font style="color:rgb(31, 35, 40);">可能存在不一样的情况</font>**<font style="color:rgb(31, 35, 40);">，因此 </font>**<font style="color:#DF2A3F;background-color:#EFF0F0;">复制</font>**<font style="color:rgb(31, 35, 40);"> 这个词用的很好 </font>**<font style="color:#DF2A3F;">表示两个实例</font>**<font style="color:rgb(31, 35, 40);">，所以设置GAS的拥有者存在服务端和客户端不同时机设置的情况</font>

**<font style="color:#DF2A3F;">在pawn被控制时，这是服务端干的事，</font>**此时是**<font style="color:#DF2A3F;">服务端</font>****的GAS实例设置拥有者**

**<font style="color:#DF2A3F;">在服务器发出有PlayerState的回调时 </font>**，此时是**<font style="color:#DF2A3F;">客户端</font>****的GAS实例进行设置拥有者**

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721492214252-85062cf7-6a0f-4653-8360-8d550d04bf85.png)

## UAuraAbilitySystemComponent
按下按钮将会发出相应的Tag，**Tag标识了键位**。给想要激活的技能相应的标签，那么该技能将被 **按键Tag** 激活。也就是说——**<font style="color:#DF2A3F;">按键触发技能，给技能绑定按键标签 </font>**

辅助定义

+ 多播单参数代理 FEffectAssetTags 用以在有 GE 应用时 广播出该GE的Tag

函数

+ <font style="background-color:#EFF0F0;">AbilityActorInfoSeted</font> 当GAS的 **<font style="background-color:#EFF0F0;">OwnerActor</font>**** **和** ****<font style="background-color:#EFF0F0;">AvatarActor</font>**** **被设置之后进行调用，进行一些恰当的初始化
+ <font style="background-color:#EFF0F0;">EffectApplied</font> 绑定 <font style="background-color:#EFF0F0;">OnGameplayEffectAppliedDelegateToSelf</font> 的代理，用以有 GE 应用时进行事件处理 

        -获取GE拥有的Tag 广播到控件

        - <font style="background-color:#E6DCF9;">Client</font> , <font style="background-color:#E6DCF9;">Reliable</font> 在客户端上执行，通过网络从服务器进行复制 保证客户端正常运行，形成了客户端RPC

+ <font style="background-color:#FBF5CB;">AbilityInputTagReleased</font> 和 <font style="background-color:#FBF5CB;">AbilityInputTagHeld</font> 函数由 Controller 触发，旨在通过 Tag 找到 GA 进行触发和对应操作阶段的通知 

## UAuraAttributeSet
该项目决定将所有属性放入一个属性集合类中

次级属性依赖主要属性的数值进行设置，在初始化使用了无线时长的GE设置

因为Attribute的属性监管，和GE的无限时长，**因此依赖的属性更改，次级属性也会更改**

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722340215055-801d1888-cfbd-4613-99e3-d341c5f8fc7e.png)

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722303858778-4381ae12-23ce-4eb6-9a66-ac2c45869357.png)



因为项目存在网络同步，因此需要**<font style="background-color:#E7E9E8;">OnRep_</font>**设置对属性的网络回调函数

重要辅助内容

+ 定义 <font style="background-color:#E7E9E8;">FEffectProperties</font> 结构体 装载目标与源的控制器、AvatarActor、GAS、Character信息，并且保存GE上下文句柄

函数

+ 重载 <font style="background-color:#EFF0F0;">PreAttributeBaseChange</font> 钳制值
+ 重载 <font style="background-color:#E7E9E8;">PostGameplayEffectExecute</font> 获取信息并且应用
+  <font style="background-color:#E7E9E8;">SetEffectProperties</font> 进行 <font style="background-color:#E7E9E8;">FEffectProperties</font>  设置。在 <font style="background-color:#E7E9E8;">PostGameplayEffectExecute</font> 中进行调用，拿到一些上下文信息
+ 重载** ****<font style="background-color:#E7E9E8;">GetLifetimeReplicatedProps</font>** 函数**将需要同步的属性**通过宏 **<font style="color:#601BDE;">DOREPLIFETIME_CONDITION_NOTIFY</font>** 添加属性到网络复制中

 <font style="background-color:#E7E9E8;">GetLifetimeReplicatedProps</font> 用于注册属性（变量）进行网络同步（Replication）的方法。在 Unreal Engine 的网络架构中，只有注册了的属性才能在客户端和服务器之间自动同步。这个函数在类的定义中被重写，用于指定哪些属性应该被同步，以及如何进行同步。  

### 元属性 (Meta Attributes)
![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723912140300-8dee1cad-04a4-4a72-9ce9-39470a6d1651.png)

元属性不进行网络复制，在应用伤害前进行计算而作为一个占位符。

在生成GE的时候，通过 <font style="background-color:#FBF5CB;">AssignTagSetByCallerMagnitude</font> 读表设置值，属性更改的 <font style="background-color:#FBF5CB;">PostGameplayEffectExecute</font> 处进行让血减去 Damage 

### GameplayEffectExecutionCalculation 计算Damage
**<font style="background-color:#E7E9E8;">UExecCalc_Damage</font>**** **进行Damage 计算，影响系数有护甲、暴击、格挡等

**属性伤害加成计算**

+ GA存在一个TMAP为伤害类型Tag映射浮点数，可以在编辑器中添加，以此为GA添加属性伤害
+ **<font style="background-color:#E7E9E8;">UExecCalc_Damage</font>**** **的静态辅助结构体 AuraDamageStatics 添加映射(属性Tag 映射 属性捕获)，方便从每个伤害类型Tag直接获取到对应的属性捕获类型（GEEC获取属性需要填入属性捕获类型-<font style="background-color:#FBF5CB;">AttemptCalculateCapturedAttributeMagnitude</font> ）获取相应抗性
+ 在计算伤害时，遍历所有伤害类型标签，并从Spec中查找相应标签的修饰器的值，然后再从**<font style="background-color:#E7E9E8;">UExecCalc_Damage</font>**** **捕获抗性

### DamageType
伤害有不同类型，该项目采用的给伤害GA上Tag，以表示该伤害的类型

## AuraGameplayAbility
<font style="background-color:#E7E9E8;">AuraCharacterBase</font> 存在 <font style="background-color:#E7E9E8;">StartupAbilities</font> 用来储存 角色初始拥有的技能

通过 <font style="background-color:#E7E9E8;">FAuraGmaeplayTags</font> 添加输入相关的标签与对应的输入 <font style="background-color:#E7E9E8;">IA</font> **方便按键配置对应技能触发 **

****

技能分为**主动和被动**，采用Tag的方式区分

**派生类**

+ **<font style="background-color:#E7E9E8;">UAuraDamageGameplayAbility</font>**** **为带伤害相关

### 冷却
继承 <font style="background-color:#EFF0F0;">UBlueprintAsyncActionBase</font> 实现蓝图的异步节点，通过 <font style="background-color:#EFF0F0;">UWaitCooldownChange</font> 异步任务让**UI执行**冷却相关逻辑

<font style="background-color:#EFF0F0;">UWaitCooldownChange</font> 类中的代理变量则是执行引脚，该类就 <font style="background-color:#CEF5F7;">CooldownStartDel</font>(进入冷却) 和 <font style="background-color:#CEF5F7;">CooldownEndDel</font>(完成冷却) 两个分支

**否完成冷却：**通过目标GAS的目标Tag(冷却类Tag)数量是否为0来判断

**是否进入冷却：**通过目标GAS应用的GE是否带有冷却Tag来判断

### 点击移动
![移动曲线](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723048236064-b0b66e26-3f85-4edc-9080-f75556a0de9f.png)

如上图，通过**样条线让路径更加平滑**

### 发射投射物技能 AuraProjectileSpell
所有发射投射物技能的基类

**函数**

+  <font style="background-color:#FBF5CB;">SpawnProjectile</font> 

           - 仅服务器生成技能

           - 从接口获取生成位置 进行延迟生成

           - 途中设置旋转，GE

+ <font style="background-color:#FBF5CB;">EventActivateAbility</font> 

          - 调用自写的 AbilityTask <font style="background-color:#FBF5CB;">TargetDataUnderMouse</font> 获取鼠标下的信息，等待消息的回调执行技能释放

          - 设置运动扭曲的目标，播放施法动画，等待动画通知发送tag 而生成发送物

+ OnSphereOverlap

           - 触碰之后播放效果。

           - 服务器进行销毁发射物

           - 可能存在客户端还未播放效果，导致服务器删除发射物之后，客户端没办法播放效果，因此加个标记进行**判断客户端是否已经播放效果，如果没有，则在销毁时，客户端再进行播放**



**执行** 

+ 播放施法蒙太奇，等待tag的通知—— <font style="background-color:#FBF5CB;">WaitGameplayEvent</font> 

         - Tag 由动画通知中重载<font style="background-color:#FBF5CB;">RecivedNotify</font> 的函数中发送(<font style="background-color:#FBF5CB;">SendGameplayTagToActor</font>)

+ AbillityTask类 <font style="background-color:#FBF5CB;">UTargetDataUnderMouse</font> 获取到一些鼠标下的消息

        - 重写 <font style="background-color:#FBF5CB;">Activate</font> 判断客户端与服务端，客户端直接广播  ,服务端监听之后 回调 再进行广播

+ <font style="background-color:#FBF5CB;">SendMouseCursorData</font> 整个期间被预测，向服务端发送包装数据，并且代理将其广播

### 闪电
闪电需要按住之后持续释放，松开按钮取消施法。在GA中用**等待输入松开的事件(GAS自带)**，因此执行相应的事件，在项目已经写好相应的输入调用下，在GAS组件对应的输入执行处调用事件( <font style="background-color:#FBF5CB;">InvokeReplicatedEvent</font> 进行回调触发)

**流程逻辑：**

+ 获取鼠标指向的位置为末端，角色武器插槽为起始，作为粒子的端点
+ 两端点间发射球形检测，如果触碰到敌人类，则以敌人为中心和原点，周围N个敌人的位置为末端点，同样设置添加粒子
+ 按住施法的过程中，持续提交法力消耗。从DamageG中提取相应伤害数值制作相应伤害GE应用给敌人(为了防止直接应用DamageGE而造成多次debuff)

**眩晕:**

+ 网络同步方面，采用布尔标记是否进入眩晕状态，使用网络回调的方式根据眩晕与否设置其移动速度，操作阻断(上Tag)
+ GAS安置完成之后，注册代理，监听眩晕Tag的数量，敌人类设置黑板变量

### 元素水晶
元素水晶从地面生成，以生成点为中心，造成径向伤害

**法阵指示物 AMagicCircle：**

+ 透贴材质，跟随鼠标移动
+ 于 <font style="background-color:#EFF0F0;">AuraPlayerController</font> 中添加与销毁

**生成点位 APointCollection：**

+ 生成点位是提前设置好相对位置的Actor
+ 能够根据输入参数进行旋转，获取点位到地面的投影位置

**技能触发：**

+ 第一次触发技能生成法阵指示物，标识生成区域
+ 第二次触发释放技能，使用Timer进行异步生成水晶
+ 在水晶生成的位置添加径向伤害，已在 <font style="background-color:#EFF0F0;">AuraDamageGameplayAbility</font> 中添加径向伤害相关的属性
+ 如果开启了径向伤害，击退逻辑已经改为根据径向原点计算，伤害径向化在 <font style="background-color:#EFF0F0;">UExecCalc_Damage</font> 计算每项伤害时进行
+ **径向原点必须在GA生成伤害参数( ****<font style="background-color:#FBF5CB;">MakeDamageEffectParamsFromClassDefaults </font>****)之前调用！！！**

### 火元子
火元子会向其向量方向飞，再返回爆炸

+ 添加了设置伤害参数内单项的函数，方便设置里面的具体内容
+ 调用生成圈行点位的函数，每个位置生成火元子
+ 火元子采用TimeLine进行插值飞到远处，使用Timer返回到玩家
+ 当到达玩家周边一定距离，火元子爆炸，设置伤害参数，拥有伤害
+ 调用GC的非复制执行GC函数(复制RPC调用占用，而且火元子类已经有网络复制)，播放爆炸效果

### 受击反应 HitReact
在属性值修改中 (<font style="background-color:#FBF5CB;">PostGameplayEffectExecute</font>),让血量减少伤害之后，如果没有死亡，则进行受击

通过Tag激活相应GA

GA流程：

+ 应用GE (上受击TAG)
+ 播放受击动画
+ 移除GE

### 近战攻击 AuraMeleeAttack
<font style="background-color:#F4F5F5;">UAuraMeleeAttack</font> -> <font style="background-color:#F4F5F5;">UAuraDamageGameplayAbility</font>

定义结构体 <font style="background-color:#F4F5F5;">FTaggedMontage</font> 使得 攻击动画 对应 攻击标签，用 标签区分 攻击是左手还是右手亦或是武器而分别处理

由于GA仅在服务器和拥有者处，在GA中直接播放的特效不会被复制到其它客户端，因此采用Cue播放音效和血溅

### 召唤技能 AuraSummonAbility
萨满能召唤随从，存在最大数量限制

算出生成点之后，延迟一定时间生成库内的敌人

### Debuff
负面效果一定是从伤害类型的GA生成的，伤害类GA中有所需的<font style="background-color:#E7E9E8;">FDamageEffectParams</font>，在伤害类型的GA中生成伤害类型GE时，<font style="background-color:#FBF5CB;">MakeDamageEffectParamsFromClassDefaults</font> 生成其参数即可

为GE上下文添加了变量，使得debuff所需的参数传入GE上下文



蓝图库写了 <font style="background-color:#FBF5CB;">ApplyDamageEffect</font> 应用GE的函数，传入<font style="background-color:#E7E9E8;">FDamageEffectParams</font>参数调用即可

+ 将参数解析，为GE的修饰器添加tag与其数值
+ 在**计算伤害的类**中解析GE修饰器中的值，处理之后传入GE上下文
+ 在属性集**投递伤害中**根据GE上下文判断是否应用Debuff，并且解析上下文数据，创建一个新的GE作为Debuff的GE

           -因为GE周期策略不同、防止因debuff循环调用。因此要根据GE上下文数据生成新的GE应用

## 被动技能 AuraPassiveAbility
被动技能只要装配在技能槽中，就一直触发；技能同步为服务器开启，客户端也运算。

因此主要开启与关闭技能的逻辑是在技能装配时发生

+ 如果装备的插槽不是空的，则需要先清除之前的技能，如果清除的技能是被动技能，则停止技能
+ 如果装备的被动技能之前的插槽是空的，说明该技能没有处于激活状态，需要进行激活
+ 同时在此技能槽更改时，启停粒子效果

## 自定义计算类 MMC
+ <font style="background-color:#EFF0F0;">UMMC_MaxHealth</font> 返回 80 + 2.5*Vigor + 10*Level
+ <font style="background-color:#EFF0F0;">UMMC_MaxMana</font> 返回 50 + 2.5*Vigor + 5*Level

## 蓝图方法库
<font style="background-color:#EFF0F0;">AuraAbilitySystemBPLibary</font> 继承 自 <font style="background-color:#EFF0F0;">UBlueprintFunctionLibrary</font> 

+ <font style="background-color:#FBF5CB;">GetOverlayWgtController</font> 获取 <font style="background-color:#EFF0F0;">UOverlayWidgetController</font> 实例

## GE
### FAuraGameEffectContext 自定义GE上下文
原有 GEContex 无法满足现有需求（获取伤害是否暴击、格挡...），需要继承 GEContex，添加内容

函数，因 Context 改变，AbilitySystemGlobals 也得重载

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1725090408241-acf5f1b8-6a7d-4ddd-a8b6-a4526547fecc.png)

函数

+ <font style="background-color:#FBF5CB;">NetSerialize</font> 添加新变量的序列化

# MVC架构UI
![UI的MVC](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721635876296-cf0e8f22-91f8-4900-8b3c-621621ad71e4.png)

游戏UI采用MVC架构

## UAuraUserWidget-视图层
是项目中所有Wiget的基类

WidgetController 是其控制层

有设置Controller的函数 <font style="color:#ED740C;background-color:#EFF0F0;">SetWidgetController</font> ，并且在设置完成之后有函数事件 <font style="color:#ED740C;background-color:#EFF0F0;">OnWidgetControllerSetEnd</font>

### WBP_Globe_ProgressBar—玩家状态控件
编写如下父类控件，据此衍生出不同属性控件

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721659054035-8d538e70-c13f-48f5-9dd2-1cd1a161d51b.png)![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721659076379-9e8c277c-d4f9-49f0-a82c-95a1ffb15cc4.png)

+ 为了使其子类能够任意设置大小，因此采用**<font style="background-color:#D8DAD9;">SizeBox</font>**作为底层，然后在其下套上显示区（OverLap）
+ **<font style="background-color:#D8DAD9;">Image_Background</font>** 是UI的背景图片，这里就是一个金色的圆环，设置笔刷图像，然后**绘制为图像**
+ **<font style="background-color:#D8DAD9;">ProgressBar_Globe</font>**是百分比滑条，设置为圆形，从下到上填充；该滑条不需要背景，因此在样式中将背景图的着色alpha设置为0；让滑条范围在环内，设置边距为10；
+ **<font style="background-color:#D8DAD9;">Image_Glass</font>** 为了让整个控件存在玻璃反光效果，设置笔刷就行
+ <font style="background-color:#E7E9E8;">ProgressBar_Ghost</font> 影子百分比滑条，平滑过度向目标百分比值，该滑条为背景，营造游戏UI中差值缓慢消失的效果

以上大部分内容为变量，可在子类更改

### WBP_EffectMessage
该控件为拾取道具时的播报，由Icon 和播报信息组成，并且添加了蹩脚的动画



1. 拾取道具 ->
2. 应用GE (GE设置标签) -> 
3. 绑定对自身应用GE 时广播的代理(  <font style="background-color:#E7E9E8;">OnGameplayEffectAppliedDelegateToSelf</font> ) -> 
4. <font style="background-color:#E7E9E8;">EffectAssetTagsDel</font> 广播此时Tag ->
5. 如果是相关Tag 则进行 信息播报

### WBP_BtnBase
该项目的按钮大致一个样，因此做个基类按钮，并以此为基础派生宽按钮

### WBP_Overlay
将整个游戏窗口作为UI区域设置显示

+ 红蓝条的常驻显示 <font style="background-color:#EFF0F0;">WBP_Globe_ProgressBar</font> 
+ 拾取道具时添加道具拾取信息 <font style="background-color:#EFF0F0;">WBP_EffectMessage</font> 

### AuraHUD
玩家的HUD类

+ <font style="background-color:#E7E9E8;">UAuraUserWidget</font> 类选择成员 <font style="background-color:#D8DAD9;">OverlayWidgetClass</font> ，HUD将此类创建后显示输出到屏幕
+ <font style="background-color:#D8DAD9;">UOverlayWidgetController</font> 类选择器，以此创建选择类型的 单例 作为视图与模型的控制层
+ <font style="color:#ED740C;background-color:#EFF0F0;">InitOverlay</font><font style="color:#F8B881;background-color:#EFF0F0;"> </font> 函数初始化控制层实例，将widget的控制层设置为初始化的实例，并且将其输出到屏幕，调用时机为Actor初始化GAS相关组件完成之后 <font style="color:#ED740C;background-color:#EFF0F0;">AAuraCharacter::InitAbilityActorInfo()</font>

### 属性菜单 attribute menu
![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722521687884-bf3ed417-4e9c-4e0d-a507-f732f718d867.png)

![图2 MVC属性菜单](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722617212849-f1fae7c9-379c-4eba-8dc0-982646b447ee.png)

每个属性一个代理，然后通过代理广播属性的方式，来进行UI与数据的交互也还行，但是不方便维护，因为每增添一个属性，就要写更多的代码。

因此，采用一个通用代理和结构体，进行通用性广播

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1722617953989-67d073aa-d222-450c-8525-62d50372801a.png)



**<font style="background-color:#E7E9E8;">UAttributeInfo</font>**** 继承自 ****<font style="background-color:#E7E9E8;">UDataAsset</font>**** 作为信息表管理**

+ <font style="background-color:#E7E9E8;">FAuraAttributeInfo</font> 装载Attribute相关的数据信息
+ <font style="background-color:#FBF5CB;">FindAttributeInfoForTag</font> 通过Tag 查询对应的 <font style="background-color:#E7E9E8;">FAuraAttributeInfo</font> 
+ 创建 DataAsset 采用 <font style="background-color:#E7E9E8;">AttributeInfo</font> 类型 配置相关信息 

## UAuraWidgetController-控制层
需要和玩家控制器、GAS、PlayerState、属性集进行交互，因此为了方便，创建了结构体 <font style="background-color:#D8DAD9;">FWidgetControllerParams</font> 储存交互类的地址

项目中**每个** <font style="background-color:#EFF0F0;">UAuraUserWidget</font> 的子类都设置了同一控制层，让控制层分别处理内部显示，并非在总集

<font style="background-color:#EFF0F0;">WBP_Overlay</font> 类下处理

**函数：**

+ 虚函数 <font style="background-color:#EFF0F0;">BroadcastInitialValues</font> 
+ 虚函数 <font style="background-color:#E7E9E8;">BindCallbackToDependencies </font> 

### UOverlayWidgetController
该类继承 <font style="background-color:#EFF0F0;">UAuraWidgetController</font> 并且使该类为蓝图类，可蓝图使用（BlueprintType,Blueprintable）

+ 定义代理，表示属性相关的值发送变化

辅助定义

+ <font style="background-color:#EFF0F0;">FUIWidgetRow</font> 继承自 <font style="background-color:#EFF0F0;">FTableRowBase</font> 让其成员可在表格行进行设置。成员为 Tag、信息、信息控件、信息图标

成员

+ <font style="background-color:#EFF0F0;">MessageWidgetDataTable</font> 表示表格，用以选择 <font style="background-color:#EFF0F0;">FUIWidgetRow</font> 相关的信息的表格 获取相关已配置的数据

函数

+ 重载函数 <font style="background-color:#EFF0F0;">BroadcastInitialValues</font> 使得属性被初始化时，广播代理
+ 重载函数 <font style="background-color:#E7E9E8;">BindCallbackToDependencies </font> 使得GAS的对应属性的代理绑定相应的值改变函数，进行相应代理的广播， 也就是广播转广播。
+ <font style="background-color:#EFF0F0;">EffectAssetTagsDel</font> 代理绑定 lambda 通过Tag查表获取信息,

         - 如果该GE 的标签是 Message 的子标签，则 <font style="background-color:#EFF0F0;">MessageWidgetRowDel</font> 进行信息广播

### UAttributeMenuWgtController
继承 <font style="background-color:#EFF0F0;">UAuraWidgetControlle</font>  主要让属性菜单和属性数值交互

函数

+ 重载函数 <font style="background-color:#EFF0F0;">BroadcastInitialValues</font> 通过循环遍历 <font style="background-color:#EFF0F0;">UAttributeInfo</font> 的 <font style="background-color:#EFF0F0;">AttributeInformation</font> 成员，获取每个标签，并且进行转调 <font style="background-color:#EFF0F0;">BroadcastAttributeInfo</font> 
+ 重载函数 <font style="background-color:#E7E9E8;">BindCallbackToDependencies </font> 使得GAS的对应属性的代理绑定相应的值改变函数，进行相应代理的广播， 也就是广播转广播。
+ <font style="background-color:#EFF0F0;">BroadcastAttributeInfo</font> 通过标签 ，<font style="background-color:#EFF0F0;">UAttributeInfo</font> 中找到其结构体，结构体中获取到属性之后 广播值

### SpellMenuWgtController 技能菜单控制层
调整和升级技能界面的控制器

![技能状态和类型tag](https://cdn.nlark.com/yuque/0/2024/png/36214189/1727349823494-20c202fb-5c0e-4536-9b95-0d4d7033c0c5.png)

**装配区域：**

+ 和主界面技能栏类似，通过输入标签来区分是否是该技能栏需要接管
+ 通过代理更新技能信息

**升级区域:**

+ 技能分状态，未到条件、未解锁、已解锁和已装备四种状态
+ 四种状态采用Tag进行区分,技能界面的技能也根据此来进行显示不同状态
+ 每个技能球对应一个技能Tag，接受到技能广播时，按照Tag进行筛选
+ <font style="background-color:#FBF5CB;">UpdateAbilityStatus</font> 函数会根据等级来匹配技能信息表中对应的技能，将技能添加至GAS中，然后RPC客户端广播技能状态变化。在Character中升级时进行调用

**技能选中：技能选中会导致说明栏、解锁、装备按钮的状态变化**

+ 技能球选中调用代理进行调用(<font style="background-color:#FBF5CB;">SpellGlobeSelected</font>)，根据技能标签查询技能是否在GAS中有效，技能状态标签是否占位来获取技能的标签状态
+ 根据技能点数和技能标签及技能状态标签，决定按钮的启用与否（<font style="background-color:#FBF5CB;">ShouldEnableBtns</font>）
+ 广播 <font style="background-color:#EFF0F0;">SpellGlobeSelectedDel</font> ，界面进行按钮状态更改
+ 打开菜单，技能选择框未变，但是可能因为其他情况导致技能状态改变了(升级)，导致相应的按钮无法及时更新，因此**需要在其他能更新技能状态的地方也广播按钮的改变**
+ 从技能描述的资产管理类获取技能描述信息

**技能装配**

+ 按下技能装配按钮，播放提示框动画，切换技能球按钮得取消
+ 发送选中技能的技能Tag，技能栏的装配Tag
+ 清除技能、选中技能栏 以及 技能之前的装配栏(如果存在) Tag
+ 赋予技能新的装配栏tag（选中的装配栏）,赋予装配栏新的技能信息。广播相关需要更改的信息

**技能升级：**

+ 升级时获取技能Tag，从GAS中根据tag获取Spec和status
+ 解锁改status或者升级该Spec的Level

### 主界面技能栏接受技能相关的UI信息
创建一个资产管理(<font style="background-color:#EFF0F0;">FAuraAbilityInfo</font>)，在里面配表，填入技能需要的相关信息

GAS执行添加技能，使控制器变更技能信息

+ 为角色添加能力时(<font style="background-color:#FBF5CB;">AddCharacterAbilities</font>)，<font style="background-color:#EFF0F0;">UAuraAbilitySystemComponent</font> 的 <font style="background-color:#CEF5F7;">AbilitiesGiveDel </font>代理进行广播，告知 <font style="background-color:#EFF0F0;">UOverlayWidgetController</font> 执行初始化技能信息(<font style="background-color:#FBF5CB;">BroadcastAbilityInfo</font>)
+ <font style="background-color:#EFF0F0;">UOverlayWidgetController</font> 添加代理(<font style="background-color:#EFF0F0;">FForEachAbility</font>)绑定函数(根据技能Tag,获取技能相关UI信息)
+ <font style="background-color:#EFF0F0;">UAuraAbilitySystemComponent</font> 执行函数(<font style="background-color:#FBF5CB;">ForEachAbility</font>)，循环获取有效的能力，执行代理(<font style="background-color:#EFF0F0;">FForEachAbility</font>)进行广播能力。代理在(<font style="background-color:#EFF0F0;">UOverlayWidgetController</font>::<font style="background-color:#FBF5CB;">BroadcastAbilityInfo</font>)中设置为了广播的Lambda表达式，<font style="background-color:#FBF5CB;">ForEachAbility</font> 相当根据能力的Tag查找DA获取能力相关的UI信息，并且进行广播
+ UI界面中的技能球存在输入Tag，当技能信息广播时，判断相关技能是否为对应的输入Tag，如果是，则接受其信息，应用在界面上

# MVVM 架构UI
![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1729255845852-02e194b1-9ce6-4f1f-b7ff-26a40db179a2.png)

**<font style="color:rgb(25, 27, 31);background-color:#EFF0F0;">Model-View-ViewModel</font>**<font style="color:rgb(25, 27, 31);"> 多了个</font>**<font style="color:rgb(25, 27, 31);">ViewModel</font>**<font style="color:rgb(25, 27, 31);">。项目中的菜单相关界面使用到了MVVM架构</font>

<font style="color:rgb(25, 27, 31);">上图MVC的 </font>**<font style="color:rgb(25, 27, 31);background-color:#EFF0F0;">Controller</font>**<font style="color:rgb(25, 27, 31);"> 可能变得冗余复杂，但是MVVM的 </font>**<font style="color:rgb(25, 27, 31);background-color:#EFF0F0;">ViewModel</font>**<font style="color:rgb(25, 27, 31);"> 能对其颗粒度到对应的界面，双箭头也表示双向绑定，</font>**<font style="color:rgb(25, 27, 31);">一头View，一头Modle</font>**<font style="color:rgb(25, 27, 31);">。而且UE有其引入的内容，何乐而不为</font>

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1729259141664-5d139ab5-51a6-44ec-a045-19ab50e97a03.png)

因此，菜单界面采用MVVM架构

**HUD基类：**ALoadScreenHUD

**ViewModel类：**UMVVM_LoadScreen（整个加载界面） ; MVVM_LoadSlot (存档槽界面)。继承UE的 **<font style="background-color:#EFF0F0;">UMVVMViewModelBase</font>**

**Wgt基类：**LoadScreenWgt

虚幻的MVVM方便之处在于**ViewModel**类中的变量可以设置FieldNotify 属性，在UMG中的绑定视图中，直接把该变量和UI中控件的某属性绑定

```cpp
const FString& GetLoadSlotName()const { return LoadSlotName; };

 void SetLoadSlotName(const FString& TargetName)
 {
	 UE_MVVM_SET_PROPERTY_VALUE(LoadSlotName,TargetName);//用MVVM的宏，方便被编辑器相关模块采用
 }

/*
* FieldNotify 启用对属性的变更通知。UE5引入，更轻松地跟踪和响应属性值的变化，尤其是在数据绑定和MVVM模式下使用时。
* FieldNotify的变量 被Setter、Getter修饰，必须存在Set和Get函数
*/
UPROPERTY(EditAnywhere,BlueprintReadWrite,FieldNotify,Setter,Getter,meta=(AllowPrivateAccess="true"),DisplayName="插槽ID")
FString LoadSlotName;//存档槽的名字
```

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1729445396286-5870b6dd-83bb-48ee-9d0f-6350968b54ae.png)

如上图，该Wgt存在**LoadSlotViewModel**，能直接**让UI控件****<font style="background-color:#E7E9E8;">SlotID</font>****的****<font style="background-color:#E7E9E8;">Text</font>****变量绑定到ViewModel中被FieldNotify修饰的成员****<font style="background-color:#E7E9E8;">LoadSlotName</font>**。

# 存档与读取
存档类 **<font style="background-color:#E7E9E8;">ULoadScreenSaveGame </font>**，以此保存数据。

但是项目保存获取的数据存在多次折转。比如存档槽的数据，要和存档界面以及和游戏实例进行交互，这点注意纰漏。

## 存档槽
存档槽的界面控制为**<font style="background-color:#E7E9E8;">UMVVM_LoadSlot</font>** 能够设置读取存档状态，切换存档槽界面显示 **新建存档、读取存档、输入存档名称三种界面**

## 检查点
项目存档采用存档点的方式进行存档，

<font style="background-color:#EFF0F0;">GameMode</font>重写 <font style="background-color:#FBF5CB;">ChoosePlayerStart</font>(打开地图后选择玩家起始点的函数)，每个地图有N个 **<font style="background-color:#EFF0F0;">APlayerStart</font>**<font style="background-color:#EFF0F0;"> </font>，按照其 <font style="background-color:#CEF5F7;">PlayerStartTag</font> 进行存档或加载的**位置标识**

## 玩家信息
因为随着游戏进程的RPG发展养成，原来默认按等级读表设置玩家属性的方案不可行。**当储存过一次游戏之后，用另一套GE设置玩家属性**。

为了方便技能储存，定义了结构体 <font style="background-color:#E7E9E8;">FSavedAbility</font> 辅助存档。在GAS中进行读取时，如果是已装备的被动技能，需要激活技能。

而且由于并未使用 <font style="background-color:#E7E9E8;">ActivatePassiveEffectDel</font> 代理进行激活，因此在<font style="background-color:#E7E9E8;">UPassiveNiagaraComponent</font> 中需要**根据装配状态和GAS的技能已经初始获取来直接激活粒子特效**

## 场景状态
**数据思路：**

 场景中存在各种Actor可能需要保存，因此定义结构体 **<font style="background-color:#EFF0F0;">FSavedActor</font>** 用以标识场景中被保存的Actor的状态，为了方便储存Actor中的内容，采用了字节数组储存Actor序列化后的内容。Actor中想要序列化储存的变量用 **<font style="color:#D22D8D;background-color:#E6DCF9;">SaveGame</font>**<font style="color:#D22D8D;background-color:#E6DCF9;"> </font>进行修饰

一个地图存在多个想要储存的Actor，而且又存在不同的地图，因此定义结构体 **<font style="background-color:#EFF0F0;">FSavedMap</font>** 来标识地图和地图下保存的Actor

加载之后会调用可保存状态Actor(继承 **<font style="background-color:#E7E9E8;">ISaveInterface</font>** )的 <font style="background-color:#FBF5CB;">LoadActor</font> 函数，因此再次根据存档数据设置状态;

**存档流程：**

获取当前存档，通过迭代器 **<font style="background-color:#EFF0F0;">FActorIterator</font>** 获取场景所有Actor( 通过是否继承接口 **<font style="background-color:#EFF0F0;">ISaveInterface</font>**** **判断是否为应该储存的对象，也降低获取场景Actor的消耗 )，进行序列化操作读写储存

于角色 **<font style="background-color:#FBF5CB;">PossessedBy</font>**** **时进行加载地图状态

# 网络同步
服务器向客户端发送相关内容称之为复制，**<font style="color:#DF2A3F;">复制只能单向，不能从客户端发送给服务端</font>**

![网络架构演示](https://cdn.nlark.com/yuque/0/2024/png/36214189/1721482926899-fe7c8797-208b-4805-a21f-9323047cd395.png)

图上红色虚线表示客户端与服务器的分割线，虚线以上就是存在服务器的实例，以服务器的内容为标准，虚线以下是客户端的实例。

+ 如果是服务器存在相同的内容，则表示为从服务器复制的，否则就是客户端独有；同理，也存在服务端独有，不然获取就出问题（客户端获取GameMode基本就是空指针）
+ **服务器上的实例不都会复制给****<font style="color:#DF2A3F;">每个</font>****客户端的**，比如**<font style="color:#DF2A3F;background-color:#E7E9E8;">PC_X </font>**控制器是每个客户端从服务器**复制自己的那一份**，不向所有客户端广播
+ **<font style="color:#DF2A3F;background-color:#E7E9E8;">PS_X</font>**玩家状态和**<font style="color:#DF2A3F;background-color:#E7E9E8;">P_X</font>**玩家则向每个客户端都复制
+ 由于复制是单向的，因此**<font style="color:#DF2A3F;">变量只能RPC服务端修改之后复制给客户端</font>**

## AAuraEnemy
该类是AI控制的，进行了以下网络设置

+ AbilitySystemComponent组件类的启用网络复制
+ 设置AbilitySystemComponent组件网络模式为 <font style="background-color:#EFF0F0;">Minimal </font>，经验来说，多人模式下AI控制的部分就用这个

## AAuraPlayerState
该类是玩家的状态，进行以下设置

+ AbilitySystemComponent组件类的启用网络复制
+ 设置AbilitySystemComponent组件网络模式为`<font style="color:rgb(31, 35, 40);">Mixed</font>`，经验来说，多人模式的玩家部分用这个模式
+ 将该类的更新频率设置为100

## 点击移动
**UE模板中**

+ 使用 `SimpleMoveToLocation` 如果是一个短按
    - 在多人游戏中无效（仅在服务器上控制的AI可以使用）
+ 使用 `AddMovementInput` 如果输入是按住不放
    - 在多人游戏中有效
    - 需要持续输入（移动方向）

**项目中**

+ 我们必须使用 `AddMovementInput`
+ 每一帧需要一个方向
+ 开启允许客户端导航

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723220049584-35c42c16-1c93-41d7-b9ff-3b756ca55083.png)

## 技能触发时机
![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723381417684-fbd92c89-eb61-4683-a13c-2cbb65b53c66.png)

如果在服务器上**调用激活所需的时间**小于**RPC到达时间**，那么服务器将调用激活，而服务器将**没有任何有效数据**。

另一方面，如果RPC 先到达服务器、那么 RPC 将在服务器上执行，服务器将获得有效数据，然后激活将被调用。

那么，是服务器先调用 activate 还是 RPC 先到达服务器呢？这是**无法确定的**。



![TargetData进行传输](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723381650820-d8de5f0b-7a45-4e53-a715-36883d98442f.png)

如上图，通过targetData传输到服务器，并且广播相应代理

![调用流程](https://cdn.nlark.com/yuque/0/2024/png/36214189/1723381812868-9696f243-f76f-4f48-88eb-fe08544ac757.png)

如上图，将激活能力绑定到接受到数据的代理上，代理通过回调调用能力激活

# 敌人AI
无他，唯行为树熟而

普通敌人采用一个AI行为树，根据不同职业类型执行不同分支

## EQS查询
### 可射击位置
远程攻击的敌人攻击需要找到合适位置，并且和玩家之间没有阻隔物

![](https://cdn.nlark.com/yuque/0/2024/png/36214189/1725361295863-739a258c-6a16-41f3-8810-e39cff6720ee.png)
**UE VERSION:** 5.2
