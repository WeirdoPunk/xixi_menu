# 兮兮的菜单

一个基于 Flask 的家庭菜单管理应用，支持菜品图片、分类、今日菜单、每日备注、素菜分类和用户头像。

## 功能

- 上传菜品名称、图片和分类
- 支持分类筛选和菜品数量统计
- 支持新增的“🥬 素菜”分类
- 将菜品加入或移出今日菜单
- 修改菜品分类
- 删除菜品及对应图片
- 保存每日备注
- 设置用户昵称和头像
- 支持 SQLite 和 PostgreSQL
- 支持部署到 PythonAnywhere 等 Gunicorn 环境

## 环境要求

- Python 3.10 或更高版本
- Windows、Linux 或 macOS
- 本地默认使用 SQLite，不需要额外安装数据库

项目当前运行时配置为 Python 3.13.5，见 `runtime.txt`。

## 本地运行

### 1. 进入项目目录

Windows PowerShell：

```powershell
cd C:\Users\punk\Desktop\xixi_menu
```

### 2. 创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 阻止激活脚本，可以直接使用虚拟环境中的 Python：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. 安装依赖

虚拟环境已激活时运行：

```powershell
python -m pip install -r requirements.txt
```

### 4. 启动应用

```powershell
python app.py
```

启动后打开主页：

<http://127.0.0.1:5000/>

也可以访问：

<http://localhost:5000/>

菜品和头像管理页：

<http://127.0.0.1:5000/manage>

主页只负责浏览菜单；上传菜品、修改昵称和上传头像请进入管理页。

首次启动时，程序会自动：

- 创建 `database.db`
- 创建菜品表、每日备注表和用户资料表
- 创建 `static/uploads/` 图片目录
- 初始化默认用户昵称“兮兮”

停止服务时，在终端按 `Ctrl+C`。

## 上传和使用

### 上传菜品

1. 在首页填写菜名。
2. 选择图片。
3. 选择分类，例如“🥬 素菜”。
4. 点击“上传”。

当前支持的图片格式：

- PNG
- JPG/JPEG
- GIF
- WEBP
- BMP

上传的图片保存在 `static/uploads/`，数据库只保存图片路径。

### 设置头像

在首页的用户资料区域：

1. 输入昵称。
2. 选择头像图片。
3. 点击“保存资料”。

头像支持与菜品相同的图片格式。

## 数据库配置

### 默认 SQLite

没有设置 `DATABASE_URL` 时，程序使用项目根目录下的 SQLite 文件：

```text
database.db
```

### PostgreSQL

设置 `DATABASE_URL` 后，程序会自动使用 PostgreSQL：

Windows PowerShell 示例：

```powershell
$env:DATABASE_URL = "postgresql://用户名:密码@主机:5432/数据库名"
python app.py
```

Linux/macOS 示例：

```bash
export DATABASE_URL="postgresql://用户名:密码@主机:5432/数据库名"
python app.py
```

生产环境建议同时设置随机的 `SECRET_KEY`：

```powershell
$env:SECRET_KEY = "请替换为随机字符串"
```

## 生产运行

项目的 `Procfile` 使用 Gunicorn：

```text
web: gunicorn app:app
```

手动启动生产服务：

```bash
gunicorn app:app
```

指定端口：

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```

Windows 本地开发建议使用 `python app.py`；Gunicorn 主要用于 Linux 或 PythonAnywhere 等生产环境。

## PythonAnywhere 部署

### 1. 上传项目

将以下内容上传到 PythonAnywhere 项目目录：

```text
app.py
requirements.txt
runtime.txt
templates/
static/
Procfile
```

不要上传本地的 `__pycache__/`、`.venv/` 和 `database.db`，除非你明确需要迁移本地数据。

### 2. 创建虚拟环境并安装依赖

在 PythonAnywhere Bash Console 中运行：

```bash
cd /home/你的用户名/xixi_menu
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 Web 应用

在 PythonAnywhere 的 Web 页面：

- 新建 Web App
- 选择 Manual configuration
- 选择 Python 3.10
- Virtualenv 填写：`/home/你的用户名/xixi_menu/venv`
- WSGI 文件中设置项目路径并导入 Flask 应用

WSGI 文件示例：

```python
import sys

project_home = '/home/你的用户名/xixi_menu'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
```

### 4. 配置静态文件

在 Web 页面的 Static files 中添加：

| URL | Directory |
| --- | --- |
| `/static/` | `/home/你的用户名/xixi_menu/static/` |

确保目录实际存在：

```bash
mkdir -p /home/你的用户名/xixi_menu/static/uploads
```

修改代码或配置后，在 PythonAnywhere Web 页面点击 **Reload**。

## 项目结构

```text
xixi_menu/
├── app.py                 # Flask 后端、路由和数据库初始化
├── templates/
│   └── index.html         # 菜单页面
├── static/
│   └── uploads/           # 菜品和头像图片
├── requirements.txt       # Python 依赖
├── runtime.txt            # Python 运行时版本
├── Procfile               # Gunicorn 启动配置
└── database.db            # 本地运行时自动生成，已被 git 忽略
```

## 常用检查命令

检查 Python 语法：

```powershell
python -m py_compile app.py
```

检查首页是否能正常返回：

```powershell
python -c "import app; print(app.app.test_client().get('/').status_code)"
```

返回 `200` 表示首页可以正常渲染。

## 安全提醒

- 生产环境必须修改 `SECRET_KEY`。
- 不要把数据库密码提交到 Git 仓库。
- 建议限制上传文件大小，并定期清理不再使用的图片。
- `database.db` 和 `static/uploads/` 当前已加入 `.gitignore`，不会被 Git 自动提交。
