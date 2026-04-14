# 1. 导入工具包
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import time
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash, check_password_hash

# 加载环境变量
load_dotenv()

# 2. 创建Flask应用
app = Flask(__name__)

# 配置 Session 密钥 (非常重要)
app.secret_key = os.getenv('SECRET_KEY', 'your_fallback_secret_key_here')

# 3. 数据库连接配置 (企业级 ORM 配置方式)
DB_PASSWORD = os.getenv('DB_PASSWORD')
if not DB_PASSWORD:
    raise ValueError("❌ 未设置 DB_PASSWORD，请检查 .env 文件")

# 构建 SQLAlchemy 专用的数据库 URI
db_uri = f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{DB_PASSWORD}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 3306)}/{os.getenv('DB_NAME', 'shequ')}?charset=utf8mb4"
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化 ORM
db = SQLAlchemy(app)

# 4. 定义数据模型 Models
class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    time = db.Column(db.String(50), nullable=False)

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    time = db.Column(db.String(50), nullable=False)

class ServiceOrder(db.Model):
    __tablename__ = 'service_orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    detail = db.Column(db.Text, nullable=False)
    service_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='待处理')
    created_at = db.Column(db.String(50), nullable=False)

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# 应用启动时自动建表
with app.app_context():
    db.create_all()
    print("✅ 数据库及 ORM 模型初始化成功")
    if not Admin.query.first():
        # 【核心修改】：绝对不存明文！使用加盐哈希算法加密密码
        hashed_pwd = generate_password_hash('123456') 
        default_admin = Admin(username='admin', password=hashed_pwd)
        db.session.add(default_admin)
        db.session.commit()
        print("✅ 默认管理员账号创建成功 (账号: admin, 初始密码已加密存储)")

# ----------------- 全局权限拦截器 -----------------
@app.before_request
def check_admin_permission():
    path = request.path
    if path.startswith('/admin/') and path != '/admin/login' and path != '/admin/do_login':
        if not session.get('is_admin_logged_in'):
            return redirect('/admin/login')

# ----------------- 登录相关路由 -----------------
@app.route('/admin/login')
def login_page():
    return render_template('admin/login.html')

@app.route('/admin/do_login', methods=['POST'])
def do_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # 1. 先只用用户名去数据库里找人
    admin = Admin.query.filter_by(username=username).first()
    
    # 2. 如果人存在，并且【校验密码哈希值】正确
    if admin and check_password_hash(admin.password, password):
        session['is_admin_logged_in'] = True
        return redirect('/admin/orders') # 登录成功直接跳到工单大屏
    else:
        return "<script>alert('账号或密码错误！'); window.location.href='/admin/login';</script>"

@app.route('/admin/logout')
def logout():
    session.pop('is_admin_logged_in', None)
    return redirect('/')

# ----------------- 核心页面路由 -----------------
@app.route('/')
def index():
    latest_news = News.query.order_by(News.id.desc()).limit(3).all()
    return render_template('index.html', latest_news=latest_news)

@app.route('/news')
def news_list():
    all_news = News.query.order_by(News.id.desc()).all()
    return render_template('news_list.html', news=all_news)

@app.route('/admin/add_news')
def add_news_form():
    return render_template('admin/add_news.html')

# ----------------- 后台工单管理路由 -----------------
@app.route('/admin/orders')
def manage_orders():
    # 1. 接收前端传来的页码，默认为第 1 页
    page = request.args.get('page', 1, type=int)
    # 2. 接收前端传来的分类标签，默认显示 '待处理'
    current_tab = request.args.get('tab', '待处理')

    # 3. 核心升级：按状态过滤 + 分页（限制每页最多查询 10 条，拒绝全表扫描崩溃）
    pagination = ServiceOrder.query.filter_by(status=current_tab)\
        .order_by(ServiceOrder.id.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    # 把分页对象和当前标签传给前端
    return render_template('admin/orders.html', pagination=pagination, current_tab=current_tab)

@app.route('/admin/complete_order/<int:order_id>')
def complete_order(order_id):
    # 处理工单：根据 ID 找到对应工单，把状态改为“已处理”
    order = ServiceOrder.query.get(order_id)
    if order:
        order.status = '已处理'
        db.session.commit()
    return redirect('/admin/orders')

@app.route('/message')
def message_list():
    all_messages = Message.query.order_by(Message.id.desc()).all()
    return render_template('message.html', messages=all_messages)

# ----------------- 便民服务静态页面 -----------------
@app.route('/service/housekeeping')
def service_housekeeping():
    return render_template('service_housekeeping.html')

@app.route('/service/courier')
def service_courier():
    return render_template('service_courier.html')

@app.route('/service/meal')
def service_meal():
    return render_template('service_meal.html')

@app.route('/service/repair')
def service_repair():
    return render_template('service_repair.html')

# ----------------- 数据提交处理 (ORM 写入) -----------------
@app.route('/admin/submit_news', methods=['POST'])
def submit_news():
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    new_item = News(title=request.form.get('title'), content=request.form.get('content'), time=now_str)
    db.session.add(new_item)
    db.session.commit()
    return redirect('/news')

@app.route('/submit_message', methods=['POST'])
def submit_message():
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    new_msg = Message(name=request.form.get('name'), content=request.form.get('content'), time=now_str)
    db.session.add(new_msg)
    db.session.commit()
    return redirect('/message')

# ----------------- 真实业务处理逻辑 -----------------
@app.route('/submit_housekeeping', methods=['POST'])
def submit_housekeeping():
    detail = f"类型: {request.form.get('service_type')} | 备注: {request.form.get('remarks', '无')}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    order = ServiceOrder(
        category='家政预约', name=request.form.get('name'), phone=request.form.get('phone'),
        detail=detail, service_date=request.form.get('service_date'), created_at=now_str
    )
    db.session.add(order)
    db.session.commit()
    return "<script>alert('家政服务预约成功！我们会尽快联系您。'); window.location.href='/service/housekeeping';</script>"

@app.route('/submit_meal', methods=['POST'])
def submit_meal():
    detail = f"套餐: {request.form.get('meal_type')} | 份数: {request.form.get('quantity')}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    order = ServiceOrder(
        category='老年餐预订', name=request.form.get('name'), phone=request.form.get('phone'),
        detail=detail, service_date=request.form.get('meal_date'), created_at=now_str
    )
    db.session.add(order)
    db.session.commit()
    return "<script>alert('订餐成功！'); window.location.href='/service/meal';</script>"

@app.route('/submit_repair', methods=['POST'])
def submit_repair():
    detail = f"家电: {request.form.get('appliance_type')} | 故障: {request.form.get('fault_description')} | 时段: {request.form.get('visit_time')}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    order = ServiceOrder(
        category='家电维修', name=request.form.get('name'), phone=request.form.get('phone'),
        detail=detail, service_date=request.form.get('visit_date'), created_at=now_str
    )
    db.session.add(order)
    db.session.commit()
    return "<script>alert('维修报修提交成功！师傅将与您联系。'); window.location.href='/service/repair';</script>"

# ----------------- 启动服务 -----------------
if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true', port=5000)