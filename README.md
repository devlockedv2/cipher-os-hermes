# CIPHER-OS

A distributable multi-agent OS layer for [Hermes Agent](https://hermes-agent.nousresearch.com).

5 specialized agents — one orchestrator — working in isolated workspaces.

## Agents

| Agent | Role |
|-------|------|
| Cipher | Orchestrator — routes, delegates, approves |
| Lens | Researcher — deep research, source synthesis |
| Atlas | Planner — architecture, estimation, planning |
| Forge | Developer — code, tests, refactoring |
| Sentinel | DevOps — infra, deploy, monitoring |

## Install

```bash
curl -sSL https://raw.githubusercontent.com/devlockedv2/cipher-os-hermes/main/install.sh | bash
```

## Documentation

See `docs/` and `BLUEPRINT.md`.

## License

MIT
