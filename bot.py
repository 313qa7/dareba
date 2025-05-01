import sqlite3
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ConversationHandler

# تفعيل التسجيل (logging) عشان نشوف المشاكل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ثابت رقم فودافون كاش ومعرف الإدارة (غير ADMIN_USER_ID للمعرف بتاعك)
VODAFONE_CASH_NUMBER = "01006311569"
ADMIN_USER_ID = 1191760477  # تم تحديث الـ ID بتاعك

# مراحل المحادثة
AMOUNT, CONFIRM, PHOTO = range(3)
DATABASE = "orders.db"

def init_db():
    """إنشاء قاعدة البيانات لو مش موجودة"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            net_balance REAL,
            total_bot REAL,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_order(user_id: int, username: str, net_balance: float, total_bot: float):
    """تسجيل الطلب في قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, username, net_balance, total_bot)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, net_balance, total_bot))
    conn.commit()
    conn.close()

def start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info(f"المستخدم {user.first_name} (ID: {user.id}) بدأ محادثة جديدة")

    # تعليق إرسال الرسائل للمسؤول مؤقتاً لحل مشكلة Chat not found
    logger.info("تم تخطي إرسال رسالة للمسؤول لتجنب خطأ Chat not found")

    # إرسال رسالة للمستخدم
    try:
        update.message.reply_text(
            "مرحبًا، اكتب لي الرصيد الصافي اللي عايز تشحنه. مثلاً: 100"
        )
        logger.info("تم إرسال رسالة الترحيب للمستخدم بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إرسال رسالة الترحيب: {e}")

    return AMOUNT

