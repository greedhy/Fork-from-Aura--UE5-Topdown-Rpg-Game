# Networked Backpack Design

## Goal

Make the backpack authoritative on the server, persistent through Pawn death, map travel, and reconnect, and safe for both listen servers and dedicated servers. A second simultaneous login for the same player identity is rejected.

## Ownership and runtime roles

`APlayerState` owns `UBackpackComponent` on the server. It is the one authoritative runtime inventory for a player during a match. `APlayerCharacter` owns no inventory state; it is the currently possessed body and the target for gameplay effects. `PlayerController` owns client-to-server request RPCs. `GameInstance` has no backpack state and remains local, non-replicated application state only.

```
Client UI -> PlayerController Server RPC -> PlayerState BackpackComponent
                                         -> replicated slot state -> Client UI
                                         -> current PlayerCharacter ASC
```

The current GameInstance-owned backpack implementation is transitional and must be removed during implementation, so only the PlayerState instance remains.

## Replicated data model

The inventory model uses stable indexed slots. Replicate the slot collection, capacity, and inventory revision through an `FFastArraySerializer` representation owned by `UBackpackComponent`; do not replicate ViewModels or UI objects. Each slot contains an item definition primary asset ID and quantity. Item definitions are static assets available to client and server.

The server emits inventory change notifications after a successful mutation. The owning client projects replicated state into MVVM view models. UI never mutates a model directly.

## Requests and validation

The client sends intent only. `PlayerController` provides reliable `Server` RPCs for pickup, use, and swap. The server validates the request against its PlayerState model, then mutates and replicates the result.

- Pickup validates the world pickup actor, distance, ownership, item definition, and capacity. Partial pickup retains the remainder in the world.
- Use validates slot index, quantity, item usability, cooldown, the currently possessed Pawn, and that Pawn's Ability System Component. The server applies the configured gameplay effect to the Pawn's ASC before decrementing the slot. A failed effect application does not consume an item.
- Swap validates two distinct, valid stable slot indices and swaps only on the server.

`UItemDefinition` supplies an optional `UseEffect` gameplay-effect class for usable items. Health and mana potion definitions reference their respective effects. The old overlap actor remains a world-pickup mechanism, but its effect application is not used when an item is consumed from the backpack.

## Death and travel

On death, the Pawn may be destroyed but the authoritative PlayerState backpack remains. Once a replacement Pawn is possessed, use requests target the replacement Pawn automatically.

For seamless travel, PlayerState retains or copies its slot snapshot. For ordinary travel, the server captures the PlayerState snapshot before travel and restores it when the player is re-established in the destination world.

## Persistence and identity

A server-side persistence abstraction owns durable storage:

```cpp
Load(PlayerId) -> FBackpackSnapshot
Save(PlayerId, Snapshot)
AcquireSessionLock(PlayerId) -> bool
ReleaseSessionLock(PlayerId)
```

`PlayerId` is the authenticated online identity; local development may use a controlled test identity. The server acquires the player lock before loading inventory, rejects duplicate active sessions, saves after important mutations and disconnect, and releases the lock only after a durable final save. The first implementation may persist server-local SaveGame files behind this interface; production may replace it with a database or service without changing inventory rules.

## Verification

Automation and multiplayer PIE tests cover server-only mutation, invalid RPC rejection, partial pickup, effect failure without consumption, stable slot replication, death/respawn retention, seamless and ordinary travel restoration, reconnect restoration, and duplicate-session rejection. Verify both listen-server and dedicated-server configurations.
