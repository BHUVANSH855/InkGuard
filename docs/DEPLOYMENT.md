# GrammarLens — Deployment Guide

## Local development

```bash
pip install -r requirements.txt
python app.py
# http://localhost:5000
```

---

## Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

```bash
docker build -t grammarlens .
docker run -p 5000:5000 grammarlens
```

---

## Render / Railway / Fly.io

Set the start command to:
```
python app.py
```

Set environment variables:
| Key | Value |
|-----|-------|
| `PORT` | `5000` (Render sets this automatically) |

For Render, update `app.py` to read the PORT env var:
```python
import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
```

---

## systemd (Linux server)

Create `/etc/systemd/system/grammarlens.service`:

```ini
[Unit]
Description=GrammarLens
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/grammarlens
ExecStart=/usr/bin/python3 /opt/grammarlens/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now grammarlens
```

---

## Nginx reverse proxy

```nginx
server {
    listen 80;
    server_name grammarlens.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
