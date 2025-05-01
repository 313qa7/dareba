import os
import shutil
import datetime
import sqlite3
import time

# المجلد الذي سيتم حفظ النسخ الاحتياطية فيه
BACKUP_DIR = 'backups'

# التأكد من وجود مجلد النسخ الاحتياطية
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def create_backup():
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    # الحصول على التاريخ والوقت الحالي
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    
    # اسم ملف النسخة الاحتياطية
    backup_file = os.path.join(BACKUP_DIR, f'orders_backup_{timestamp}.db')
    
    try:
        # التأكد من إغلاق جميع الاتصالات بقاعدة البيانات
        time.sleep(1)
        
        # نسخ ملف قاعدة البيانات
        shutil.copy2('orders.db', backup_file)
        
        print(f'تم إنشاء نسخة احتياطية بنجاح: {backup_file}')
        
        # حذف النسخ الاحتياطية القديمة (الاحتفاظ بآخر 10 نسخ فقط)
        cleanup_old_backups()
        
        return True
    except Exception as e:
        print(f'حدث خطأ أثناء إنشاء النسخة الاحتياطية: {e}')
        return False

def cleanup_old_backups():
    """حذف النسخ الاحتياطية القديمة والاحتفاظ بآخر 10 نسخ فقط"""
    # الحصول على قائمة بجميع ملفات النسخ الاحتياطية
    backup_files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.startswith('orders_backup_') and f.endswith('.db')]
    
    # ترتيب الملفات حسب تاريخ التعديل (الأقدم أولاً)
    backup_files.sort(key=lambda x: os.path.getmtime(x))
    
    # حذف النسخ القديمة إذا كان عدد النسخ أكثر من 10
    if len(backup_files) > 10:
        for old_file in backup_files[:-10]:
            try:
                os.remove(old_file)
                print(f'تم حذف النسخة الاحتياطية القديمة: {old_file}')
            except Exception as e:
                print(f'حدث خطأ أثناء حذف النسخة الاحتياطية القديمة: {e}')

if __name__ == '__main__':
    create_backup()
