"""One-shot source migration: share StoneGolem's proven attack lifecycle, keep its public types."""
from pathlib import Path
import shutil,uuid
r=Path(__file__).resolve().parents[2];src=r/'Source/test_25d'
backup=r/'Saved/GAAuthoring/MonsterWave1'/('shared-extraction-'+uuid.uuid4().hex);backup.mkdir(parents=True)
files=['Public/StoneGolem/StoneGolemCharacter.h','Private/StoneGolem/StoneGolemCharacter.cpp','Public/StoneGolem/StoneGolemAbility.h','Private/StoneGolem/StoneGolemAbility.cpp','Public/StoneGolem/StoneGolemConfig.h']
old={p:(src/p).read_text(encoding='utf8') for p in files}
assert not (src/'Public/Character/TelegraphedEnemyCharacter.h').exists()
for p in files:shutil.copy2(src/p,backup/Path(p).name)
def write(p,s):
 (src/p).parent.mkdir(parents=True,exist_ok=True);(src/p).write_text(s,encoding='utf8')
h=old[files[0]].replace('StoneGolemCharacter.generated.h','TelegraphedEnemyCharacter.generated.h').replace('AStoneGolemCharacter','ATelegraphedEnemyCharacter')
h=h.replace('TObjectPtr<UStoneGolemConfig> MonsterConfig;','TObjectPtr<UMonsterCombatConfig> CombatConfig;\n    virtual UMonsterCombatConfig* GetCombatConfig() const { return CombatConfig; }')
h='\n'.join(l for l in h.splitlines() if 'TObjectPtr<UStaticMeshComponent>' not in l)
h=h.replace('private:\n    void ApplyConfig();','    virtual void ApplyConfig();\nprivate:')
write('Public/Character/TelegraphedEnemyCharacter.h',h+'\n')
c=old[files[1]].replace('StoneGolem/StoneGolemCharacter.h','Character/TelegraphedEnemyCharacter.h').replace('StoneGolem/StoneGolemAbility.h','AbilitySystem/Ability/TelegraphedEnemyAbility.h').replace('AStoneGolemCharacter','ATelegraphedEnemyCharacter').replace('UStoneGolemAttackAbility','UTelegraphedEnemyAbility').replace('UStoneGolemSelectAttack','UTelegraphedSelectAttack')
start=c.index('    Hammer=CreateDefaultSubobject');end=c.index('    Footprint=',start);c=c[:start]+c[end:]
c='\n'.join(l for l in c.splitlines() if 'Hammer->SetStaticMesh' not in l)
c=c.replace('MonsterConfig','GetCombatConfig()')
write('Private/Character/TelegraphedEnemyCharacter.cpp',c+'\n')
write(files[0],'''#pragma once
#include "Character/TelegraphedEnemyCharacter.h"
#include "StoneGolemCharacter.generated.h"
UCLASS()
class TEST_25D_API AStoneGolemCharacter : public ATelegraphedEnemyCharacter
{
    GENERATED_BODY()
public:
    AStoneGolemCharacter();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="StoneGolem") TObjectPtr<UStoneGolemConfig> MonsterConfig;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="StoneGolem") TObjectPtr<UStaticMeshComponent> Hammer;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="StoneGolem") TObjectPtr<UStaticMeshComponent> Shield;
    virtual UMonsterCombatConfig* GetCombatConfig() const override { return MonsterConfig; }
protected:
    virtual void ApplyConfig() override;
};
''')
write(files[1],'''#include "StoneGolem/StoneGolemCharacter.h"
#include "Components/StaticMeshComponent.h"
AStoneGolemCharacter::AStoneGolemCharacter()
{
    Hammer=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StoneHammer"));
    Shield=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StoneShield"));
    Hammer->SetupAttachment(GetMesh(),TEXT("weapon_rSocket"));
    Shield->SetupAttachment(GetMesh(),TEXT("weapon_lSocket"));
    Hammer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Shield->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AStoneGolemCharacter::ApplyConfig()
{
    Super::ApplyConfig();
    if(MonsterConfig) { Hammer->SetStaticMesh(MonsterConfig->Hammer); Shield->SetStaticMesh(MonsterConfig->Shield); }
}
''')
cfg=old[files[4]];start=cfg.index('UCLASS(BlueprintType)\nclass TEST_25D_API UStoneGolemConfig');end=cfg.index('// One point policy',start)
block=cfg[start:end].replace('UStoneGolemConfig','UMonsterCombatConfig')
block='\n'.join(l for l in block.splitlines() if 'TObjectPtr<UStaticMesh>' not in l)
block+='''
UCLASS(BlueprintType)
class TEST_25D_API UStoneGolemConfig : public UMonsterCombatConfig
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Model") TObjectPtr<UStaticMesh> Hammer;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Model") TObjectPtr<UStaticMesh> Shield;
};

'''
write(files[4],cfg[:start]+block+cfg[end:])
ah=old[files[2]];split=ah.index('UCLASS() class TEST_25D_API UStoneGolemHeavyHammer')
base=ah[:split].replace('StoneGolemAbility.generated.h','TelegraphedEnemyAbility.generated.h').replace('AStoneGolemCharacter','ATelegraphedEnemyCharacter').replace('UStoneGolemAttackAbility','UTelegraphedEnemyAbility').replace('UCLASS(Abstract)','UCLASS()')
base=base.replace('    FGameplayTag CooldownIdentity;','    UPROPERTY(EditDefaultsOnly, Category="Combat") FGameplayTag CooldownIdentity;')
selector=ah[ah.index('// Existing behavior-tree'):].replace('UStoneGolemSelectAttack','UTelegraphedSelectAttack')
write('Public/AbilitySystem/Ability/TelegraphedEnemyAbility.h',base+selector)
sub=ah[split:ah.index('// Existing behavior-tree')]
write(files[2],'''#pragma once
#include "AbilitySystem/Ability/TelegraphedEnemyAbility.h"
#include "StoneGolemAbility.generated.h"
UCLASS(Abstract)
class TEST_25D_API UStoneGolemAttackAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() };
'''+sub+'''UCLASS()
class TEST_25D_API UStoneGolemSelectAttack : public UTelegraphedSelectAttack
{ GENERATED_BODY() };
''')
ac=old[files[3]]
constructors=[l for l in ac.splitlines() if l.startswith('UStoneGolemHeavyHammer::') or l.startswith('UStoneGolemQuake::') or l.startswith('UStoneGolemShieldBash::')]
tags=[l for l in ac.splitlines() if l.startswith('UE_DEFINE_GAMEPLAY_TAG_STATIC') and 'TAG_SGSelect' not in l]
write(files[3],'#include "StoneGolem/StoneGolemAbility.h"\n#include "NativeGameplayTags.h"\n'+'\n'.join(tags+constructors)+'\n')
ac='\n'.join(l for l in ac.splitlines() if l not in constructors and l not in tags)
ac=ac.replace('StoneGolem/StoneGolemAbility.h','AbilitySystem/Ability/TelegraphedEnemyAbility.h').replace('StoneGolem/StoneGolemCharacter.h','Character/TelegraphedEnemyCharacter.h').replace('AStoneGolemCharacter','ATelegraphedEnemyCharacter').replace('UStoneGolemAttackAbility','UTelegraphedEnemyAbility').replace('UStoneGolemSelectAttack','UTelegraphedSelectAttack').replace('->MonsterConfig','->GetCombatConfig()').replace('Abilities.Attack.StoneGolem','Abilities.Attack.ConfiguredMonster')
write('Private/AbilitySystem/Ability/TelegraphedEnemyAbility.cpp',ac+'\n')
print(backup)
