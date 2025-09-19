#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки функциональности автообновления страницы
"""

import sys
import os

# Добавляем путь к основному файлу
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Тест импорта основного модуля"""
    try:
        import gta5_rp_calculator17
        print("✅ Модуль gta5_rp_calculator17 успешно импортирован")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_class_methods():
    """Тест методов класса TraderApp"""
    try:
        import gta5_rp_calculator17
        import tkinter as tk
        
        # Создаем корневое окно
        root = tk.Tk()
        root.withdraw()  # Скрываем окно
        
        # Создаем экземпляр приложения
        app = gta5_rp_calculator17.TraderApp(root)
        
        # Проверяем наличие новых методов
        assert hasattr(app, 'toggle_page_refresh'), "Метод toggle_page_refresh не найден"
        assert hasattr(app, '_page_refresh_loop'), "Метод _page_refresh_loop не найден"
        assert hasattr(app, '_refresh_page'), "Метод _refresh_page не найден"
        assert hasattr(app, 'page_refresh_enabled'), "Атрибут page_refresh_enabled не найден"
        assert hasattr(app, 'page_refresh_thread'), "Атрибут page_refresh_thread не найден"
        
        print("✅ Все новые методы и атрибуты найдены")
        
        # Проверяем начальное состояние
        assert app.page_refresh_enabled == False, "page_refresh_enabled должен быть False по умолчанию"
        print("✅ Начальное состояние корректно")
        
        # Закрываем приложение
        app.on_close()
        root.destroy()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования методов: {e}")
        return False

def test_refresh_methods():
    """Тест методов обновления страницы"""
    try:
        import gta5_rp_calculator17
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()
        app = gta5_rp_calculator17.TraderApp(root)
        
        # Тестируем метод _refresh_page (без реального выполнения)
        # Проверяем, что метод существует и может быть вызван
        if hasattr(app, '_refresh_page'):
            print("✅ Метод _refresh_page доступен")
        
        # Тестируем переключение состояния
        initial_state = app.page_refresh_enabled
        app.toggle_page_refresh()
        new_state = app.page_refresh_enabled
        assert new_state != initial_state, "Состояние должно измениться"
        print("✅ Переключение состояния работает")
        
        # Возвращаем исходное состояние
        app.toggle_page_refresh()
        assert app.page_refresh_enabled == initial_state, "Состояние должно вернуться к исходному"
        print("✅ Возврат к исходному состоянию работает")
        
        app.on_close()
        root.destroy()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования методов обновления: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Запуск тестов автообновления страницы...")
    print("=" * 50)
    
    tests = [
        ("Импорт модуля", test_import),
        ("Методы класса", test_class_methods),
        ("Методы обновления", test_refresh_methods),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Тест: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - ПРОЙДЕН")
            else:
                print(f"❌ {test_name} - ПРОВАЛЕН")
        except Exception as e:
            print(f"❌ {test_name} - ОШИБКА: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Функциональность автообновления готова к использованию.")
        return True
    else:
        print("⚠️ Некоторые тесты провалены. Требуется дополнительная проверка.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
