#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки GTA5 RP Calculator
"""

import sys
import os
import traceback

def test_imports():
    """Тестирует импорты всех модулей"""
    print("🔧 Тестирование импортов...")
    
    try:
        import tkinter as tk
        print("✅ tkinter импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта tkinter: {e}")
        return False
    
    try:
        from mobile_interface import MobileInterface
        print("✅ MobileInterface импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта MobileInterface: {e}")
        return False
    
    try:
        from qr_generator import QRCodeGenerator
        print("✅ QRCodeGenerator импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта QRCodeGenerator: {e}")
        return False
    
    try:
        import flask
        print("✅ Flask импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта Flask: {e}")
        return False
    
    try:
        import qrcode
        print("✅ qrcode импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта qrcode: {e}")
        return False
    
    try:
        from PIL import Image
        print("✅ PIL импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта PIL: {e}")
        return False
    
    return True

def test_files():
    """Тестирует наличие необходимых файлов"""
    print("\n🔍 Тестирование файлов...")
    
    required_files = [
        "gta5_rp_calculator17.py",
        "mobile_interface.py", 
        "qr_generator.py",
        "items.csv",
        "requirements.txt"
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} найден")
        else:
            print(f"❌ {file} не найден")
            all_exist = False
    
    return all_exist

def test_syntax():
    """Тестирует синтаксис основного файла"""
    print("\n🔍 Тестирование синтаксиса...")
    
    try:
        with open("gta5_rp_calculator17.py", "r", encoding="utf-8") as f:
            code = f.read()
        
        compile(code, "gta5_rp_calculator17.py", "exec")
        print("✅ Синтаксис основного файла корректен")
        return True
    except SyntaxError as e:
        print(f"❌ Синтаксическая ошибка: {e}")
        print(f"   Строка {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Ошибка компиляции: {e}")
        return False

def test_mobile_interface():
    """Тестирует мобильный интерфейс"""
    print("\n📱 Тестирование мобильного интерфейса...")
    
    try:
        from mobile_interface import MobileInterface
        mobile = MobileInterface()
        print("✅ MobileInterface создан успешно")
        
        # Проверяем основные методы
        deals = mobile.load_deals()
        print(f"✅ Загрузка сделок: {len(deals)} записей")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в мобильном интерфейсе: {e}")
        return False

def test_qr_generator():
    """Тестирует генератор QR-кодов"""
    print("\n🔍 Тестирование генератора QR-кодов...")
    
    try:
        from qr_generator import QRCodeGenerator
        # Не создаем GUI для теста, только проверяем импорт
        print("✅ QRCodeGenerator импортирован успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка в генераторе QR-кодов: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования GTA5 RP Calculator")
    print("=" * 50)
    
    # Тестируем файлы
    files_ok = test_files()
    
    # Тестируем импорты
    imports_ok = test_imports()
    
    # Тестируем синтаксис
    syntax_ok = test_syntax()
    
    # Тестируем мобильный интерфейс
    mobile_ok = test_mobile_interface()
    
    # Тестируем генератор QR-кодов
    qr_ok = test_qr_generator()
    
    print("\n" + "=" * 50)
    print("📊 Результаты тестирования:")
    print(f"   Файлы: {'✅ OK' if files_ok else '❌ ОШИБКИ'}")
    print(f"   Импорты: {'✅ OK' if imports_ok else '❌ ОШИБКИ'}")
    print(f"   Синтаксис: {'✅ OK' if syntax_ok else '❌ ОШИБКИ'}")
    print(f"   Мобильный интерфейс: {'✅ OK' if mobile_ok else '❌ ОШИБКИ'}")
    print(f"   QR-генератор: {'✅ OK' if qr_ok else '❌ ОШИБКИ'}")
    
    if files_ok and imports_ok and syntax_ok and mobile_ok and qr_ok:
        print("\n🎉 Все тесты пройдены! Приложение готово к запуску.")
        print("\n📋 Инструкции по запуску:")
        print("   1. Установите зависимости: pip install -r requirements.txt")
        print("   2. Запустите приложение: python gta5_rp_calculator17.py")
        return True
    else:
        print("\n⚠️ Обнаружены проблемы. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
