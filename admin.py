from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
import hashlib
import os
import json

admin_bp = Blueprint('admin', __name__)

# هنا هنخزن بيانات الأدمن في ملف خارجي عشان الأمان
ADMIN_FILE = 'admin_data.json'

# دالة لإنشاء ملف الأدمن لو مش موجود
def init_admin_file():
    if not os.path.exists(ADMIN_FILE):
        # كلمة المرور الافتراضية هتكون "admin123" وهنخزنها مشفرة
        default_password = hashlib.sha256("admin123".encode()).hexdigest()
        admin_data = {
            "username": "admin",
            "password": default_password
        }
        with open(ADMIN_FILE, 'w') as f:
            json.dump(admin_data, f)

# دالة للتحقق من تسجيل دخول الأدمن
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('لازم تسجل دخول الأول', 'danger')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

# صفحة تسجيل الدخول
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # هنتأكد من وجود ملف الأدمن
        if not os.path.exists(ADMIN_FILE):
            init_admin_file()
            
        # هنقرأ بيانات الأدمن
        with open(ADMIN_FILE, 'r') as f:
            admin_data = json.load(f)
            
        # هنشفر كلمة المرور المدخلة للمقارنة
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        if username == admin_data['username'] and hashed_password == admin_data['password']:
            session['admin_logged_in'] = True
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غلط', 'danger')
            
    return render_template('admin/login.html')

# صفحة لوحة التحكم
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

# صفحة تغيير كلمة المرور
@admin_bp.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # هنقرأ بيانات الأدمن
        with open(ADMIN_FILE, 'r') as f:
            admin_data = json.load(f)
            
        # هنشفر كلمة المرور القديمة للمقارنة
        hashed_old_password = hashlib.sha256(old_password.encode()).hexdigest()
        
        if hashed_old_password != admin_data['password']:
            flash('كلمة المرور القديمة غلط', 'danger')
        elif new_password != confirm_password:
            flash('كلمة المرور الجديدة مش متطابقة', 'danger')
        elif len(new_password) < 8:
            flash('كلمة المرور لازم تكون 8 حروف على الأقل', 'danger')
        else:
            # هنشفر كلمة المرور الجديدة ونحفظها
            hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()
            admin_data['password'] = hashed_new_password
            
            with open(ADMIN_FILE, 'w') as f:
                json.dump(admin_data, f)
                
            flash('تم تغيير كلمة المرور بنجاح', 'success')
            return redirect(url_for('admin.dashboard'))
            
    return render_template('admin/change_password.html')

# تسجيل الخروج
@admin_bp.route('/logout')
@admin_required
def logout():
    session.pop('admin_logged_in', None)
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('admin.login'))
