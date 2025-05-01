import os
import hashlib
import json
import time
import datetime

# قائمة الملفات المهمة التي يجب مراقبتها
IMPORTANT_FILES = [
    'app.py',
    'admin.py',
    'templates/index.html',
    'templates/confirm.html',
    'templates/thank_you.html',
    'templates/admin/login.html',
    'templates/admin/dashboard.html',
    'templates/admin/change_password.html',
    'templates/orders.html',
    'static/css/style.css'
]

# ملف لتخزين البصمات الرقمية للملفات
CHECKSUMS_FILE = 'file_checksums.json'

def calculate_file_hash(file_path):
    """حساب البصمة الرقمية للملف باستخدام SHA-256"""
    if not os.path.exists(file_path):
        return None
        
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            # قراءة الملف بأجزاء لتوفير الذاكرة
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"خطأ في حساب البصمة الرقمية للملف {file_path}: {e}")
        return None

def save_checksums():
    """حفظ البصمات الرقمية للملفات المهمة"""
    checksums = {}
    
    for file_path in IMPORTANT_FILES:
        file_hash = calculate_file_hash(file_path)
        if file_hash:
            checksums[file_path] = file_hash
    
    with open(CHECKSUMS_FILE, 'w') as f:
        json.dump(checksums, f, indent=4)
    
    print(f"تم حفظ البصمات الرقمية للملفات في {CHECKSUMS_FILE}")

def verify_checksums():
    """التحقق من البصمات الرقمية للملفات المهمة"""
    if not os.path.exists(CHECKSUMS_FILE):
        print("ملف البصمات الرقمية غير موجود. سيتم إنشاؤه الآن.")
        save_checksums()
        return True
    
    try:
        with open(CHECKSUMS_FILE, 'r') as f:
            saved_checksums = json.load(f)
    except Exception as e:
        print(f"خطأ في قراءة ملف البصمات الرقمية: {e}")
        return False
    
    modified_files = []
    
    for file_path in IMPORTANT_FILES:
        current_hash = calculate_file_hash(file_path)
        
        if file_path not in saved_checksums:
            print(f"ملف جديد تمت إضافته: {file_path}")
            modified_files.append(file_path)
        elif current_hash != saved_checksums[file_path]:
            print(f"تم تعديل الملف: {file_path}")
            modified_files.append(file_path)
    
    if modified_files:
        print("تم العثور على ملفات معدلة:")
        for file in modified_files:
            print(f"- {file}")
        
        # يمكن إضافة إرسال إشعار للمسؤول هنا
        
        return False
    else:
        print("جميع الملفات سليمة ولم يتم العبث بها.")
        return True

def log_security_check():
    """تسجيل عملية التحقق من الأمان"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("security_log.txt", "a") as f:
        f.write(f"{timestamp} - تم إجراء فحص أمني للملفات\n")

if __name__ == "__main__":
    print("بدء فحص أمان الملفات...")
    result = verify_checksums()
    log_security_check()
    
    if result:
        print("تم الانتهاء من الفحص بنجاح. جميع الملفات آمنة.")
    else:
        print("انتبه! تم العثور على تغييرات في الملفات المهمة.")
        
        # تحديث البصمات الرقمية بعد التحقق منها يدويًا
        update = input("هل تريد تحديث البصمات الرقمية؟ (نعم/لا): ")
        if update.lower() in ['نعم', 'y', 'yes']:
            save_checksums()
            print("تم تحديث البصمات الرقمية.")
