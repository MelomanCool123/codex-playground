#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестирование запуска консоли бота
"""

import subprocess
import sys
import os

def test_console_launch():
    """Тестируем различные способы запуска консоли"""
    
    print("🔍 Тестирование запуска консоли бота...")
    print(f"📂 Текущая директория: {os.getcwd()}")
    print(f"🐍 Python: {sys.executable}")
    
    # Проверяем наличие файлов
    files_to_check = ['bot_launcher.py', 'telegram_bot.py']
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} найден")
        else:
            print(f"❌ {file} НЕ найден")
    
    print("\n" + "="*50)
    print("1️⃣ Тестируем subprocess.Popen с CREATE_NEW_CONSOLE")
    
    try:
        process = subprocess.Popen([
            sys.executable, 'bot_launcher.py'
        ], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        print(f"✅ Консоль запущена (PID: {process.pid})")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
        print("\n2️⃣ Тестируем альтернативный способ через CMD")
        try:
            cmd = f'start "Test Bot Console" cmd /k "python bot_launcher.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print(f"✅ CMD запуск: {result.returncode}")
            if result.stderr:
                print(f"⚠️ Stderr: {result.stderr}")
                
        except Exception as e2:
            print(f"❌ CMD ошибка: {e2}")
            
            print("\n3️⃣ Тестируем прямой запуск")
            try:
                import bot_launcher
                print("✅ Прямой импорт успешен")
            except Exception as e3:
                print(f"❌ Импорт ошибка: {e3}")

if __name__ == "__main__":
    test_console_launch()
    input("\nНажмите Enter для выхода...")
