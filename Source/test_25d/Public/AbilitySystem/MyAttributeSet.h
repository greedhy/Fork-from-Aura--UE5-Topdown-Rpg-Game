// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "GameplayEffectExtension.h"
#include "Containers/Map.h"
#include "MyAttributeSet.generated.h"



#define ATTRIBUTE_ACCESSORS(ClassName, PropertyName) \
	GAMEPLAYATTRIBUTE_PROPERTY_GETTER(ClassName, PropertyName) \
	GAMEPLAYATTRIBUTE_VALUE_GETTER(PropertyName) \
	GAMEPLAYATTRIBUTE_VALUE_SETTER(PropertyName) \
	GAMEPLAYATTRIBUTE_VALUE_INITTER(PropertyName)

USTRUCT()
struct FEffectProperties
{
	GENERATED_BODY()
	FEffectProperties() {}
	FGameplayEffectContextHandle EffectContextHandle;
	//Source 代表这个Effect是从哪个Actor释放的,Target代表自身(拥有该AttributeSet的角色)

	UPROPERTY()
	UAbilitySystemComponent* SourceASC = nullptr;
	UPROPERTY()
	AActor* SourceAvatarActor = nullptr;
	UPROPERTY()
	AController* SourceController = nullptr;
	UPROPERTY()
	ACharacter* SourceCharacter = nullptr;
	UPROPERTY()
	UAbilitySystemComponent* TargetASC = nullptr;
	UPROPERTY()
	AActor* TargetAvatarActor = nullptr;
	UPROPERTY()
	AController* TargetController = nullptr;
	UPROPERTY()
	ACharacter* TargetCharacter = nullptr;
};


template<class T>
using TStaticFunPtr = typename TBaseStaticDelegateInstance<T, FDefaultDelegateUserPolicy>::FFuncPtr;


/**
 * 
 */
UCLASS()
class TEST_25D_API UMyAttributeSet : public UAttributeSet
{
	GENERATED_BODY()
public:
	UMyAttributeSet();
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
	virtual void PostGameplayEffectExecute	(const FGameplayEffectModCallbackData& Data) override;

	void SetEffectProperties(const FGameplayEffectModCallbackData& Data, FEffectProperties& Props) const;

	virtual void PostAttributeChange(const FGameplayAttribute& Attribute, float OldValue, float NewValue) override ;




	TMap<FGameplayTag, TStaticFunPtr<FGameplayAttribute()>> TagsToAttributes;

	//meta attributes



