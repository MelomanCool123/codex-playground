#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работы библиотеки keyboard
"""

import sys
import os

def test_keyboard():
    """Тестируем библиотеку keyboard"""
    print("=== Тест библиотеки keyboard ===")
    
    # Проверяем Python
    print(f"Python версия: {sys.version}")
    print(f"Путь к Python: {sys.executable}")
    print(f"Текущая директория: {os.getcwd()}")
    
    # Пытаемся импортировать keyboard
    try:
        import keyboard
        print("✅ Библиотека keyboard успешно импортирована")
        # У некоторых версий keyboard нет атрибута __version__
        try:
            print(f"Версия keyboard: {keyboard.__version__}")
        except AttributeError:
            print("Версия keyboard: неизвестна")
        
        # Тестируем базовые функции
        print("\nТестируем базовые функции...")
        
        # Проверяем, можем ли мы регистрировать горячие клавиши
        def test_callback():
            print("🎯 Горячая клавиша сработала!")
        
        try:
            print("Регистрирую тестовую горячую клавишу F12...")
            keyboard.add_hotkey("F12", test_callback, suppress=True)
            print("✅ Горячая клавиша F12 зарегистрирована")
            print("Нажмите F12 для теста (или Ctrl+C для выхода)")
            
            # Ждем нажатия
            keyboard.wait("F12")
            
        except Exception as e:
            print(f"❌ Ошибка при регистрации горячей клавиши: {e}")
            
        finally:
            # Очищаем все горячие клавиши
            try:
                keyboard.unhook_all()
                print("✅ Все горячие клавиши очищены")
            except Exception as e:
                print(f"❌ Ошибка при очистке горячих клавиш: {e}")
                
    except ImportError as e:
        print(f"❌ Не удалось импортировать keyboard: {e}")
        print("Попробуйте установить: pip install keyboard")
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":
    try:
        test_keyboard()
    except KeyboardInterrupt:
        print("\n\n👋 Тест прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
