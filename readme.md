# CYRacing Server

小程序端见：[github.com:qkmc-rk/cyracing_miniapp.git](https://github.com/qkmc-rk/cyracing_miniapp)

基于 FastAPI 的 Assetto Corsa 赛车数据 API 服务，为微信小程序提供比赛结果、车手画像、圈速分析等功能。

仍存在问题：车手画像数据算法比较随意，另外有些异常比赛记录仍未排除，统计信息可能存在偏差
---

## 架构概览

```
┌─────────────────┐     HTTPS (WX小程序)    ┌──────────────┐
│  微信小程序       │ ◄──────────────────────► │   Nginx      │
│  (前端)          │                         │   :8444 SSL  │
└─────────────────┘                         └──────┬───────┘
                                                   │ proxy_pass
                                          ┌────────▼───────┐
                                          │   Uvicorn      │
                                          │   :8000 (4 workers)
                                          │   FastAPI APP  │
                                          └────────┬───────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                                    │              │              │
                              ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
                              │  MySQL     │  │  JSON   │  │  Static   │
                              │  (阿里云RDS)│  │  扫描器  │  │  Files    │
                              └───────────┘  │  /opt/.. │  └───────────┘
                                             │  /results │
                                             └──────────┘
```

**技术栈：** Python 3.10 · FastAPI · SQLAlchemy + PyMySQL · Nginx · MySQL (阿里云 RDS)

**核心功能：**
- 比赛数据自动导入（每 60 秒扫描 JSON 目录）（跑该服务的前置条件是已经搭建好ac在线比赛服务器）
- 车手画像（安全分、天梯分、驾照等级、全服排名）
- 微信小程序登录绑定
- 公告 CRUD
- 圈速与碰撞事件详情

---

## 目录结构

```
cyracing_data/
├── app/
│   ├── main.py                 # FastAPI 入口，路由注册，JSON 扫描后台任务
│   ├── database.py             # SQLAlchemy 引擎和 Session 配置
│   ├── models.py               # 所有数据表 ORM 模型
│   ├── routes/
│   │   ├── races.py            # 比赛相关接口
│   │   ├── events.py           # 事件相关接口
│   │   ├── drivers.py          # 车手接口
│   │   ├── users.py            # 用户登录/绑定接口
│   │   ├── announcements.py    # 公告 CRUD 接口
│   │   └── driver_profiles.py  # 车手画像接口
│   └── schemas/                # Pydantic 请求/响应模型
├── import_cyracing_results.py  # JSON 比赛数据解析导入脚本
├── requirements.txt            # Python 依赖
├── start_prod.sh               # 生产环境启动脚本
├── .env                        # 环境变量（不入 git）
├── static/                     # 静态资源目录
├── json_results/               # 待导入的 JSON 文件目录
└── key/                        # SSL 证书（不入 git）
```

---

## 数据模型

| 表名 | 说明 |
|------|------|
| `cars` | 赛车信息（模型名、制造商、级别） |
| `drivers` | 车手信息（Steam GUID、姓名、车队、国家） |
| `tracks` | 赛道信息（名称、配置、长度） |
| `races` | 比赛基本信息（赛道、类型、圈数、日期） |
| `race_results` | 比赛结果（排名、最佳单圈、总时间、完成圈数） |
| `laps` | 单圈详细记录（时间、分段 S1/S2/S3、切弯、轮胎） |
| `events` | 赛事事件（碰撞类型、碰撞速度、世界/相对坐标） |
| `users` | 微信用户（openid 绑定车手） |
| `announcements` | 公告（标题、富文本内容、置顶） |
| `driver_profiles` | 车手画像（安全分、天梯分、驾照等级、全服排名） |

---

# API 接口文档

## 比赛 (Races) — `/races`

### `GET /races/`
获取比赛列表（按日期倒序），包含每场参赛车手。

**响应示例：**
```json
[
  {
    "race_id": 1,
    "date": "2026-06-15 20:30:00",
    "session_type": "RACE",
    "track_name": "spa",
    "entrants": ["车手A", "车手B"]
  }
]
```

### `GET /races/summaries`
批量获取所有比赛的摘要数据（单次请求），含每位参赛者的最佳单圈、平均干净圈速、切弯次数、事故数、轮胎类型。

### `GET /races/{race_id}/summary`
获取单场比赛摘要，返回同上格式。

### `GET /races/{race_id}/laps`
获取某场比赛所有参赛者的完整圈速数据（分段 S1/S2/S3、轮胎、切弯、有效性）。

### `GET /races/{race_id}/driver/{driver_id}/laps`
获取指定车手在某场比赛中的圈速详细数据。

### `GET /races/{race_id}/driver/{driver_id}/collisions`
获取指定车手在某场比赛中的碰撞事件列表。
包含：碰撞类型、碰撞速度(impact_speed)、相对位置、世界坐标。

---

## 车手 (Drivers) — `/drivers`

### `GET /drivers/{steam_guid}/races`
通过 Steam GUID 获取某车手的所有参赛记录（日期、赛道、赛车、排名、最佳单圈等）。

---

## 用户 (Users) — `/users`

### `POST /users/login`
微信小程序登录。

**请求体：**
```json
{ "code": "微信 wx.login() 返回的 code" }
```

**响应：**
```json
{
  "openid": "xxxx",
  "user_id": 1,
  "is_new_user": false
}
```

### `POST /users/bind`
绑定微信用户与车手数据。

**请求体：**
```json
{ "openid": "xxxx", "steam_guid": "76561198000000000" }
```

### `GET /users/{openid}/driver`
通过 openid 查询已绑定的车手信息。

---

## 车手画像 (Driver Profiles) — `/driver_profiles`

### `GET /driver_profiles/profiles`
获取所有车手画像列表。

**查询参数：** `?order_by=ladder_score`（可选：`total_races`、`safety_score`）

**响应示例：**
```json
[
  {
    "driver_id": 1,
    "driver_name": "车手A",
    "team_name": "车队X",
    "total_races": 50,
    "total_laps": 320,
    "ladder_score": 1650,
    "license_level": "C",
    "rank_overall": 1
  }
]
```

### `GET /driver_profiles/profiles/{driver_id}`
获取指定车手的画像详情。
包含：总比赛场次、总驾驶时间、总圈数、安全分(0-10)、天梯分、驾照等级(A/B/C/D/N)、全服排名。

### `POST /driver_profiles/profiles/{driver_id}/refresh`
刷新指定车手的画像数据，实时重算安全分、天梯分、驾照等级和排名。

### `POST /driver_profiles/profiles/refresh`
刷新**所有**车手的画像数据（耗时长，慎用）。

---

## 公告 (Announcements) — `/announcements`

### `GET /announcements/`
获取全部公告（置顶在前，按发布时间倒序）。

### `GET /announcements/{announcement_id}`
获取单条公告详情。

### `POST /announcements/`
创建新公告。

### `PUT /announcements/{announcement_id}`
更新公告（部分字段可选）。

### `DELETE /announcements/{announcement_id}`
删除公告。

---

## 事件 (Events) — `/events`

### `GET /events/race/{race_id}`
获取某场比赛的所有事件记录。

---

## 静态资源 — `/static/`

通过 Nginx 直接代理静态文件，后端也通过 `StaticFiles` 挂载提供备用访问。

---

# 阿里云 CentOS 7 部署指南

## 1. 环境准备

```bash
# 安装依赖
yum install -y gcc make openssl11-devel bzip2-devel libffi-devel zlib-devel

# 编译安装 Python 3.10
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

## 2. 部署代码

```bash
# 创建目录
mkdir -p /opt/cyracing

# 上传代码（本地执行）
scp -r app/ import_cyracing_results.py requirements.txt start_prod.sh .env root@<服务器IP>:/opt/cyracing/

# 上传 SSL 证书
scp -r key/ruankun.xyz_nginx/* root@<服务器IP>:/etc/nginx/ssl/
```

## 3. 安装依赖

```bash
cd /opt/cyracing
/usr/local/python310/bin/pip3.10 install -r requirements.txt
```

## 4. 环境变量配置 (.env)

```env
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_HOST=你的RDS地址
DB_PORT=3306
DB_NAME=cyracing
WX_APPID=微信小程序AppID
WX_SECRET=微信小程序Secret
JSON_DIR=/opt/asm/server/results（需要确认你自己的ac服务器results目录在哪里）
STATIC_DIR=static
```

## 5. Nginx HTTPS 配置

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

配置文件放到 `/etc/nginx/conf.d/cyracing.conf`，然后：

```bash
nginx -t && systemctl reload nginx
或者
systemctl restart nginx
```

## 6. 启动服务

```bash
cd /opt/cyracing
bash start_prod.sh
```

服务在 `http://127.0.0.1:8000` 运行，对外开放 `https://ruankun.xyz:8444`。
(记得在云服务器安全组中添加端口放行)

## 7. 日常运维

```bash
# 查看日志
tail -f /opt/cyracing/server.log

# 重启服务
pkill -f uvicorn
bash /opt/cyracing/start_prod.sh

# 查看进程
ps aux | grep uvicorn
```

---

## 数据导入

比赛数据 JSON 由 Assetto Corsa 服务器自动生成到 `JSON_DIR` 目录。

- 启动时自动扫描已有文件
- 运行期间每 60 秒检测新文件
- 新文件等待 3 秒确保写入完成后自动导入
- 通过 `races.source_file` 唯一约束防止重复导入

---

## 🙏 鸣谢

- **[CodeBuddy](https://codebuddy.tencent.com/)** — AI 智能编程助手，助力本项目高效开发
- **[esports podium team](https://space.bilibili.com/23046921?spm_id_from=333.337.search-card.all.click)** — 提供灵感和氛围（bilibili up主:EktarTee模拟赛车）
- **[Assetto Corsa Server Manager](https://emperorservers.com/assetto-corsa-server-manager/)** — Assetto Corsa 服务器管理工具
- **[Content Manager](https://assettocorsa.club/content-manager.html)** — Assetto Corsa 内容管理器，PC 端必备神器
- **[Low Fuel Motorsports](https://lowfuelmotorsport.com/)** — LFM比赛平台提供设计灵感
---

## 📄 许可证

随便玩

---

## 👤 作者
## [bilibili up主: 阮超越咦](https://space.bilibili.com/14785225?spm_id_from=333.337.0.0)
