#include "AbilitySystem/Ability/ShamanEnemyAbility.h"
#include "Character/ShamanEnemyCharacter.h"
#include "NativeGameplayTags.h"
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShCast,"Abilities.Shaman.Cast");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShBurst,"Abilities.Shaman.Burst");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShSummon,"Abilities.Shaman.Summon");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShCastCD,"Cooldown.Shaman.Cast");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShBurstCD,"Cooldown.Shaman.Burst");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShSummonCD,"Cooldown.Shaman.Summon");
UShamanCastAbility::UShamanCastAbility(){SetAssetTags(FGameplayTagContainer(TAG_ShCast));CooldownIdentity=TAG_ShCastCD;}
UShamanBurstAbility::UShamanBurstAbility(){SetAssetTags(FGameplayTagContainer(TAG_ShBurst));CooldownIdentity=TAG_ShBurstCD;}
UShamanSummonAbility::UShamanSummonAbility(){SetAssetTags(FGameplayTagContainer(TAG_ShSummon));CooldownIdentity=TAG_ShSummonCD;}
bool UShamanSummonAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    const FGameplayTagContainer* Source,const FGameplayTagContainer* Target,FGameplayTagContainer* Relevant) const
{
    const auto* Actor=Info?Cast<AShamanEnemyCharacter>(Info->AvatarActor.Get()):nullptr;
    const auto* Config=Cast<UShamanSummonConfig>(AttackConfig);
    return Actor && Config && Config->ValidateSummon() && Actor->GetOwnedMinionCount()<Config->MaxAlive &&
        Super::CanActivateAbility(Handle,Info,Source,Target,Relevant);
}
void UShamanSummonAbility::ResolveHit()
{
    auto* Actor=Cast<AShamanEnemyCharacter>(Golem.Get());
    if(!Actor || !Actor->IsAttackCurrent(Serial,Lease)) return;
    Actor->ShowImpact(Serial,Center);
    Actor->Summon(SummonSnapshot,Lease);
}
void UShamanSummonAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event)
{
    const auto* Config=Cast<UShamanSummonConfig>(AttackConfig);
    SummonSnapshot=Config?DuplicateObject<UShamanSummonConfig>(Config,this):nullptr;
    Super::ActivateAbility(Handle,Info,Activation,Event);
}
