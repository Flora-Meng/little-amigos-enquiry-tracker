# Little Amigos Enquiry Tracker — 上线与交接说明

更新日期：2026-08-16

## 本次已经完成

- 正式环境使用 Gunicorn 提供 Web 服务。
- WhiteNoise 收集、压缩并提供带版本号的静态文件。
- `DEBUG=0` 时强制要求真实 `DJANGO_SECRET_KEY`。
- 启用 HTTPS 跳转、安全 Cookie、代理 HTTPS 识别和安全响应头。
- 支持托管 PostgreSQL 的 `DATABASE_URL`。
- 新增无需登录的 `/health/` 健康检查（只返回服务状态，不泄露业务数据）。
- 提供 Render Blueprint、Dockerfile、构建脚本和启动脚本。
- Docker 镜像已在本机成功构建和运行；`/health/` 返回 HTTP 200。
- Django 全部 76 项自动测试通过，正式环境安全检查 0 个问题。

## 重要文件

- `render.yaml`：Render Web Service 与 PostgreSQL 配置。
- `Dockerfile`：可移植到支持 Docker 的其他平台。
- `build.sh`：安装依赖并收集静态文件。
- `start.sh`：执行数据库迁移，再启动 Gunicorn。
- `.env.example`：正式环境变量名称样板，不包含真实密码。
- `config/settings.py`：正式环境安全、数据库和静态文件设置。
- `config/views.py`：健康检查。

## 推荐发布方式

推荐先用 Render 发布，因为项目已经包含 `render.yaml`。发布会创建一个 Web Service 和一个 PostgreSQL 数据库。正式创建前应先查看 Render 当前价格并选择方案；不要把真实密码或密钥提交到代码库。

发布流程：

1. 为项目创建私有 Git 仓库并推送代码。
2. 在 Render 连接该私有仓库，选择 Blueprint，并让平台读取 `render.yaml`。
3. Render 自动生成 `DJANGO_SECRET_KEY`，并把 PostgreSQL 连接写入 `DATABASE_URL`。
4. 首次部署完成后，在 Render Shell 中依次设置三位用户的初始密码：

   ```bash
   python manage.py set_initial_password flora@littleamigos.au
   python manage.py set_initial_password southland@littleamigos.com
   python manage.py set_initial_password canberra@littleamigos.com
   ```

5. 分别用 Flora、Kiva、Emma 登录，确认地点权限正确。
6. Flora 登录后重新生成 Extension token。
7. Chrome 扩展的 Tracker URL 从 `http://127.0.0.1:8000` 改为正式 HTTPS 地址，再粘贴新 token 并点击 **Save and test**。

## 环境变量

正式环境必须具备：

```text
DJANGO_SECRET_KEY=<由托管平台生成的长随机值>
DEBUG=0
DATABASE_URL=<托管 PostgreSQL 连接地址>
```

Render 自动提供 `RENDER_EXTERNAL_HOSTNAME`，应用会据此设置允许访问的域名和 CSRF 来源。若使用其他平台或自定义域名，还需设置：

```text
ALLOWED_HOSTS=tracker.example.com
CSRF_TRUSTED_ORIGINS=https://tracker.example.com
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=1
```

只有确认域名和所有子域名都长期使用 HTTPS 后，才启用 HSTS 子域名设置。

## 备份与恢复

至少每天备份 PostgreSQL，并定期实际测试恢复。通用命令如下：

```bash
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" --file enquiry-tracker.dump
pg_restore --no-owner --no-acl --dbname "$DATABASE_URL" enquiry-tracker.dump
```

恢复可能覆盖或重复正式数据，应先在独立测试数据库演练，不要直接对正式库执行未经验证的恢复命令。

## 上线验收清单

- `https://正式地址/health/` 返回 `{"status": "ok"}`。
- 未登录访问首页会跳转登录页。
- Flora 能看到 Southland 与 Canberra；Kiva、Emma 只能看到自己的地点。
- 新建 enquiry、更新状态、添加 note、安排 follow-up 均正常。
- Zumo 扩展能识别、导入、忽略及处理重复 enquiry。
- 管理后台、数据库和托管平台都启用了强密码与双重验证。
- 已设置自动备份和故障通知。

## 本机验证结果

```text
76 tests passed
Django deployment check: 0 issues
Docker image: little-amigos-enquiry-tracker:local
Health check: HTTP/1.1 200 OK
Response: {"status": "ok"}
```
