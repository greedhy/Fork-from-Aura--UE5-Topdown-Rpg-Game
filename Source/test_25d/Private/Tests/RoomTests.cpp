#include "Misc/AutomationTest.h"
#include "Online/RoomSubsystem.h"
#include "Online/RoomLobby.h"
#include "Engine/World.h"
#include "GameFramework/PlayerState.h"
#include "Game/MyGameInstance.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRoomPasswordRules,"test_25d.Rooms.PasswordValidationAndFingerprint",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FRoomPasswordRules::RunTest(const FString&)
{
    TestTrue(TEXT("Generated room password is valid"),URoomSubsystem::IsValidPassword(URoomSubsystem::GeneratePassword()));
    TestTrue(TEXT("Six digits"),URoomSubsystem::IsValidPassword(TEXT("123456")));
    TestTrue(TEXT("Twelve mixed ASCII characters"),URoomSubsystem::IsValidPassword(TEXT("AbCd12345678")));
    for(const FString& Invalid:TArray<FString>{TEXT(""),TEXT("12345"),TEXT("1234567890123"),TEXT("123?45"),TEXT("123 45"),TEXT("123&45"),TEXT("１２３４５６")})
        TestFalse(TEXT("Reject invalid or URL-injecting password"),URoomSubsystem::IsValidPassword(Invalid));
    TestNotEqual(TEXT("Password case is significant"),URoomSubsystem::PasswordFingerprint(TEXT("ABC123")),URoomSubsystem::PasswordFingerprint(TEXT("abc123")));
    TestNotEqual(TEXT("Never advertise the plain password"),URoomSubsystem::PasswordFingerprint(TEXT("123456")),FString(TEXT("123456")));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRoomMatchRules,"test_25d.Rooms.MatchFiltersAndAmbiguousPassword",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FRoomMatchRules::RunTest(const FString&)
{
    auto Make=[](const FString& Password,bool Open=true,int32 Free=1){FOnlineSessionSearchResult R; R.Session.NumOpenPublicConnections=Free; R.Session.SessionSettings.Set(URoomSubsystem::ProtocolKey,FString(TEXT("test25d-lan-v1")),EOnlineDataAdvertisementType::ViaOnlineServiceAndPing); R.Session.SessionSettings.Set(URoomSubsystem::PasswordKey,URoomSubsystem::PasswordFingerprint(Password),EOnlineDataAdvertisementType::ViaOnlineServiceAndPing); R.Session.SessionSettings.Set(URoomSubsystem::OpenKey,Open,EOnlineDataAdvertisementType::ViaOnlineServiceAndPing); return R;};
    const auto Good=Make(TEXT("123456"));
    TestEqual(TEXT("Correct password selects one room"),URoomSubsystem::MatchingRoomIndices({Make(TEXT("654321")),Good},TEXT("123456")).Num(),1);
    TestEqual(TEXT("Full and started rooms are excluded"),URoomSubsystem::MatchingRoomIndices({Make(TEXT("123456"),true,0),Make(TEXT("123456"),false)},TEXT("123456")).Num(),0);
    TestEqual(TEXT("Duplicates remain detectable; never silently choose first"),URoomSubsystem::MatchingRoomIndices({Good,Good},TEXT("123456")).Num(),2);
    FOnlineSessionSearchResult Foreign; TestEqual(TEXT("Ignore unrelated games"),URoomSubsystem::MatchingRoomIndices({Foreign},TEXT("123456")).Num(),0);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRoomHostAuthority,"test_25d.Rooms.OnlyOwnerCanManageLobby",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FRoomHostAuthority::RunTest(const FString&)
{
    UWorld* W=UWorld::CreateWorld(EWorldType::Game,false);
    auto* State=W->SpawnActor<ARoomLobbyGameState>();
    auto* Host=W->SpawnActor<ARoomLobbyController>(); auto* Guest=W->SpawnActor<ARoomLobbyController>();
    Host->PlayerState=W->SpawnActor<APlayerState>(); Guest->PlayerState=W->SpawnActor<APlayerState>();
    State->RoomOwner=Host->PlayerState;
    TestTrue(TEXT("Room owner can manage"),State->CanManage(Host));
    TestFalse(TEXT("Guest cannot manage"),State->CanManage(Guest));
    TestFalse(TEXT("Missing requester cannot manage"),State->CanManage(nullptr));
    State->bStarting=true; TestFalse(TEXT("Cannot change room during travel"),State->CanManage(Host));
    W->DestroyWorld(false); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRoomInvalidSelection,"test_25d.Rooms.InvalidSelectionNeverStartsTravel",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FRoomInvalidSelection::RunTest(const FString&)
{
    auto* Rooms=NewObject<URoomSubsystem>(NewObject<UMyGameInstance>());
    TestFalse(TEXT("No selected save"),Rooms->HasSelection());
    Rooms->StartSinglePlayer(); TestFalse(TEXT("Failure is retryable"),Rooms->IsBusy());
    TestFalse(TEXT("Explains missing selection"),Rooms->LastError.IsEmpty());
    Rooms->JoinRoom(TEXT("bad?pw")); TestFalse(TEXT("Invalid password never starts search"),Rooms->IsBusy());
    TestEqual(TEXT("State remains idle"),Rooms->State,ERoomFlowState::Idle);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRoomReentrancy,"test_25d.Rooms.MemberArrivalPreservesPendingHostOperations",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FRoomReentrancy::RunTest(const FString&)
{
    auto* Rooms=NewObject<URoomSubsystem>(NewObject<UMyGameInstance>());
    Rooms->State=ERoomFlowState::Updating; Rooms->NotifyLobbyReady();
    TestEqual(TEXT("An arriving member cannot cancel password update"),Rooms->State,ERoomFlowState::Updating);
    Rooms->State=ERoomFlowState::Starting; Rooms->NotifyLobbyReady();
    TestEqual(TEXT("An arriving member cannot cancel starting the game"),Rooms->State,ERoomFlowState::Starting);
    Rooms->CreateRoom(); Rooms->JoinRoom(TEXT("123456")); Rooms->StartSinglePlayer();
    TestEqual(TEXT("Repeated menu actions do not replace an active operation"),Rooms->State,ERoomFlowState::Starting);
    Rooms->State=ERoomFlowState::Joining; Rooms->NotifyLobbyReady();
    TestEqual(TEXT("A joining local player transitions to lobby"),Rooms->State,ERoomFlowState::InLobby);
    return true;
}
#endif
