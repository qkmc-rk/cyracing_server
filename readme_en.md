# CYRacing Server

miniapp: github.com:qkmc-rk/cyracing_miniapp.git

A FastAPI-based API service for Assetto Corsa racing data, providing race results, driver profiles, lap analysis, and more for WeChat Mini Programs.
仍存在问题：车手画像数据算法比较随意，另外有些异常比赛记录仍未排除，统计信息可能存在偏差
---

## Architecture Overview

```
┌─────────────────┐     HTTPS (Mini Program)  ┌──────────────┐
│  WeChat Mini     │ ◄────────────────────────► │   Nginx      │
│  Program         │                           │   :8444 SSL  │
└─────────────────┘                           └──────┬───────┘
                                                     │ proxy_pass
                                            ┌────────▼───────┐
                                            │   Uvicorn      │
                                            │   :8000        │
                                            │   (4 workers)  │
                                            │   FastAPI APP  │
                                            └────────┬───────┘
                                                     │
                                      ┌──────────────┼──────────────┐
                                      │              │              │
                                ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
                                │  MySQL     │  │  JSON   │  │  Static   │
                                │  (Aliyun   │  │ Scanner │  │  Files    │
                                │   RDS)     │  │ /opt/.. │  └───────────┘
                                └───────────┘  │ /results │
                                               └──────────┘
```

**Tech Stack:** Python 3.10 · FastAPI · SQLAlchemy + PyMySQL · Nginx · MySQL (Alibaba Cloud RDS)

**Core Features:**
- Auto-import race data (JSON directory scanned every 60 seconds)
- Driver profiles (safety score, ladder score, license level, overall rank)
- WeChat Mini Program login & driver binding
- Announcements CRUD
- Lap times & collision event details

---

## Directory Structure

```
cyracing_data/
├── app/
│   ├── main.py                 # FastAPI entry point, routes, JSON scan background task
│   ├── database.py             # SQLAlchemy engine & session configuration
│   ├── models.py               # All ORM table models
│   ├── routes/
│   │   ├── races.py            # Race-related endpoints
│   │   ├── events.py           # Event-related endpoints
│   │   ├── drivers.py          # Driver endpoints
│   │   ├── users.py            # User login/binding endpoints
│   │   ├── announcements.py    # Announcement CRUD endpoints
│   │   └── driver_profiles.py  # Driver profile endpoints
│   └── schemas/                # Pydantic request/response models
├── import_cyracing_results.py  # Race JSON data parser & importer
├── requirements.txt            # Python dependencies
├── start_prod.sh               # Production startup script
├── .env                        # Environment variables (git ignored)
├── static/                     # Static assets directory
├── json_results/               # Pending JSON files for import
└── key/                        # SSL certificates (git ignored)
```

---

## Data Model

| Table | Description |
|-------|-------------|
| `cars` | Car info (model, manufacturer, class) |
| `drivers` | Driver info (Steam GUID, name, team, nation) |
| `tracks` | Track info (name, config, length) |
| `races` | Race info (track, type, laps, date) |
| `race_results` | Race results (position, best lap, total time, laps completed) |
| `laps` | Lap details (time, sectors S1/S2/S3, cuts, tyre) |
| `events` | Race events (collision type, impact speed, world/relative position) |
| `users` | WeChat users (openid to driver binding) |
| `announcements` | Announcements (title, rich text content, pinned) |
| `driver_profiles` | Driver profiles (safety score, ladder score, license level, overall rank) |

---

# API Documentation

## Races — `/races`

### `GET /races/`
Returns the race list (sorted by date descending), including entrants for each race.

**Response example:**
```json
[
  {
    "race_id": 1,
    "date": "2026-06-15 20:30:00",
    "session_type": "RACE",
    "track_name": "spa",
    "entrants": ["DriverA", "DriverB"]
  }
]
```

### `GET /races/summaries`
Batch fetch summaries for all races in a single request. Includes each entrant's best lap, average clean lap time, cuts, incident count, and tyre type.

### `GET /races/{race_id}/summary`
Fetch the summary for a single race (same format as above).

### `GET /races/{race_id}/laps`
Get complete lap data for all entrants in a race (sectors S1/S2/S3, tyre, cuts, validity).

### `GET /races/{race_id}/driver/{driver_id}/laps`
Get detailed lap data for a specific driver in a specific race.

### `GET /races/{race_id}/driver/{driver_id}/collisions`
Get collision events for a specific driver in a specific race. Includes: collision type, impact speed, relative position, world coordinates.

---

## Drivers — `/drivers`

### `GET /drivers/{steam_guid}/races`
Get all race records for a driver by Steam GUID (date, track, car, position, best lap, etc.).

---

## Users — `/users`

### `POST /users/login`
WeChat Mini Program login.

**Request body:**
```json
{ "code": "code returned by wx.login()" }
```

**Response:**
```json
{
  "openid": "xxxx",
  "user_id": 1,
  "is_new_user": false
}
```

