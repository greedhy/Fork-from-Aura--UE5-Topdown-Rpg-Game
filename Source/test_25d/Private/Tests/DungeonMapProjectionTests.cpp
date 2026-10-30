#include "Misc/AutomationTest.h"
#include "Roguelike/DungeonMapProjection.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDungeonMapProjectionTest,"test_25d.Roguelike.UI.MapCameraOrientation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDungeonMapProjectionTest::RunTest(const FString&)
{
    TestTrue(TEXT("Default camera forward is map up"),DungeonMapProjection::Project(FVector2D(1,0),0).Equals(FVector2D(0,-1)));
    TestTrue(TEXT("Default camera right is map right"),DungeonMapProjection::Project(FVector2D(0,1),0).Equals(FVector2D(1,0)));
    for(float Yaw:{0.f,90.f,180.f,-90.f,37.f})
    {
        const FRotationMatrix Camera(FRotator(-35,Yaw,0));
        const FVector Right=Camera.GetUnitAxis(EAxis::Y);
        const FVector Forward=FRotator(0,Yaw,0).Vector();
        TestTrue(TEXT("Camera-right projects right"),DungeonMapProjection::Project(FVector2D(Right.X,Right.Y),Yaw).Equals(FVector2D(1,0),.0001));
        TestTrue(TEXT("Camera-forward projects up"),DungeonMapProjection::Project(FVector2D(Forward.X,Forward.Y),Yaw).Equals(FVector2D(0,-1),.0001));
        const FVector2D A(-3,2),B(4,-1);
        TestTrue(TEXT("Offset independent of map origin"),(DungeonMapProjection::Project(B,Yaw)-DungeonMapProjection::Project(A,Yaw)).Equals(DungeonMapProjection::Project(B-A,Yaw),.0001));
    }
    return true;
}
#endif
