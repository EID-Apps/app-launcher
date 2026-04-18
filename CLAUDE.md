# EID App Launcher

## What this is
The landing page at apps.ellisid.com. Shows cards for each EID app (EBIF Schedules, Meeting Notes, Shop Drawing QA, etc.) with status indicators and links.

## Stack
- Python Flask (main.py)
- Jinja2 templates in templates/
- Static assets in static/
- nginx reverse proxy (nginx.conf)
- systemd service (eid-launcher.service)
- Deployed on DigitalOcean server at 209.38.130.201

## Deploy
- Code lives locally here AND on the server at /opt/eid-apps/app-launcher
- After changes: SSH in, pull or copy files, restart service
- systemctl restart eid-launcher

## App cards
- Each card shows an app name, status (Live/Planned), and link
- When a new app goes live, update the card from "Planned" to "Live" and add the URL

## EID brand
- Olive #868C54, sage #C2C8A2, warm gray #737569
- Headers: Lato Bold. Body: Arial Narrow
