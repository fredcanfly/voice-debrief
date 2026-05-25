# OVH VPS-1 Deployment (Single-Server Pre-Alpha)

This deployment is intentionally simple and reproducible.

## 1) Server prerequisites
- Ubuntu 22.04+ on OVH VPS-1
- DNS A record pointed to server IP
- SSH access working

## 2) Install runtime deps
```bash
sudo apt update
sudo apt install -y git python3 python3-venv
```

## 3) Clone + bootstrap
```bash
git clone https://github.com/REPLACE_ME/voice-debrief.git
cd voice-debrief
bash deploy/ovh/deploy.sh
```

## 4) Enable service
```bash
sudo cp deploy/ovh/voice-debrief.service /etc/systemd/system/voice-debrief.service
sudo systemctl daemon-reload
sudo systemctl enable --now voice-debrief
sudo systemctl status voice-debrief --no-pager
```

## 5) Verify
```bash
curl -sS http://127.0.0.1:8000/health
```