### `POST /users/bind`
Bind a WeChat user to a driver.

**Request body:**
```json
{ "openid": "xxxx", "steam_guid": "76561198000000000" }
```

### `GET /users/{openid}/driver`
Query the driver bound to a given openid.

---

## Driver Profiles — `/driver_profiles`

### `GET /driver_profiles/profiles`
Get the list of all driver profiles.

**Query params:** `?order_by=ladder_score` (also supports `total_races`, `safety_score`)

**Response example:**
```json
[
  {
    "driver_id": 1,
    "driver_name": "DriverA",
    "team_name": "TeamX",
    "total_races": 50,
    "total_laps": 320,
    "ladder_score": 1650,
    "license_level": "C",
    "rank_overall": 1
  }
]
```

### `GET /driver_profiles/profiles/{driver_id}`
Get detailed profile for a specific driver.
Includes: total races, total drive time, total laps, safety score (0-10), ladder score, license level (A/B/C/D/N), overall rank.

### `POST /driver_profiles/profiles/{driver_id}/refresh`
Refresh a single driver's profile data. Recalculates safety score, ladder score, license level, and rank in real time.

### `POST /driver_profiles/profiles/refresh`
Refresh profile data for **all** drivers (time-consuming, use sparingly).

---

## Announcements — `/announcements`

### `GET /announcements/`
Get all announcements (pinned first, then by publish date descending).

### `GET /announcements/{announcement_id}`
Get a single announcement detail.

### `POST /announcements/`
Create a new announcement.

### `PUT /announcements/{announcement_id}`
Update an announcement (partial fields supported).

### `DELETE /announcements/{announcement_id}`
Delete an announcement.

---

## Events — `/events`

### `GET /events/race/{race_id}`
Get all event records for a race.

---

## Static Files — `/static/`

Static files proxied directly through Nginx; also mounted via FastAPI `StaticFiles` as a fallback.

---

# Alibaba Cloud CentOS 7 Deployment Guide

## 1. Environment Setup

```bash
# Install dependencies
yum install -y gcc make openssl11-devel bzip2-devel libffi-devel zlib-devel

# Build Python 3.10 from source
cd /tmp
wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz
tar xzf Python-3.10.13.tgz
cd Python-3.10.13

./configure --prefix=/usr/local/python310 \
    --enable-optimizations \
    CPPFLAGS="-I/usr/include/openssl11" \
    LDFLAGS="-L/usr/lib64/openssl11"

make -j$(nproc)
make altinstall
```

## 2. Deploy Code

```bash
# Create directory
mkdir -p /opt/cyracing

# Upload code (run locally)
scp -r app/ import_cyracing_results.py requirements.txt start_prod.sh .env root@<server_ip>:/opt/cyracing/

# Upload SSL certificates
scp -r key/ruankun.xyz_nginx/* root@<server_ip>:/etc/nginx/ssl/
```

## 3. Install Dependencies

```bash
cd /opt/cyracing
/usr/local/python310/bin/pip3.10 install -r requirements.txt
```

## 4. Environment Variables (`.env`)

```env
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=your_rds_host
DB_PORT=3306
DB_NAME=cyracing
WX_APPID=your_wechat_appid
WX_SECRET=your_wechat_secret
JSON_DIR=/opt/asm/server/results（需要确认你自己的ac服务器results目录在哪里）
STATIC_DIR=static
```

## 5. Nginx HTTPS Configuration

```nginx
server {
    listen 8080;
    server_name ruankun.xyz www.ruankun.xyz;
    return 301 https://$host:8444$request_uri;
}

server {
    listen 8444 ssl http2;
    server_name ruankun.xyz www.ruankun.xyz;

    ssl_certificate     /etc/nginx/ssl/ruankun.xyz_bundle.pem;
    ssl_certificate_key /etc/nginx/ssl/ruankun.xyz.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /static/ {
        alias /opt/cyracing/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Place this config at `/etc/nginx/conf.d/cyracing.conf`, then:

```bash
nginx -t && systemctl reload nginx
```

## 6. Start the Service

```bash
cd /opt/cyracing
bash start_prod.sh
```

The service runs at `http://127.0.0.1:8000` internally, exposed externally at `https://ruankun.xyz:8444`.
(记得在云服务器安全组中添加端口放行)
## 7. Routine Operations

```bash
# View logs
tail -f /opt/cyracing/server.log

# Restart service
pkill -f uvicorn
bash /opt/cyracing/start_prod.sh

# Check processes
ps aux | grep uvicorn
```

---

## Data Import

Race data JSON files are automatically generated by the Assetto Corsa server into the `JSON_DIR` directory.

- Existing files are scanned on startup
- New files are detected every 60 seconds during runtime
- New files wait 3 seconds to ensure write completion before importing
- The `races.source_file` unique constraint prevents duplicate imports


# 参考
TENCENT CLOUD CodeBuddy