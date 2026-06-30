// Fill out your copyright notice in the Description page of Project Settings.


#include "MyAssetManager.h"
#include "MyGameplayTags.h"
UMyAssetManager& UMyAssetManager::Get()
{
	// TODO: 在此处插入 return 语句

	check(GEngine);
	UMyAssetManager* MyAssetManager = Cast<UMyAssetManager>(GEngine->AssetManager);
	return *MyAssetManager;
}
void UMyAssetManager::StartInitialLoading()
{
Super::StartInitialLoading();
// 这里可以添加一些在游戏开始时需要加载的资源
FMyGameplayTags::InitializeNativeGameplayTags();
}