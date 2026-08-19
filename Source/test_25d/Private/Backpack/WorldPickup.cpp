#include "Backpack/WorldPickup.h"

#include "Net/UnrealNetwork.h"

AWorldPickup::AWorldPickup()
{
	bReplicates = true;
}

void AWorldPickup::SetItemDefinition(UItemDefinition* InItemDefinition)
{
	if (HasAuthority())
	{
		ItemDefinition = InItemDefinition;
	}
}

void AWorldPickup::SetQuantity(int32 InQuantity)
{
	if (HasAuthority())
	{
		Quantity = FMath::Max(0, InQuantity);
	}
}

bool AWorldPickup::ConsumeQuantity(int32 Amount)
{
	if (!HasAuthority() || Amount <= 0 || Amount > Quantity)
	{
		return false;
	}

	Quantity -= Amount;
	if (Quantity == 0)
	{
		Destroy();
	}
	else
	{
		ForceNetUpdate();
	}
	return true;
}

void AWorldPickup::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	DOREPLIFETIME(AWorldPickup, ItemDefinition);
	DOREPLIFETIME(AWorldPickup, Quantity);
}
