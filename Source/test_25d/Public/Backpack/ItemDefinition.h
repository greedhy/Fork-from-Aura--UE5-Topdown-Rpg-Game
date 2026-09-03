#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "ItemDefinition.generated.h"

class UGameplayEffect;
class UStaticMesh;
class UTexture2D;
class AActor;

UENUM(BlueprintType)
enum class EPickupMode : uint8
{
	Auto,
	Interact
};

USTRUCT(BlueprintType)
struct FBackpackItemDefEntry
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Item")
	FPrimaryAssetId ItemDefinitionId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Item")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Item")
	TObjectPtr<UTexture2D> Icon;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "World")
	TObjectPtr<UStaticMesh> WorldMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "World")
	TSubclassOf<AActor> PickupActorClass;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pickup")
	EPickupMode PickupMode = EPickupMode::Interact;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stacking")
	bool bStackable = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stacking", meta = (ClampMin = "1"))
	int32 MaxStack = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Use")
	bool bUsable = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Use")
	TSubclassOf<UGameplayEffect> UseEffect;
};

UCLASS(BlueprintType)
class TEST_25D_API UBackpackItemDefinitions : public UDataAsset
{
	GENERATED_BODY()

public:
	const FBackpackItemDefEntry* FindDefinition(const FPrimaryAssetId& ItemDefinitionId) const;
	const FBackpackItemDefEntry* FindDefinitionForPickupActor(const UClass* PickupActorClass) const;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Item")
	TArray<FBackpackItemDefEntry> Items;
};

UCLASS(BlueprintType)
class TEST_25D_API UItemDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Item")
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Item")
	TObjectPtr<UTexture2D> Icon;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Pickup")
	bool bAutoPickup = false;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stacking")
	bool bStackable = true;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stacking", meta = (ClampMin = "1"))
	int32 MaxStack = 1;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Use")
	bool bUsable = false;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Use")
	TSubclassOf<UGameplayEffect> UseEffect;
};
