# Homelab Architecture

## Node Inventory

| Node | Hostname | IP | CPU | RAM | GPU | Role |
|------|----------|----|-----|-----|-----|------|
| Host A | neubneub | 192.168.1.188 | i9-13900K (32t) | 128 GB | RTX 4090 (24 GB) | Compute: Ollama primary, Tdarr |
| Host B | neub | 192.168.1.166 | Ryzen 9 9950X (24t) | 96 GB | RTX 3070 (8 GB) | Storage + Media: Plex, *arr stack, NFS |
| Host C | neub3 | 192.168.1.22 | Ryzen 9 7900 (24t) | 64 GB | RTX 5060 Ti (16 GB) | AI workloads, n8n, LiteLLM gateway |
| UGreen NAS | — | 192.168.1.107 | — | — | — | Navidrome, Nextcloud |

## Key LXC/CT Containers

| Container | Host | IP | Service |
|-----------|------|----|---------|
| LXC 101 | Host A | 192.168.1.220 | Ollama (4090), Tdarr, Open WebUI |
| CT 102 | Host A | 192.168.1.221 | Paperless-ngx |
| LXC 201 | Host B | 192.168.1.38 | *arr stack, ntfy, Homepage, Qdrant, Music Rec |
| LXC 501 | Host B | 192.168.1.41 | Ollama (3070), Whisper/Speaches |
| LXC 110 | Host B | 192.168.1.240 | Cloudflare Tunnel (cloudflared) |
| LXC 100 | Host C | 192.168.1.50 | Ollama (5060 Ti) |
| CT 101 | Host C | 192.168.1.51 | Grafana, Prometheus, Alertmanager |
| CT 102 | Host C | 192.168.1.52 | LiteLLM gateway, n8n, Agent Service |

## Storage Architecture

- **Host A ZFS `fast`**: NVMe pool for compute workloads
- **Host B ZFS `tank`**: HDD pool for media + NFS exports (no redundancy — stripe)
- **NFS exports**: /tank/ai-context, /tank/media, /tank/backups
- **Proxmox bind mounts**: Used for unprivileged LXC NFS access

## External Access

- Cloudflare Zero Trust Tunnel from LXC 110 (192.168.1.240)
- Tunnel ID: e62ae79a-7e67-4caf-90ea-e8505c496977
- No inbound NAT, zero exposed WAN ports
- Access policy: Homelab Wildcard (email OTP auth)
