from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
# import pywhatkit as kit
import time
import random
import string
import pytz
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
import urllib.parse
from admin import admin_bp, init_admin_file

# إنشاء تطبيق Flask
app = Flask(__name__)
# استخدام مفتاح سري قوي جدا للتشفير
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['SESSION_COOKIE_SECURE'] = True  # لتأمين الكوكيز
app.config['SESSION_COOKIE_HTTPONLY'] = True  # لمنع الوصول للكوكيز عبر JavaScript
app.config['SESSION_TYPE'] = 'filesystem'  # تخزين الجلسة في ملفات
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # مدة الجلسة بالثواني (ساعة واحدة)

# إعدادات البريد الإلكتروني
app.config['EMAIL_SENDER'] = 'dareba.service@outlook.com'
app.config['EMAIL_PASSWORD'] = 'Dareba123456'
app.config['NOTIFICATION_EMAIL'] = 'lahmantisho@gmail.com'  # الإيميل المستلم للإشعارات
app.config['BREVO_API_KEY'] = 'xkeysib-0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u-XYZ123'

# تعريف حدود الطلبات (بدون استخدام flask_limiter)
# يمكن تنفيذ هذا يدويًا لاحقًا إذا لزم الأمر

# وظيفة إرسال البريد الإلكتروني (باستخدام SMTP)
def send_order_email(order_details):
    try:
        # إنشاء مجلد للإشعارات إذا لم يكن موجودًا (للاحتياط)
        email_dir = 'email_notifications'
        os.makedirs(email_dir, exist_ok=True)

        # إنشاء اسم ملف فريد باستخدام الوقت الحالي
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        email_file = os.path.join(email_dir, f'order_notification_{timestamp}.txt')

        # كتابة تفاصيل الطلب في الملف (للاحتياط)
        with open(email_file, 'w', encoding='utf-8') as f:
            f.write(f"To: {app.config['NOTIFICATION_EMAIL']}\n")
            f.write(f"From: {app.config['EMAIL_SENDER']}\n")
            f.write("Subject: طلب جديد - خدمة شحن الرصيد\n")
            f.write("=" * 50 + "\n")
            f.write(order_details)

        print(f"تم حفظ إشعار البريد الإلكتروني في الملف: {email_file}")

        # إرسال البريد الإلكتروني باستخدام SMTP
        msg = MIMEMultipart()
        msg['From'] = app.config['EMAIL_SENDER']
        msg['To'] = app.config['NOTIFICATION_EMAIL']
        msg['Subject'] = "طلب جديد - خدمة شحن الرصيد"

        # إضافة محتوى الرسالة
        msg.attach(MIMEText(order_details, 'plain', 'utf-8'))

        # إعداد خادم SMTP
        try:
            # استخدام خادم Outlook
            server = smtplib.SMTP('smtp-mail.outlook.com', 587)
            server.starttls()  # تأمين الاتصال
            server.login(app.config['EMAIL_SENDER'], app.config['EMAIL_PASSWORD'])

            # إرسال البريد الإلكتروني
            server.send_message(msg)
            server.quit()

            print("تم إرسال البريد الإلكتروني بنجاح!")
            return True
        except Exception as smtp_error:
            print(f"حدث خطأ أثناء إرسال البريد الإلكتروني: {str(smtp_error)}")
            print("تم حفظ تفاصيل الطلب في ملف نصي كاحتياط.")
            return False

    except Exception as e:
        print(f"حدث خطأ عام: {str(e)}")
        return False

# التأكد من وجود مجلد الرفع
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# إنشاء قاعدة البيانات
db = SQLAlchemy(app)

# نموذج الطلبات
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    user_phone = db.Column(db.String(20), nullable=False)
    net_balance = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    receipt_image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.UTC).astimezone(pytz.timezone('Africa/Cairo')).replace(hour=(datetime.now(pytz.timezone('Africa/Cairo')).hour - 1) % 24))

    def __repr__(self):
        return f'<Order {self.id}>'

# ثوابت
VODAFONE_CASH_NUMBER = "01012874414"
WHATSAPP_NUMBER = "+201012874414"
TELECOM_TAX_RATE = 0.4285714285714  # ضريبة فودافون 43% (القيمة الفعلية 42.85714285714%)
BOT_TAX_RATE = 0.22      # ضريبة البوت 22%

