---
name: migrating-fabric-trial-capacities
description: Migrate Power BI / Fabric workspaces from trial capacity to a production capacity using the Fabric CLI (fab). Use when the user asks to move workspaces off a trial capacity, migrate trial workspaces, or reassign workspace capacity in bulk.
---

# Migrate Trial Capacity Workspaces

<!-- Ported from plugins/fabric-cli/commands/migrating-fabric-trial-capacities.md (Claude Code slash command) for Codex. -->

Migrate workspaces from Fabric trial capacity to the production capacity the user names (ask if not given). Requires the `fab` CLI, authenticated (`fab auth login`); load the `fabric-cli` skill for syntax details.

## Step 1: Audit Trial Workspaces

```bash
# List all capacities
fab ls .capacities

# List workspaces on trial capacity
fab ls -l | grep "Trial-"

# Count trial workspaces
fab ls -l | grep "Trial-" | wc -l
```

## Step 2: Identify Target Capacity

```bash
# List available capacities
fab ls .capacities -l

# Get capacity details
fab get ".capacities/TargetCapacity.Capacity"
```

## Step 3: Migrate Single Workspace

```bash
# Assign workspace to new capacity
fab assign ".capacities/TargetCapacity.Capacity" -W "WorkspaceName.Workspace" -f
```

## Step 4: Bulk Migration

```bash
# Migrate all trial workspaces to target capacity
TARGET_CAPACITY="ProductionCapacity"

fab ls -l | grep "Trial-" | cut -d' ' -f1 | while read ws; do
  echo "Migrating: $ws"
  fab assign ".capacities/$TARGET_CAPACITY.Capacity" -W "$ws" -f
done
```

## Step 5: Verify Migration

```bash
# Check workspace capacity assignment
fab get "WorkspaceName.Workspace" -q "capacityId"

# Verify no workspaces remain on trial
fab ls -l | grep "Trial-" | wc -l
```

## Pre-Migration Checklist

- [ ] Verify target capacity has sufficient CUs
- [ ] Check target capacity region matches workspaces
- [ ] Ensure you have admin permissions on workspaces
- [ ] Back up critical items before migration
- [ ] Schedule during low-usage period

## Notes

- Capacity assignment is immediate but may briefly affect running jobs
- Cross-region migration is not supported
- Trial capacity expires after 60 days
- Some features may differ between trial and production capacities
