# Homelab Troubleshooting Guide

## Common Issues

### Ollama Not Responding
1. Check service: `systemctl status ollama`
2. Check GPU: `nvidia-smi` — look for VRAM exhaustion
3. Check logs: `journalctl -u ollama --no-pager -n 50`
4. Restart: `systemctl restart ollama`
5. If VRAM stuck: `nvidia-smi --gpu-reset` (last resort)

### Container Won't Start
1. Check config: `pct config <CTID>`
2. Check logs: `pct start <CTID> --debug`
3. Common cause: mount point failures (NFS not available)
4. Fix: ensure NFS is mounted on Proxmox host before starting CT

### NFS Mount Issues
- NFS server: Host B (192.168.1.166), exports from /tank/
- Unprivileged LXCs can't mount NFS directly
- Solution: Mount on Proxmox host, bind-mount into LXC via `pct set <CTID> -mp0`
- Check: `showmount -e 192.168.1.166`

### Docker Container Issues
1. Check status: `docker ps -a`
2. Check logs: `docker logs --tail 50 <container>`
3. Restart: `docker compose restart <service>`
4. Rebuild: `docker compose up -d --build <service>`
5. Check disk: `df -h` — Docker can fill up storage

### GPU Passthrough Not Working
1. Verify cgroup rules in LXC config
2. Check `/dev/nvidia*` devices exist inside container
3. Verify driver version matches host: `nvidia-smi`
4. Check `ls -la /dev/dri/` for render nodes

### Cloudflare Tunnel Issues
- Tunnel runs on LXC 110 (192.168.1.240)
- Config: `/etc/cloudflared/config.yml`
- Creds: `/root/.cloudflared/`
- Check: `systemctl status cloudflared`
- Logs: `journalctl -u cloudflared --no-pager -n 30`
- Cloudflare Access may block API endpoints (wildcard policy)

### High CPU / Memory Usage
1. Check: `htop` or `top`
2. Common culprits: Tdarr transcoding, Ollama model loading, SABnzbd extraction
3. Tdarr: check active workers at http://192.168.1.220:8265
4. Ollama: large model loads spike RAM temporarily

### Prometheus/Grafana Not Showing Data
1. Check Prometheus targets: http://192.168.1.51:9090/targets
2. Check exporter is running on target host
3. Verify firewall allows scrape port
4. Check Grafana data source config

## SSH Quick Reference

```bash
ssh root@192.168.1.188  # Host A (neubneub)
ssh root@192.168.1.166  # Host B (neub)
ssh root@192.168.1.22   # Host C (neub3)
```

Access containers from host:
```bash
pct exec <CTID> -- bash
pct exec <CTID> -- <command>
```
