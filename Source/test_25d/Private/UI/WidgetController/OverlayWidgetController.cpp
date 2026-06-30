// Fill out your copyright notice in the Description page of Project Settings.


#include "UI/WidgetController/OverlayWidgetController.h"

#include "MyGameplayTags.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "AbilitySystem/MyAttributeSet.h"
#include"AbilitySystem/Data/AbilityInfo.h"
#include"Player/MyPlayerState.h"
#include "AbilitySystem/Data/LevelUpInfo.h"

void UOverlayWidgetController::BroadcastInitialValues()
{

//转化至UMyAttributeSet，这样就可以调用GetHealth和GetMaxHealth等获得数据了
  
    //如果转化不成功游戏将会崩溃
    //广播初始化值
    OnHealthChanged.Broadcast(GetMyAS()->GetHealth());
    OnMaxHealthChanged.Broadcast(GetMyAS()->GetMaxHealth());
    OnManaChanged.Broadcast(GetMyAS()->GetMana());
    OnMaxManaChanged.Broadcast(GetMyAS()    ->GetMaxMana());


}


void UOverlayWidgetController::BindCallbacksToDependencies()
{
	GetMyPS()->OnXPChangedDelegate.AddUObject(this, &UOverlayWidgetController::OnXPChanged);
    GetMyPS()->OnLevelChangedDelegate.AddLambda(
        [this](int32 NewLevel, bool bLevelUp)
        {
            OnPlayerLevelChangedDelegate.Broadcast(NewLevel, bLevelUp);
        }
    );



    ASC->GetGameplayAttributeValueChangeDelegate(GetMyAS()->GetHealthAttribute()).AddLambda(
        [this](const FOnAttributeChangeData& Data) {
            OnHealthChanged.Broadcast(Data.NewValue);
        }

    );
    ASC->GetGameplayAttributeValueChangeDelegate(GetMyAS()->GetMaxHealthAttribute()).AddLambda(
        [this](const FOnAttributeChangeData& Data) {
            OnMaxHealthChanged.Broadcast(Data.NewValue);
        }

    );
    ASC->GetGameplayAttributeValueChangeDelegate(GetMyAS()->GetManaAttribute()).AddLambda(
        [this](const FOnAttributeChangeData& Data) {
            OnManaChanged.Broadcast(Data.NewValue);
        }

    );
    ASC->GetGameplayAttributeValueChangeDelegate(GetMyAS()->GetMaxManaAttribute()).AddLambda(
        [this](const FOnAttributeChangeData& Data) {
            OnMaxManaChanged.Broadcast(Data.NewValue);
        }

    );
    if (GetMyASC())
    {
        GetMyASC()->AbilityEquipped.AddUObject(this, &UOverlayWidgetController::OnAbilityEquipped);
        if (GetMyASC()->bStartupAbilityGiven)
        {
            BroadcastAbilityInfo();
        }
        else
        {
            GetMyASC()->AbilitiesGiven.AddUObject(this, &UOverlayWidgetController::BroadcastAbilityInfo);
        }
            GetMyASC()->EffectAssectTags.AddLambda(
                [this](const FGameplayTagContainer& TagContainer)
                {
                    for (const FGameplayTag& Tag : TagContainer)
                    {
                        // message标签开头的Tag会触发MessageWidgetRowDelegate，
                        // MessageWidgetRowDelegate会将对应的DataTable行广播出去，
                        // UI层根据这个行数据生成对应的Widget


                        FGameplayTag MessageTag = FGameplayTag::RequestGameplayTag(FName("Message"));
                        if (Tag.MatchesTag(MessageTag)) {

                            const FUIWidgetRow* Row = GetDataTableRowByTag<FUIWidgetRow>(MessageWidgetDataTable, Tag);
                            MessageWidgetRowDelegate.Broadcast(*Row);
                        }
                    }
				}
            );
}
}


void UOverlayWidgetController::OnXPChanged(int32 NewXP)
{
    ULevelUpInfo* LevelUpInfo = GetMyPS()->LevelUpInfo;

	int32 Level=LevelUpInfo->FindLevelForXP(NewXP);


    const int32 MaxLevel = LevelUpInfo->LevelUpInformation.Num();

    if (Level <= MaxLevel && Level > 0)
    {
        const int32 LevelUpRequirement = LevelUpInfo->LevelUpInformation[Level].LevelUpRequirement;
        const int32 PreviousLevelUpRequirement = LevelUpInfo->LevelUpInformation[Level - 1].LevelUpRequirement;

        const int32 DeltaLevelRequirement = LevelUpRequirement - PreviousLevelUpRequirement;
        const int32 XPForThisLevel = NewXP - PreviousLevelUpRequirement;

        const float XPBarPercent = static_cast<float>(XPForThisLevel) / static_cast<float>(DeltaLevelRequirement);

        OnXPPercentChangedDelegate.Broadcast(XPBarPercent);
    }
}

void UOverlayWidgetController::OnAbilityEquipped(const FGameplayTag& AbilityTag, const FGameplayTag& Status, const FGameplayTag& Slot, const FGameplayTag& PreviousSlot) const
{
    const FMyGameplayTags& GameplayTags = FMyGameplayTags::Get();

    FMyAbilityInfo LastSlotInfo;
    LastSlotInfo.StatusTag = GameplayTags.Abilities_Status_Unlocked;
    LastSlotInfo.InputTag = PreviousSlot;
    LastSlotInfo.AbilityTag = GameplayTags.Abilities_None;
    // Broadcast empty info if PreviousSlot is a valid slot. Only if equipping an already-equipped spell
    AbilityInfoDelegate.Broadcast(LastSlotInfo);

    FMyAbilityInfo Info = AbilityInfo->FindAbilityInfoForTag(AbilityTag);
    Info.StatusTag = Status;
    Info.InputTag = Slot;
    AbilityInfoDelegate.Broadcast(Info);
}
