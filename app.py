import os
import sqlite3
import psycopg2
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, date
from collections import Counter
#todo再加个素菜专栏，加头像
#todo热菜：青椒肉丝，芹菜肉丝，黄瓜炒肉，莴笋肉片，可乐鸡翅，
#todo素菜：清炒时蔬，香菇青菜，番茄鸡蛋，清炒土豆丝，韭黄鸡蛋，
#todo冷菜：拍黄瓜，青椒皮蛋，凉拌折耳根，
#todo汤：番茄鸡蛋，酸菜粉丝汤，萝卜排骨汤
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------- 分类（用户指定） ----------
CATEGORIES = [
    {'name': '热菜', 'emoji': '🍲'},
    {'name': '素菜', 'emoji': '🥬'},
    {'name': '凉菜', 'emoji': '🥗'},
    {'name': '汤类', 'emoji': '🍜'},
    {'name': '主食', 'emoji': '🍚'},
    {'name': '饮品', 'emoji': '🥤'},
    {'name': '甜品', 'emoji': '🍰'},
    {'name': '水果', 'emoji': '🍊'},
]
CATEGORY_DISPLAY = [f"{cat['emoji']} {cat['name']}" for cat in CATEGORIES]

# ---------- 定时清理标记（单进程） ----------
last_clean_date = None

# ---------- 数据库连接 ----------
def get_db_connection():
    if 'DATABASE_URL' in os.environ:
        DATABASE_URL = os.environ['DATABASE_URL']
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    else:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

