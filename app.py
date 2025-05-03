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

# إنشاء المجلدات الضرورية
os.makedirs('temp_messages', exist_ok=True)  # مجلد رسائل الطلبات المؤقتة
os.makedirs('email_notifications', exist_ok=True)  # مجلد إشعارات البريد الإلكتروني

# إعدادات البريد الإلكتروني
app.config['EMAIL_SENDER'] = 'dareba.service@gmail.com'
app.config['EMAIL_PASSWORD'] = 'rvxs zcxl rvxs zcxl'  # كلمة مرور التطبيق لـ Gmail
app.config['NOTIFICATION_EMAIL'] = 'lahmantisho@gmail.com'  # الإيميل المستلم للإشعارات

# تعريف حدود الطلبات (بدون استخدام flask_limiter)
# يمكن تنفيذ هذا يدويًا لاحقًا إذا لزم الأمر

# وظيفة إرسال البريد الإلكتروني (باستخدام SMTP أو API)
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

        # تقسيم الرسالة إلى أسطر
        lines = order_details.split('\n')

        # إنشاء محتوى HTML منظم
        formatted_content = ""
        for line in lines:
            if line.startswith("طلب جديد!"):
                formatted_content += f'<div class="order-item order-title">{line}</div>'
            elif ":" in line:
                # تقسيم السطر إلى عنوان وقيمة
                parts = line.split(":", 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    formatted_content += f'<div class="order-item"><strong>{label}:</strong> {value}</div>'
            else:
                # إذا لم يكن هناك ":" في السطر، أضفه كما هو
                if line.strip():  # تجاهل الأسطر الفارغة
                    formatted_content += f'<div class="order-item">{line}</div>'

        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; text-align: right; }}
                .order-details {{ background-color: #f9f9f9; padding: 20px; border-radius: 8px; border: 1px solid #ddd; max-width: 600px; margin: 0 auto; }}
                .order-title {{ color: #28a745; font-size: 22px; font-weight: bold; margin-bottom: 15px; }}
                .order-item {{ margin-bottom: 10px; font-size: 16px; }}
                .footer {{ margin-top: 20px; font-size: 14px; color: #777; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="order-details">
                {formatted_content}
                <div class="footer">
                    <p>خدمة شحن الرصيد - dareba.onrender.com</p>
                </div>
            </div>
        </body>
        </html>
        """

        # محاولة إرسال البريد الإلكتروني باستخدام SMTP
        try:
            # إرسال البريد الإلكتروني باستخدام SMTP
            msg = MIMEMultipart()
            msg['From'] = app.config['EMAIL_SENDER']
            msg['To'] = app.config['NOTIFICATION_EMAIL']
            msg['Subject'] = "طلب جديد - خدمة شحن الرصيد"

            # إضافة نسخة HTML ونسخة نصية للبريد
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            # إضافة نسخة نصية كاحتياط للعملاء الذين لا يدعمون HTML
            msg.attach(MIMEText(order_details, 'plain', 'utf-8'))

            # استخدام خادم Gmail
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()  # تأمين الاتصال
            server.login(app.config['EMAIL_SENDER'], app.config['EMAIL_PASSWORD'])

            # إرسال البريد الإلكتروني
            server.send_message(msg)
            server.quit()

            print("تم إرسال البريد الإلكتروني بنجاح عبر SMTP!")
            return True
        except Exception as smtp_error:
            print(f"حدث خطأ أثناء إرسال البريد الإلكتروني عبر SMTP: {str(smtp_error)}")

            # محاولة إرسال البريد الإلكتروني باستخدام API
            try:
                # استخدام طريقة بديلة - إرسال البريد الإلكتروني باستخدام API
                url = "https://api.emailjs.com/api/v1.0/email/send"
                payload = {
                    "service_id": "service_dareba",
                    "template_id": "template_order",
                    "user_id": "user_dareba",
                    "template_params": {
                        "to_email": app.config['NOTIFICATION_EMAIL'],
                        "subject": "طلب جديد - خدمة شحن الرصيد",
                        "message": order_details.replace("\n", "<br>")
                    }
                }
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    print("تم إرسال البريد الإلكتروني بنجاح عبر API!")
                    return True
                else:
                    print(f"فشل إرسال البريد الإلكتروني عبر API: {response.text}")
                    print("تم حفظ تفاصيل الطلب في ملف نصي كاحتياط.")
                    return False
            except Exception as api_error:
                print(f"حدث خطأ أثناء إرسال البريد الإلكتروني عبر API: {str(api_error)}")
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
    created_at = db.Column(db.DateTime, default=datetime.now)

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
    # حساب عدد الطلبات التي تمت
    total_orders = Order.query.count()

    if request.method == 'POST':
        try:
            # طباعة البيانات المستلمة للتشخيص
            print(f"بيانات النموذج المستلمة: {request.form}")

            # التحقق من وجود قيمة الرصيد
            if 'net_balance' not in request.form or not request.form['net_balance']:
                flash('من فضلك أدخل قيمة الرصيد الصافي', 'danger')
                return render_template('index.html', total_orders=total_orders)

            # تنظيف القيمة المدخلة والتأكد من أنها رقمية
            net_balance_str = request.form['net_balance'].strip()
            if not net_balance_str.isdigit():
                flash('من فضلك أدخل رقم صحيح فقط!', 'danger')
                return render_template('index.html', total_orders=total_orders)

            net_balance = float(net_balance_str)

            # التحقق من أن الرصيد لا يقل عن 20 جنيه
            if net_balance < 20:
                flash('أقل قيمة لشحن رصيد صافي هي 20 جنيه!', 'danger')
                return render_template('index.html', total_orders=total_orders)

            # حساب التكلفة
            # المعادلة الجديدة: الرصيد الصافي + (الرصيد الصافي × نسبة الضريبة)
            total_vodafone = net_balance + (net_balance * TELECOM_TAX_RATE)
            # تقريب التكلفة بتاعتنا لأقرب رقم صحيح
            total_bot_exact = net_balance + (net_balance * BOT_TAX_RATE)
            total_bot = round(total_bot_exact)

            print(f"تم حساب التكلفة: الرصيد={net_balance}, التكلفة={total_bot}")

            # حفظ البيانات في الجلسة
            session['net_balance'] = net_balance
            session['total_vodafone'] = total_vodafone
            session['total_bot'] = total_bot

            # تعيين الجلسة كدائمة لتجنب فقدان البيانات
            session.permanent = True

            print("تم حفظ البيانات في الجلسة، جاري التوجيه إلى صفحة التأكيد")
            return redirect(url_for('confirm'))
        except Exception as e:
            print(f"حدث خطأ أثناء معالجة النموذج: {str(e)}")
            flash('حدث خطأ أثناء معالجة طلبك. من فضلك حاول مرة أخرى.', 'danger')

    return render_template('index.html', total_orders=total_orders)

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
        # تم إزالة الوقت من رسالة تفاصيل الطلب

        # إنشاء نص الرسالة بدون الوقت
        message = (
            f"طلب جديد!\n"
            f"رقم الطلب: {new_order.id}\n"
            f"الاسم: {user_name}\n"
            f"رقم الهاتف الذي سيصل إليه الرصيد: {user_phone}\n"
            f"الرصيد المطلوب: {session['net_balance']} ج\n"
            f"المبلغ المطلوب دفعه: {session['total_bot']:.0f} ج"
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

        # محاولة استرجاع آخر طلب من قاعدة البيانات كاحتياط إضافي
        try:
            last_order = Order.query.order_by(Order.id.desc()).first()
            if last_order:
                print(f"تم العثور على آخر طلب في قاعدة البيانات برقم: {last_order.id}")
                # إنشاء رسالة واتساب من بيانات الطلب
                # تم إزالة الوقت من رسالة تفاصيل الطلب

                # إنشاء نص الرسالة بدون الوقت
                recovered_message = (
                    f"طلب جديد!\n"
                    f"رقم الطلب: {last_order.id}\n"
                    f"الاسم: {last_order.user_name}\n"
                    f"رقم الهاتف الذي سيصل إليه الرصيد: {last_order.user_phone}\n"
                    f"الرصيد المطلوب: {last_order.net_balance} ج\n"
                    f"المبلغ المطلوب دفعه: {last_order.total_cost:.0f} ج"
                )

                whatsapp_message = recovered_message
                print("تم استرجاع رسالة الواتساب من قاعدة البيانات")

                # حفظ الرسالة في الجلسة وفي ملف
                session['order_id'] = last_order.id
                session['whatsapp_message'] = whatsapp_message

                # حفظ الرسالة في ملف
                try:
                    temp_dir = 'temp_messages'
                    message_file = os.path.join(temp_dir, f'order_{last_order.id}.txt')
                    with open(message_file, 'w', encoding='utf-8') as f:
                        f.write(whatsapp_message)
                    print(f"تم حفظ الرسالة المسترجعة في الملف: {message_file}")
                except Exception as e:
                    print(f"فشل حفظ الرسالة المسترجعة في ملف: {str(e)}")
        except Exception as e:
            print(f"فشل استرجاع آخر طلب من قاعدة البيانات: {str(e)}")

    # طباعة رسالة الواتساب للتأكد من وجودها
    print(f"رسالة الواتساب في صفحة الشكر: {whatsapp_message}")

    # إزالة سطر الوقت من الرسالة إذا كان موجودًا
    if "الوقت:" in whatsapp_message:
        whatsapp_message = '\n'.join([line for line in whatsapp_message.split('\n') if not line.startswith("الوقت:")])
        print("تم إزالة سطر الوقت من الرسالة")

    # طباعة الرسالة بتنسيق مناسب للتشخيص
    formatted_message = whatsapp_message.replace('\n', '\\n')
    print(f"الرسالة المنسقة: {formatted_message}")

    # تشفير الرسالة لاستخدامها في رابط الواتساب
    encoded_message = urllib.parse.quote(whatsapp_message)

    # طباعة الرسالة المشفرة للتشخيص
    print(f"الرسالة المشفرة: {encoded_message}")

    # إنشاء روابط الواتساب (نستخدم عدة صيغ للتوافق مع مختلف الأجهزة)
    whatsapp_url = f"https://api.whatsapp.com/send?phone=201012874414&text={encoded_message}"
    whatsapp_url_alt = f"https://wa.me/201012874414?text={encoded_message}"

    # طباعة الروابط للتشخيص
    print(f"رابط الواتساب الأساسي: {whatsapp_url_alt}")
    print(f"رابط الواتساب الاحتياطي: {whatsapp_url}")

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
    app.run(debug=True, port=8080, host='0.0.0.0')
