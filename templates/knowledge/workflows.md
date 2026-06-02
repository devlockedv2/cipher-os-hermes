# Standard Workflows

## Feature Implementation (full pipeline)

1. Cipher receives request
2. Cipher creates ticket chain:
   - Lens: research existing patterns/APIs (if needed)
   - Atlas: plan implementation, define interfaces
   - Forge: build it, write tests
   - Sentinel: deploy to staging
3. Each ticket depends on the previous
4. Dependencies auto-gate execution

## Bug Fix

1. Cipher routes to Forge
2. Forge: diagnose, fix, test
3. If infra-related: Forge hands to Sentinel

## Research Task

1. Cipher routes to Lens
2. Lens: research, synthesize, produce brief
3. Brief delivered to requesting agent or user

## Deployment

1. Cipher routes to Sentinel
2. Sentinel: dry-run, deploy staging, verify, deploy prod (if approved)
3. Rollback plan defined before execution