# ---------- 数据库初始化 ----------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # 创建 dishes 表
    if 'DATABASE_URL' in os.environ:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dishes (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                is_today BOOLEAN DEFAULT FALSE,
                category TEXT DEFAULT '🍳 家常小炒',
                note TEXT DEFAULT ''
            )
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                is_today BOOLEAN DEFAULT 0,
                category TEXT DEFAULT '🍳 家常小炒',
                note TEXT DEFAULT ''
            )
        ''')
    # 添加 category 和 note 列（兼容已有表）
    if 'DATABASE_URL' in os.environ:
        cur.execute('ALTER TABLE dishes ADD COLUMN IF NOT EXISTS category TEXT DEFAULT \'🍳 家常小炒\'')
        cur.execute('ALTER TABLE dishes ADD COLUMN IF NOT EXISTS note TEXT DEFAULT \'\'')
    else:
        cur.execute("PRAGMA table_info(dishes)")
        columns = [row[1] for row in cur.fetchall()]
        if 'category' not in columns:
            cur.execute('ALTER TABLE dishes ADD COLUMN category TEXT DEFAULT \'🍳 家常小炒\'')
        if 'note' not in columns:
            cur.execute('ALTER TABLE dishes ADD COLUMN note TEXT DEFAULT \'\'')

    # 创建 daily_note 表
    if 'DATABASE_URL' in os.environ:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_note (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                content TEXT NOT NULL
            )
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_note (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                content TEXT NOT NULL
            )
        ''')

    # 创建用户资料表（单用户应用固定使用 id=1）
    if 'DATABASE_URL' in os.environ:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                nickname TEXT NOT NULL DEFAULT '兮兮',
                avatar_path TEXT DEFAULT ''
            )
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                nickname TEXT NOT NULL DEFAULT '兮兮',
                avatar_path TEXT DEFAULT ''
            )
        ''')
    if 'DATABASE_URL' in os.environ:
        cur.execute(
            "INSERT INTO user_profile (id, nickname, avatar_path) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (1, '兮兮', '')
        )
    else:
        cur.execute(
            "INSERT OR IGNORE INTO user_profile (id, nickname, avatar_path) VALUES (?, ?, ?)",
            (1, '兮兮', '')
        )

    # 插入默认行（如果为空）
    cur.execute("SELECT COUNT(*) FROM daily_note")
    if cur.fetchone()[0] == 0:
        if 'DATABASE_URL' in os.environ:
            cur.execute("INSERT INTO daily_note (date, content) VALUES (%s, %s)", ('1970-01-01', ''))
        else:
            cur.execute("INSERT INTO daily_note (date, content) VALUES (?, ?)", ('1970-01-01', ''))

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------- 辅助函数 ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ---------- 路由 ----------
@app.route('/')
def index():
    global last_clean_date
    today = date.today()
    today_str = today.isoformat()

    # ----- 定时清理（每天0点触发） -----
    if last_clean_date != today:
        conn = get_db_connection()
        cur = conn.cursor()
        # 清空菜品备注（如仍有字段）
        if 'DATABASE_URL' in os.environ:
            cur.execute("UPDATE dishes SET note = '' WHERE is_today = TRUE")
            cur.execute("UPDATE daily_note SET date = %s, content = '' WHERE id = 1", (today_str,))
        else:
            cur.execute("UPDATE dishes SET note = '' WHERE is_today = 1")
            cur.execute("UPDATE daily_note SET date = ?, content = '' WHERE id = 1", (today_str,))
        conn.commit()
        cur.close()
        conn.close()
        last_clean_date = today

    # ----- GET：展示页面 -----
    conn = get_db_connection()
    cur = conn.cursor()

    # 全部菜品
    cur.execute("SELECT id, name, image_path, is_today, category, note FROM dishes ORDER BY id DESC")
    all_dishes = cur.fetchall()

    # 今日菜品
    if 'DATABASE_URL' in os.environ:
        cur.execute("SELECT id, name, image_path, category, note FROM dishes WHERE is_today = TRUE ORDER BY id DESC")
    else:
        cur.execute("SELECT id, name, image_path, category, note FROM dishes WHERE is_today = 1 ORDER BY id DESC")
    today_dishes = cur.fetchall()

    # 今日备注
    cur.execute("SELECT date, content FROM daily_note WHERE id = 1")
    row = cur.fetchone()
    if row and row[0] == today_str:
        daily_note_content = row[1]
    else:
        daily_note_content = ''

    cur.execute("SELECT nickname, avatar_path FROM user_profile WHERE id = 1")
    profile_row = cur.fetchone()
    profile = {
        'nickname': profile_row[0] if profile_row else '兮兮',
        'avatar_path': profile_row[1] if profile_row else ''
    }

    # 分类计数
    category_list = [dish[4] for dish in all_dishes]  # dish[4] = category
    category_counts = Counter(category_list)
    for cat in CATEGORY_DISPLAY:
        if cat not in category_counts:
            category_counts[cat] = 0
    total_count = len(all_dishes)

    cur.close()
    conn.close()

    return render_template('index.html',
                           all_dishes=all_dishes,
                           today_dishes=today_dishes,
                           categories=CATEGORY_DISPLAY,
                           category_counts=category_counts,
                           total_count=total_count,
                           daily_note_content=daily_note_content,
                           profile=profile)

# ---------- 菜品和用户资料管理页 ----------
@app.route('/manage')
def manage():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT nickname, avatar_path FROM user_profile WHERE id = 1")
    profile_row = cur.fetchone()
    cur.close()
    conn.close()
    profile = {
        'nickname': profile_row[0] if profile_row else '兮兮',
        'avatar_path': profile_row[1] if profile_row else ''
    }
    return render_template('manage.html', categories=CATEGORY_DISPLAY, profile=profile)


@app.route('/add_dish', methods=['POST'])
def add_dish():
    dish_name = request.form.get('dish_name', '').strip()
    if not dish_name:
        return "菜名不能为空", 400

    file = request.files.get('dish_image')
    if not file or file.filename == '':
        return "请选择一张图片", 400

    if not allowed_file(file.filename):
        return "仅支持 jpg、png、gif、webp、bmp 格式", 400

    category = request.form.get('category', '🍳 家常小炒')
    if category not in CATEGORY_DISPLAY:
        category = '🍳 家常小炒'

    original_name = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    new_filename = f"{timestamp}_{original_name}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    file.save(save_path)

    image_path = f"static/uploads/{new_filename}"
    conn = get_db_connection()
    cur = conn.cursor()
    if 'DATABASE_URL' in os.environ:
        cur.execute(
            "INSERT INTO dishes (name, image_path, category) VALUES (%s, %s, %s)",
            (dish_name, image_path, category)
        )
    else:
        cur.execute(
            "INSERT INTO dishes (name, image_path, category) VALUES (?, ?, ?)",
            (dish_name, image_path, category)
        )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('manage'))

# ---------- 切换今日状态 ----------
@app.route('/toggle_today/<int:dish_id>', methods=['POST'])
def toggle_today(dish_id):
    conn = get_db_connection()
    cur = conn.cursor()
    if 'DATABASE_URL' in os.environ:
        cur.execute("SELECT is_today FROM dishes WHERE id = %s", (dish_id,))
    else:
        cur.execute("SELECT is_today FROM dishes WHERE id = ?", (dish_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return "菜品不存在", 404
    current = row[0]
    new_val = not current
    if 'DATABASE_URL' in os.environ:
        cur.execute("UPDATE dishes SET is_today = %s WHERE id = %s", (new_val, dish_id))
    else:
        cur.execute("UPDATE dishes SET is_today = ? WHERE id = ?", (new_val, dish_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

# ---------- 删除菜品 ----------
@app.route('/delete/<int:dish_id>', methods=['POST'])
def delete_dish(dish_id):
    conn = get_db_connection()
    cur = conn.cursor()
    if 'DATABASE_URL' in os.environ:
        cur.execute("SELECT image_path FROM dishes WHERE id = %s", (dish_id,))
    else:
        cur.execute("SELECT image_path FROM dishes WHERE id = ?", (dish_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return "菜品不存在", 404
    image_path = row[0]
    if 'DATABASE_URL' in os.environ:
        cur.execute("DELETE FROM dishes WHERE id = %s", (dish_id,))
    else:
        cur.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
    conn.commit()
    cur.close()
    conn.close()
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception:
            pass
    return redirect(url_for('index'))

# ---------- 更新分类（内联） ----------
@app.route('/update_category/<int:dish_id>', methods=['POST'])
def update_category(dish_id):
    new_category = request.form.get('category')
    if new_category not in CATEGORY_DISPLAY:
        new_category = '🍳 家常小炒'
    conn = get_db_connection()
    cur = conn.cursor()
    if 'DATABASE_URL' in os.environ:
        cur.execute("UPDATE dishes SET category = %s WHERE id = %s", (new_category, dish_id))
    else:
        cur.execute("UPDATE dishes SET category = ? WHERE id = ?", (new_category, dish_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

# ---------- 更新今日备注 ----------
@app.route('/update_daily_note', methods=['POST'])
def update_daily_note():
    note = request.form.get('daily_note', '').strip()
    today_str = date.today().isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    if 'DATABASE_URL' in os.environ:
        cur.execute("UPDATE daily_note SET date = %s, content = %s WHERE id = 1", (today_str, note))
    else:
        cur.execute("UPDATE daily_note SET date = ?, content = ? WHERE id = 1", (today_str, note))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

# ---------- 更新用户资料 ----------
@app.route('/update_profile', methods=['POST'])
def update_profile():
    nickname = request.form.get('nickname', '').strip() or '兮兮'
    avatar = request.files.get('avatar')
    avatar_path = None

    if avatar and avatar.filename:
        if not allowed_file(avatar.filename):
            return "头像仅支持 jpg、png、gif、webp、bmp 格式", 400
        original_name = secure_filename(avatar.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        new_filename = f"avatar_{timestamp}_{original_name}"
        avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
        avatar_path = f"static/uploads/{new_filename}"

    conn = get_db_connection()
    cur = conn.cursor()
    if avatar_path:
        if 'DATABASE_URL' in os.environ:
            cur.execute(
                "UPDATE user_profile SET nickname = %s, avatar_path = %s WHERE id = 1",
                (nickname, avatar_path)
            )
        else:
            cur.execute(
                "UPDATE user_profile SET nickname = ?, avatar_path = ? WHERE id = 1",
                (nickname, avatar_path)
            )
    elif 'DATABASE_URL' in os.environ:
        cur.execute("UPDATE user_profile SET nickname = %s WHERE id = 1", (nickname,))
    else:
        cur.execute("UPDATE user_profile SET nickname = ? WHERE id = 1", (nickname,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('manage'))

# ---------- 启动 ----------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)