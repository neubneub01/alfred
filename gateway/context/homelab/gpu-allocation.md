# GPU VRAM Allocation

Total AI VRAM (active): 48 GB

## Assignment Map

| GPU | Host | Container | Primary Model | VRAM Used | Headroom |
|-----|------|-----------|--------------|-----------|----------|
| RTX 4090 (24 GB) | Host A | LXC 101 | qwen3:32b (Q4_K_M) | ~20 GB (81%) | ~4 GB |
| RTX 3070 (8 GB) | Host B | LXC 501 | qwen3:4b (Q4_K_M) | ~2.5 GB | ~5 GB |
| RTX 5060 Ti (16 GB) | Host C | LXC 100 | qwen3:14b (Q4_K_M) | ~9.3 GB | ~6.7 GB |

## Ollama Configuration

| Node | KV Cache | Keep-Alive | VRAM Gate |
|------|----------|------------|-----------|
| Host A LXC 101 | q4_0 | 60m | vram-gate.service on :11435 (90% threshold) |
| Host B LXC 501 | q4_0 | 60m | None |
| Host C LXC 100 | Default | Default | None |

## Routing Chain (OpenClaw)

```
ollama-4090/qwen3:32b  (Host A, VRAM-gated, free)
  → ollama-5060ti/qwen3:14b  (Host C, direct, free)
    → google/gemini-flash-latest  (cloud)
      → anthropic/claude-sonnet-4-6  (cloud)
        → google/gemini-3.1-pro-preview  (cloud)
          → anthropic/claude-opus-4-6  (cloud, premium)
```

## Notes

- RTX 4090 shared between Ollama and Tdarr (NVENC has dedicated silicon)
- RTX 3070 dedicated to triage + embeddings (nomic-embed-text, 768-dim)
- VRAM gate returns 503 when GPU > 90% → auto-failover to Host C → cloud
- No DeepSeek in any fallback chain (privacy policy)
- RTX 5060 Ti shared between Ollama LXC 100 and Speaches (Whisper) on bare metal
