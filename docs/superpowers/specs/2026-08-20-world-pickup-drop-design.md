# World Pickup and Drop Design

## Goal

Extend the server-authoritative backpack with data-asset-driven world pickup and whole-stack dropping. Native world items may be collected automatically or with an interaction key. Any item dropped from a player's backpack becomes an immediately public, interaction-only world item.

## Scope

- Add a pickup-mode setting to each item definition asset.
- Support automatic world pickup and `E`-key interaction pickup.
- Allow a player to drop the complete stack in one backpack slot.
- Preserve the existing server-authoritative inventory, stable slots, replication, and partial-pickup rules.

Quantity selection, per-player pickup reservations, timed pickup ownership, and item expiration are out of scope.

## Item Pickup Configuration

`UItemDefinition` replaces `bAutoPickup` with `EPickupMode`:

```cpp
UENUM(BlueprintType)
enum class EPickupMode : uint8
{
    Auto,
    Interact
};
```

Each `UItemDefinition` primary data asset stores its default pickup mode. This setting applies when a world pickup is authored or otherwise spawned as a normal world item. It does not change at runtime.

## World Pickup Runtime State

`AWorldPickup` remains the single replicated actor for every world item. Alongside its item definition and quantity, it replicates an effective pickup mode.

Normal world spawns initialize the effective mode from the definition asset. A dropped item explicitly overrides that effective mode to `Interact`, regardless of the definition default. The override is actor state only: it never modifies the source item asset.

The actor exposes a collision/interaction range, its effective mode, item display data, and replicated quantity for presentation. It does not own or mutate client inventory state.

## Pickup Flows

### Automatic pickup

On the server, a Pawn entering an `AWorldPickup` interaction range attempts collection only when the actor's effective mode is `Auto`. The server resolves the Pawn's `AMyPlayerState` and its backpack component, then uses the existing authoritative add/pickup rules.

If capacity accepts only part of the stack, the pickup actor retains the remaining quantity. If nothing can be accepted, the actor remains in the world. A successful full pickup destroys the actor through its existing quantity-consumption path.

### Interaction pickup

For an effective mode of `Interact`, a nearby local player sees the item name and an `E` interaction prompt. Pressing `E` invokes the existing intent-only `AMyPlayerController::ServerRequestPickup(AActor*)` request.

The server validates that the target is a live authoritative `AWorldPickup`, the player controls a valid Pawn, the Pawn is within the configured range, and the backpack can accept quantity. It then applies the same partial-pickup rules as automatic collection. Failed validation leaves both the world item and backpack unchanged.

## Drop Flow

The backpack slot UI exposes a drop action. It passes only the stable slot index to a new `ServerRequestDrop(int32 SlotIndex)` RPC on `AMyPlayerController`.

The server validates the requesting controller, PlayerState backpack, controlled Pawn, and a non-empty valid slot. It creates an `AWorldPickup` in front of the Pawn with the complete stack from that slot, initializes its effective mode to `Interact`, and verifies spawn success before removing the stack from the backpack. The spawned item is immediately public: every player may use `E` to collect it without an owner-only protection period.

The drop request has no quantity argument. It always removes the complete stack in the selected slot.

## Authority and UI Boundaries

```
Item definition asset -> default pickup mode
                           |
World pickup effective mode -> auto overlap on server
                            -> E request from local player -> ServerRequestPickup
Backpack UI -> ServerRequestDrop(slot index) -> server spawn -> remove complete stack
```

Clients present prompts and submit intent only. The server alone changes world pickup quantities, spawns drops, and mutates backpack slots. Pickups and drops continue to replicate through the existing `AWorldPickup` and backpack Fast Array state.

## Failure Handling

- Invalid slot, empty slot, invalid item definition, missing Pawn, invalid target, or out-of-range request: reject without mutation.
- Full or partially full backpack: accept only the quantity permitted by the inventory model; retain the remainder in the world.
- Failed drop spawn: retain the original complete stack in the backpack.
- A pickup already consumed by another player: reject the later request without modifying inventory.

## Verification

Automation tests cover:

1. Item definitions expose both pickup modes.
2. Native `Auto` pickup collects on a valid server-side range overlap.
3. `Interact` pickup does not collect without a valid `E` request.
4. Partial pickup retains the correct world remainder.
5. Dropping removes a complete stack only after a world pickup successfully spawns.
6. A dropped `Auto`-configured item has effective mode `Interact` and is not auto-collected.
7. Any other player can immediately interact-pick up a dropped item.
8. Invalid, empty, forged, stale, and out-of-range pickup/drop requests make no mutation.

Manual two-player PIE verification covers a player dropping an auto-configured item, neither player automatically collecting it, then the other player immediately collecting it with `E`.
