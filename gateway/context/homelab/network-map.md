# Network Map

## Subnet: 192.168.1.0/24

All devices on a single flat subnet. No VLANs configured.

## Static IP Assignments

### Bare Metal Hosts
| IP | Hostname | Role |
|----|----------|------|
| 192.168.1.188 | neubneub (Host A) | Proxmox compute node |
| 192.168.1.166 | neub (Host B) | Proxmox storage/media node |
| 192.168.1.22 | neub3 (Host C) | Proxmox AI workloads node |
| 192.168.1.107 | UGreen NAS | Navidrome, Nextcloud |

### LXC/CT Containers
| IP | Container | Host | Service |
|----|-----------|------|---------|
| 192.168.1.220 | LXC 101 | Host A | Ollama, Tdarr, Open WebUI |
| 192.168.1.221 | CT 102 | Host A | Paperless-ngx |
| 192.168.1.222 | CT 103 | Host A | Kasm Workspaces |
| 192.168.1.38 | LXC 201 | Host B | *arr stack, ntfy, services |
| 192.168.1.41 | LXC 501 | Host B | Ollama (3070), Speaches |
| 192.168.1.240 | LXC 110 | Host B | Cloudflare Tunnel |
| 192.168.1.50 | LXC 100 | Host C | Ollama (5060 Ti) |
| 192.168.1.51 | CT 101 | Host C | Grafana, Prometheus |
| 192.168.1.52 | CT 102 | Host C | LiteLLM, n8n, Agent Service |

## DNS / Cloudflare Tunnel Routes

| Hostname | Target |
|----------|--------|
| sonarr.neubneub.com | 192.168.1.38:8989 |
| radarr.neubneub.com | 192.168.1.38:7878 |
| lidarr.neubneub.com | 192.168.1.38:8686 |
| sab.neubneub.com | 192.168.1.38:8080 |
| overseerr.neubneub.com | 192.168.1.38:5055 |
| tdarr.neubneub.com | 192.168.1.220:8265 |
| ai.neubneub.com | 192.168.1.220:3000 |
| plex.neubneub.com | 192.168.1.180:32400 |
| n8n.neubneub.com | 192.168.1.52:5678 |
| gateway.neubneub.com | 192.168.1.52:4000 |

## Key Ports

| Port | Service |
|------|---------|
| 4000 | LiteLLM Gateway |
| 5678 | n8n |
| 8100 | Agent Service |
| 8090 | ntfy |
| 8000 | Paperless-ngx |
| 9090 | Prometheus |
| 9101 | AI Gateway Prometheus Exporter |
| 11434 | Ollama API |
| 11435 | VRAM Gate (Host A) |