# الصفحة الرئيسية
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            net_balance = float(request.form['net_balance'])

            # التحقق من أن الرصيد لا يقل عن 50 جنيه
            if net_balance < 50:
                flash('أقل قيمة لشحن رصيد صافي هي 50 جنيه!', 'danger')
                return render_template('index.html')

            # حساب التكلفة
            # المعادلة الجديدة: الرصيد الصافي + (الرصيد الصافي × نسبة الضريبة)
            total_vodafone = net_balance + (net_balance * TELECOM_TAX_RATE)
            # تقريب التكلفة بتاعتنا لأقرب رقم صحيح
            total_bot_exact = net_balance + (net_balance * BOT_TAX_RATE)
            total_bot = round(total_bot_exact)

            # حفظ البيانات في الجلسة
            session['net_balance'] = net_balance
            session['total_vodafone'] = total_vodafone
            session['total_bot'] = total_bot

            return redirect(url_for('confirm'))
        except ValueError:
            flash('من فضلك أدخل رقم صحيح!', 'danger')

    return render_template('index.html')

# صفحة تأكيد الطلب
@app.route('/confirm', methods=['GET', 'POST'])
def confirm():
    if 'net_balance' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        print("تم استلام طلب POST في صفحة التأكيد")
        user_name = request.form['user_name']
        user_phone = request.form['user_phone']
        print(f"اسم المستخدم: {user_name}, رقم الهاتف: {user_phone}")

        # إنشاء طلب جديد
        new_order = Order(
            user_name=user_name,
            user_phone=user_phone,
            net_balance=session['net_balance'],
            total_cost=session['total_bot']
        )

        db.session.add(new_order)
        db.session.commit()
        print(f"تم إنشاء طلب جديد برقم: {new_order.id}")

        # تجهيز رسالة واتساب
        # تحويل الوقت إلى توقيت القاهرة بنظام 12 ساعة
        utc_now = datetime.now(pytz.UTC)
        cairo_time = utc_now.astimezone(pytz.timezone('Africa/Cairo'))
        formatted_time = cairo_time.strftime('%I:%M:%S %p %d/%m/%Y')  # نظام 12 ساعة مع AM/PM

        # إنشاء نص الرسالة
        message = (
            f"طلب جديد!\n"
            f"رقم الطلب: {new_order.id}\n"
            f"الاسم: {user_name}\n"
            f"رقم الهاتف الذي سيصل إليه الرصيد: {user_phone}\n"
            f"الرصيد المطلوب: {session['net_balance']} ج\n"
            f"المبلغ المطلوب دفعه: {session['total_bot']:.0f} ج\n"
            f"الوقت: {formatted_time}"
        )

        print(f"تم إنشاء رسالة واتساب: {message}")

        # إرسال تفاصيل الطلب بالبريد الإلكتروني
        print("جاري إرسال البريد الإلكتروني...")
        try:
            email_result = send_order_email(message)
            print(f"نتيجة إرسال البريد الإلكتروني: {email_result}")
        except Exception as e:
            print(f"حدث خطأ أثناء إرسال البريد الإلكتروني: {str(e)}")

        # حفظ الرسالة في ملف مؤقت
        # إنشاء مجلد للملفات المؤقتة إذا لم يكن موجوداً
        temp_dir = 'temp_messages'
        os.makedirs(temp_dir, exist_ok=True)

        # إنشاء اسم ملف فريد باستخدام رقم الطلب
        message_file = os.path.join(temp_dir, f'order_{new_order.id}.txt')

        # كتابة الرسالة في الملف
        try:
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(message)
            print(f"تم حفظ رسالة الواتساب في الملف: {message_file}")
        except Exception as e:
            print(f"حدث خطأ أثناء حفظ ملف الرسالة: {str(e)}")

        # تخزين رقم الطلب والرسالة في الجلسة
        session['order_id'] = new_order.id
        session['whatsapp_message'] = message  # تخزين الرسالة مباشرة في الجلسة كاحتياط

        # توجيه المستخدم إلى صفحة الشكر
        return redirect(url_for('thank_you'))

    return render_template('confirm.html',
                          net_balance=session['net_balance'],
                          total_vodafone=session['total_vodafone'],
                          total_bot=session['total_bot'],
                          vodafone_cash=VODAFONE_CASH_NUMBER)



