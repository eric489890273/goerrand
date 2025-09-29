from datetime import datetime
from flask import Flask, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Case, CaseUpdate
from flask import render_template
from flask import redirect, url_for

# 對照表
STATUS_MAP = {
    "pending": "待處理",
    "accepted": "已接取",
    "in_progress": "進行中",
    "delivered": "已送達",
    "done": "已完成"
}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cases.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "secret_key"

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

with app.app_context():
    db.create_all()


## 功能
# 登入
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 註冊
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400
    user = User(username=data["username"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered!"})

# 登入
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401
    login_user(user)
    return jsonify({"message": f"Logged in as {user.username}", "role": user.role})

# 登出
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))  # 登出後導向登入頁

# 建立案件（客戶）
@app.route("/create_case", methods=["POST"])
@login_required
def create_case():
    data = request.json

    case = Case(
        document_name=data.get("document_name"),
        delivery_target=data["delivery_target"],
        given_location=data["given_location"],
        given_to_staff_time=datetime.fromisoformat(data["given_to_staff_time"]),
        note=data.get("note"),   # ✅ 新增
        status="pending",
        user_id=current_user.id
    )
    db.session.add(case)
    db.session.commit()

    return jsonify({"message": "案件建立成功！", "case_id": case.id})


# 查看自己的案件（客戶）
@app.route("/cases")
@login_required
def get_cases():
    cases = Case.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            "id": c.id,
            "document_name": c.document_name,
            "delivery_target": c.delivery_target,
            "given_location": c.given_location,
            "given_to_staff_time": c.given_to_staff_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": STATUS_MAP.get(c.status, c.status),
            "note": c.note or ""   # ✅ 把 note 加回來
        }
        for c in cases
    ])

# 查看所有案件（僅 staff）
@app.route("/all_cases")
@login_required
def all_cases():
    if current_user.role != "staff":
        return jsonify({"error": "Access denied"}), 403

    cases = Case.query.all()
    result = []
    for c in cases:
        updates = [
            {
                "status": u.status,
                "note": u.note,
                "location": u.location,
                "time": u.update_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            for u in CaseUpdate.query.filter_by(case_id=c.id).order_by(CaseUpdate.update_time)
        ]

        result.append({
            "id": c.id,
            "document_name": c.document_name,
            "delivery_target": c.delivery_target,
            "given_location": c.given_location,
            "given_to_staff_time": c.given_to_staff_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": STATUS_MAP.get(c.status, c.status),
            "note": c.note or "",
            "user_id": c.user_id,
            "updates": updates
        })

    return jsonify(result)

# 取得待接案件（員工專用）
@app.route("/pending_cases")
@login_required
def pending_cases():
    if current_user.role != "staff":
        return jsonify({"error": "Access denied"}), 403

    cases = Case.query.filter_by(status="pending").all()
    result = [
        {
            "id": c.id,
            "document_name": c.document_name,
            "delivery_target": c.delivery_target,
            "given_location": c.given_location,
            "given_to_staff_time": c.given_to_staff_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": STATUS_MAP.get(c.status, c.status),
            "user_id": c.user_id,
            "note": c.note or ""
        }
        for c in cases
    ]
    return jsonify(result)

# 員工更新自己已接案件進度
@app.route("/update_taken_case/<int:case_id>", methods=["POST"])
@login_required
def update_taken_case(case_id):
    if current_user.role != "staff":
        return jsonify({"error": "Access denied"}), 403

    data = request.json
    case = Case.query.get(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404

    # ❌ 如果案件已完成，不允許修改
    if case.status == "done":
        return jsonify({"error": "此案件已完成，不可再修改"}), 400

    # 更新案件主表狀態
    new_status = data.get("status")
    if new_status:
        case.status = new_status

    # 新增歷程紀錄
    case_update = CaseUpdate(
        case_id=case.id,
        status=new_status or case.status,
        note=data.get("note"),
        location=data.get("location"),
        update_time=datetime.utcnow()
    )
    db.session.add(case_update)
    db.session.commit()

    return jsonify({"message": "Case progress updated"})

# 檢查使用者名稱是否存在
@app.route("/check_username/<username>")
def check_username(username):
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({"exists": exists})

# 取得員工已接案件
@app.route("/my_taken_cases")
@login_required
def my_taken_cases():
    if current_user.role != "staff":
        return jsonify({"error": "Access denied"}), 403

    cases = Case.query.filter(Case.status != "pending").all()
    result = []
    for c in cases:
        updates = [
            {
                "status": u.status,
                "note": u.note,
                "location": u.location,
                "time": u.update_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            for u in CaseUpdate.query.filter_by(case_id=c.id).order_by(CaseUpdate.update_time)
        ]
        result.append({
            "id": c.id,
            "document_name": c.document_name,
            "delivery_target": c.delivery_target,
            "given_location": c.given_location,
            "given_to_staff_time": c.given_to_staff_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": STATUS_MAP.get(c.status, c.status),
            "note": c.note or "",
            "updates": updates
        })
    return jsonify(result)

## 路徑
# 根目錄
@app.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login_page"))  # 未登入導向登入頁
    return render_template("index.html")       # 已登入導向首頁

# 登入頁面
@app.route("/login_page")
def login_page():
    return render_template("login.html")

# 註冊頁面
@app.route("/register_page")
def register_page():
    return render_template("register.html")

# 建立案件頁面
@app.route("/create_case_page")
@login_required
def create_case_page():
    return render_template("create_case.html")

# 案件進度頁面
@app.route("/my_cases_page")
@login_required
def my_cases_page():
    return render_template("my_cases.html")

# 全案件頁面(員工)
@app.route("/all_cases_page")
@login_required
def all_cases_page():
    if current_user.role != "staff":
        return "Access denied", 403
    return render_template("all_cases.html")

# 個人資料頁面
@app.route("/profile_page")
@login_required
def profile_page():
    return render_template("profile.html")

# 接取案件頁面
@app.route("/take_case_page")
@login_required
def take_case_page():
    if current_user.role != "staff":
        return "Access denied", 403
    return render_template("take_case_page.html")


with app.app_context():
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin")
        admin.set_password("1234")
        admin.role = "staff"
        db.session.add(admin)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