def calculate_cost(update: Update, context: CallbackContext) -> int:
    try:
        net_balance = float(update.message.text)
    except ValueError:
        update.message.reply_text("من فضلك ادخل رقم صحيح!")
        return AMOUNT

    telecom_tax_rate = 0.30  # ضريبة فودافون 30%
    bot_tax_rate = 0.15      # ضريبة البوت 15%

    total_vodafone = net_balance / (1 - telecom_tax_rate)
    total_bot = net_balance / (1 - bot_tax_rate)

    # حفظ البيانات للمستقبل
    context.user_data['net_balance'] = net_balance
    context.user_data['total_vodafone'] = total_vodafone
    context.user_data['total_bot'] = total_bot

    message = (
        f"لو الرصيد الصافي {net_balance:.2f} ج:\n"
        f"• مع فودافون كنت هتدفع {round(total_vodafone)} ج\n"
        f"• معانا هتدفع {total_bot:.2f} ج\n\n"
        "تأكد لو تحب تأكد الطلب؟"
    )

    keyboard = [
        [InlineKeyboardButton("تأكيد الطلب", callback_data='confirm')],
        [InlineKeyboardButton("إلغاء", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(message, reply_markup=reply_markup)

    return CONFIRM

def confirm_order(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == 'cancel':
        query.edit_message_text(text="تم إلغاء الطلب. ابدأ من جديد بكتابة /start")
        return ConversationHandler.END
    else:
        message = (
            f"شكرًا لتأكيد الطلب.\n\n"
            f"المبلغ المطلوب دفعه: {context.user_data['total_bot']:.2f} ج\n\n"
            f"حضرتك اتحول المبلغ على رقم فودافون كاش ده:\n{VODAFONE_CASH_NUMBER}\n\n"
            "وبعدها ابعتلنا صورة (screenshot) لعملية التحويل."
        )
        query.edit_message_text(text=message)
        return PHOTO

def photo_handler(update: Update, context: CallbackContext) -> int:
    if update.message.photo:
        # تعليق إرسال الرسائل للمسؤول مؤقتاً لحل مشكلة Chat not found
        logger.info("تم تخطي إرسال رسالة للمسؤول لتجنب خطأ Chat not found")

        # تسجيل الطلب في قاعدة البيانات
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.full_name
        net_balance = context.user_data.get('net_balance', 0)
        total_bot = context.user_data.get('total_bot', 0)

        try:
            insert_order(user_id, username, net_balance, total_bot)
            logger.info(f"تم تسجيل طلب جديد للمستخدم {username}")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء تسجيل الطلب: {e}")

        update.message.reply_text("تم استلام صورة التحويل وسجلنا الطلب، وهنتعامل معاه في أسرع وقت. شكرًا!")
        return ConversationHandler.END
    else:
        update.message.reply_text("محتاج صورة واضحة لعملية التحويل. جرب تاني.")
        return PHOTO

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("تم إلغاء العملية. ابدأ من جديد بكتابة /start")
    return ConversationHandler.END

# أوامر إدارية تقدر تضيفها لإدارة الطلبات
def list_orders(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_USER_ID:
        update.message.reply_text("مش من صلاحياتك للوصول للأمر ده!")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, username, net_balance, total_bot, status, timestamp FROM orders WHERE status = 'pending'")
    orders = cursor.fetchall()
    conn.close()

    if orders:
        msg = "الطلبات القيد التنفيذ:\n"
        for order in orders:
            msg += (f"طلب رقم: {order[0]}, المستخدم: {order[2]} (ID: {order[1]}), "
                    f"الرصيد: {order[3]} ج, المبلغ: {order[4]:.2f} ج, الحالة: {order[5]}, التاريخ: {order[6]}\n")
        update.message.reply_text(msg)
    else:
        update.message.reply_text("مش عندنا طلبات حالياً.")

def complete_order(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_USER_ID:
        update.message.reply_text("مش من صلاحياتك للوصول للأمر ده!")
        return

    args = context.args
    if not args:
        update.message.reply_text("اكتب رقم الطلب اللى عايز تعمله complete، مثلا: /complete_order 1")
        return

    order_id = args[0]
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    update.message.reply_text(f"طلب رقم {order_id} اتعلم انه مكتمل.")

def main():
    logger.info("بدء تشغيل البوت...")

    try:
        init_db()  # تهيئة قاعدة البيانات
        logger.info("تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تهيئة قاعدة البيانات: {e}")

    # تم تحديث التوكن للبوت dar117bot
    token = "7284430169:AAEwwKpd7Za4C7rNCZqz_3qNqK0Agh3M1wA"
    try:
        updater = Updater(token, use_context=True)
        dp = updater.dispatcher
        logger.info("تم إنشاء الـ Updater بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إنشاء الـ Updater: {e}")
        return

    # تعليق إرسال الرسائل للمسؤول مؤقتاً لحل مشكلة Chat not found
    logger.info("تم تخطي إرسال رسالة للمسؤول لتجنب خطأ Chat not found")

    try:
        # إضافة handler بسيط للتأكد من أن البوت يستجيب للأوامر
        def echo(update, context):
            logger.info(f"تم استلام رسالة: {update.message.text}")
            update.message.reply_text(f"أنت كتبت: {update.message.text}")

        # إضافة handler للأمر /test
        def test_command(update, context):
            logger.info("تم استلام أمر /test")
            update.message.reply_text("البوت يعمل! هذه رسالة اختبار.")

        # إضافة الـ handlers بترتيب مختلف
        dp.add_handler(CommandHandler("test", test_command))
        dp.add_handler(CommandHandler("orders", list_orders))
        dp.add_handler(CommandHandler("complete_order", complete_order, pass_args=True))

        # إضافة handler بسيط للأمر start
        dp.add_handler(CommandHandler("start", start))

        # إضافة الـ echo handler في النهاية
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
        logger.info("تم إضافة جميع الـ handlers بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إضافة الـ handlers: {e}")

    try:
        logger.info("بدء استقبال الرسائل...")
        updater.start_polling()
        logger.info("البوت يعمل الآن! اضغط Ctrl+C للإيقاف.")
        updater.idle()
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تشغيل البوت: {e}")

if __name__ == '__main__':
    main()