# صفحة الشكر
@app.route('/thank_you')
def thank_you():
    # الحصول على رقم الطلب من الجلسة
    order_id = session.get('order_id')

    # محاولة الحصول على الرسالة مباشرة من الجلسة (الطريقة الاحتياطية)
    whatsapp_message = session.get('whatsapp_message', "طلب جديد! لم يتم العثور على تفاصيل الطلب.")

    # طباعة محتويات الجلسة للتشخيص
    print(f"محتويات الجلسة: {dict(session)}")

    if order_id:
        print(f"تم العثور على رقم الطلب في الجلسة: {order_id}")

        # محاولة قراءة الرسالة من الملف
        temp_dir = 'temp_messages'
        message_file = os.path.join(temp_dir, f'order_{order_id}.txt')

        try:
            if os.path.exists(message_file):
                with open(message_file, 'r', encoding='utf-8') as f:
                    file_message = f.read()
                    if file_message.strip():  # التأكد من أن الرسالة ليست فارغة
                        whatsapp_message = file_message
                print(f"تم قراءة رسالة الواتساب من الملف: {message_file}")
            else:
                print(f"ملف الرسالة غير موجود: {message_file}")
                # إذا كانت الرسالة موجودة في الجلسة، نحاول إعادة إنشاء الملف
                if 'whatsapp_message' in session and session['whatsapp_message']:
                    try:
                        os.makedirs(temp_dir, exist_ok=True)
                        with open(message_file, 'w', encoding='utf-8') as f:
                            f.write(session['whatsapp_message'])
                        print(f"تم إعادة إنشاء ملف الرسالة من الجلسة: {message_file}")
                    except Exception as e:
                        print(f"فشل إعادة إنشاء ملف الرسالة: {str(e)}")
        except Exception as e:
            print(f"حدث خطأ أثناء قراءة ملف الرسالة: {str(e)}")
            # استخدام الرسالة من الجلسة كاحتياط
            if 'whatsapp_message' in session and session['whatsapp_message']:
                whatsapp_message = session['whatsapp_message']
                print("تم استخدام الرسالة من الجلسة كاحتياط")
    else:
        print("لم يتم العثور على رقم الطلب في الجلسة")

    # طباعة رسالة الواتساب للتأكد من وجودها
    print(f"رسالة الواتساب في صفحة الشكر: {whatsapp_message}")

    # تشفير الرسالة لاستخدامها في رابط الواتساب
    encoded_message = urllib.parse.quote(whatsapp_message)

    # إنشاء روابط الواتساب (نستخدم عدة صيغ للتوافق مع مختلف الأجهزة)
    whatsapp_url = f"https://api.whatsapp.com/send?phone=201012874414&text={encoded_message}"
    whatsapp_url_alt = f"https://wa.me/201012874414?text={encoded_message}"

    # تمرير المعلومات إلى القالب
    return render_template('thank_you.html',
                          whatsapp_url=whatsapp_url,
                          whatsapp_url_alt=whatsapp_url_alt,
                          whatsapp_message=whatsapp_message)

# تسجيل صفحات الأدمن
app.register_blueprint(admin_bp, url_prefix='/admin')

# إنشاء ملف بيانات الأدمن إذا لم يكن موجودًا
init_admin_file()

# صفحة الأوامر - محمية بكلمة مرور
@app.route('/orders')
def orders():
    # التحقق من تسجيل دخول الأدمن
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash('لازم تسجل دخول الأول', 'danger')
        return redirect(url_for('admin.login'))

    # جلب جميع الطلبات
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=all_orders)

# صفحة الخطأ 404
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.html'), 404

# صفحة الخطأ 500
@app.errorhandler(500)
def server_error(_):
    return render_template('500.html'), 500

# صفحة sitemap.xml
@app.route('/sitemap.xml')
def sitemap():
    return app.send_static_file('sitemap.xml'), 200, {'Content-Type': 'application/xml'}

# صفحة robots.txt
@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt'), 200, {'Content-Type': 'text/plain'}

# إنشاء قاعدة البيانات عند بدء التطبيق
with app.app_context():
    db.create_all()

# تشغيل التطبيق
if __name__ == '__main__':
    # تفعيل وضع التصحيح للتطوير المحلي فقط
    app.run(debug=True, port=5001, host='0.0.0.0')
