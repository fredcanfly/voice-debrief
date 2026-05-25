# Production Hardening Checklist (OVH)

## Firewall
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
sudo ufw status
```

## Fail2ban
```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
sudo fail2ban-client status
```

## Service hygiene
- Run app as non-root service user.
- Keep `.env` mode at `600`.
- Rotate API keys if leaked.
- Keep system packages updated (`apt update && apt upgrade`).

## Caddy HTTPS validation
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl restart caddy
curl -I https://$VOICE_DEBRIEF_DOMAIN/health
```