	UPROPERTY(BlueprintReadOnly, Category = "Meta Attributes")
	FGameplayAttributeData IncomingDamage; //处理传入的伤害
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, IncomingDamage);

	UPROPERTY(BlueprintReadOnly, Category = "Meta Attributes")
	FGameplayAttributeData IncomingXP; //处理传入的经验值
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, IncomingXP);
	// damage attributes
		/*
	 * 属性伤害抗性
	*/

	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_FireResistance, Category = "Resistance Attributes")
	FGameplayAttributeData FireResistance; // 火属性抗性
	UFUNCTION()
	void OnRep_FireResistance(const FGameplayAttributeData& OldFireResistance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, FireResistance);

	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_ThunderResistance, Category = "Resistance Attributes")
	FGameplayAttributeData ThunderResistance; // 雷属性抗性
	UFUNCTION()
	void OnRep_ThunderResistance(const FGameplayAttributeData& OldThunderResistance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, ThunderResistance);

	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_WaterResistance, Category = "Resistance Attributes")
	FGameplayAttributeData WaterResistance; // 雷属性抗性
	UFUNCTION()
	void OnRep_WaterResistance(const FGameplayAttributeData& OldWaterResistance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, WaterResistance);

	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_MagicResistance, Category = "Resistance Attributes")
	FGameplayAttributeData MagicResistance; // 魔法抗性
	UFUNCTION()
	void OnRep_MagicResistance(const FGameplayAttributeData& OldMagicResistance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, MagicResistance);

	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_PhysicsResistance, Category = "Resistance Attributes")
	FGameplayAttributeData PhysicsResistance; // 物理抗性
	UFUNCTION()
	void OnRep_PhysicsResistance(const FGameplayAttributeData& OldPhysicsResistance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, PhysicsResistance);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_PureResistance, Category = "Resistance Attributes")
	FGameplayAttributeData PureResistance; // 物理抗性
	UFUNCTION()
	void OnRep_PureResistance(const FGameplayAttributeData& OldPureResistance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, PureResistance);


	// primary attributes
	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Strength, Category = "Primary Attributes")
	FGameplayAttributeData Strength;
	UFUNCTION()
	void OnRep_Strength(const FGameplayAttributeData& OldStrength) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Strength);




	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Intelligence, Category = "Primary Attributes")
	FGameplayAttributeData Intelligence;
	UFUNCTION()
	void OnRep_Intelligence(const FGameplayAttributeData& OldIntelligence) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Intelligence);




	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Resilience, Category = "Primary Attributes")
	FGameplayAttributeData Resilience;
	UFUNCTION()
	void OnRep_Resilience(const FGameplayAttributeData& OldResilience) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Resilience);




	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Vigor, Category = "Primary Attributes")
	FGameplayAttributeData Vigor;
	UFUNCTION()
	void OnRep_Vigor(const FGameplayAttributeData& OldVigor) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Vigor);

	//secondary attributes
	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Armor, Category = "Secondary Attributes")
	FGameplayAttributeData Armor;
	UFUNCTION()
	void OnRep_Armor(const FGameplayAttributeData& OldArmor) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Armor);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_ArmorPene, Category = "Secondary Attributes")
	FGameplayAttributeData ArmorPene;
	UFUNCTION()
	void OnRep_ArmorPene(const FGameplayAttributeData& OldArmorPene) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, ArmorPene);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_BlockChance, Category = "Secondary Attributes")
	FGameplayAttributeData BlockChance;
	UFUNCTION()
	void OnRep_BlockChance(const FGameplayAttributeData& OldBlockChance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, BlockChance);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_CriticalHitChance, Category = "Secondary Attributes")
	FGameplayAttributeData CriticalHitChance;
	UFUNCTION()
	void OnRep_CriticalHitChance(const FGameplayAttributeData& OldCriticalHitChance) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, CriticalHitChance);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_CriticalHitDamage, Category = "Secondary Attributes")
	FGameplayAttributeData CriticalHitDamage;
	UFUNCTION()
	void OnRep_CriticalHitDamage(const FGameplayAttributeData& OldCriticalHitDamage) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, CriticalHitDamage);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_CriticalHitResistence, Category = "Secondary Attributes")
	FGameplayAttributeData CriticalHitResistence;
	UFUNCTION()
	void OnRep_CriticalHitResistence(const FGameplayAttributeData& OldCriticalHitResistence) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, CriticalHitResistence);

	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_HealthRegeneration, Category = "Secondary Attributes")
	FGameplayAttributeData HealthRegeneration;
	UFUNCTION()
	void OnRep_HealthRegeneration(const FGameplayAttributeData& OldHealthRegeneration) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, HealthRegeneration);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_ManaRegeneration, Category = "Secondary Attributes")
	FGameplayAttributeData ManaRegeneration;
	UFUNCTION()
	void OnRep_ManaRegeneration(const FGameplayAttributeData& OldManaRegeneration) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, ManaRegeneration);

	// vital attributes
	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Health, Category = "Vital Attributes")
	FGameplayAttributeData Health;
	UFUNCTION()
	void OnRep_Health(const FGameplayAttributeData& OldHealth) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Health);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_MaxHealth, Category = "Secondary Attributes")
	FGameplayAttributeData MaxHealth;
	UFUNCTION()
	void OnRep_MaxHealth(const FGameplayAttributeData& OldMaxHealth) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, MaxHealth);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Mana, Category = "Vital Attributes")
	FGameplayAttributeData Mana;
	UFUNCTION()
	void OnRep_Mana(const FGameplayAttributeData& OldMana) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, Mana);


	UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_MaxMana, Category = "Secondary Attributes")
	FGameplayAttributeData MaxMana;
	UFUNCTION()
	void OnRep_MaxMana(const FGameplayAttributeData& OldMaxMana) const;
	ATTRIBUTE_ACCESSORS(UMyAttributeSet, MaxMana);

private:
	void ShowFloatingText(const FEffectProperties& Props,float Damage,bool bBlockHit,bool bCriticalHit) const;

	void HandleIncomingDamage(const FEffectProperties& Props);
	void HandleIncomingXP(const FEffectProperties& Props);
	void Debuff(const FEffectProperties& Props);
	void SendXPEvent(const FEffectProperties& Props);

	bool bTopOffHealth = false;
	bool bTopOffMana = false;
};
