#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт для определения позиции мыши
Запустите этот файл для быстрого определения координат
"""

import pyautogui
import time
import ctypes
from ctypes import wintypes

def get_mouse_info():
    """Получает подробную информацию о позиции мыши"""
    try:
        # Получаем текущую позицию мыши
        mouse_x, mouse_y = pyautogui.position()
        print(f"🖱️ Позиция мыши: ({mouse_x}, {mouse_y})")
        
        # Получаем информацию об окне под курсором
        try:
            # Получаем handle окна под курсором
            point = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            hwnd = ctypes.windll.user32.WindowFromPoint(point)
            
            # Получаем заголовок окна
            window_title = ""
            if hwnd:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                    window_title = buffer.value
            
            # Получаем координаты окна
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            # Вычисляем относительные координаты
            rel_x = (mouse_x - rect.left) / (rect.right - rect.left) if rect.right != rect.left else 0
            rel_y = (mouse_y - rect.top) / (rect.bottom - rect.top) if rect.bottom != rect.top else 0
            
            print(f"\n🪟 Окно под курсором: \"{window_title}\"")
            print(f"📐 Координаты окна: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})")
            print(f"📏 Размер окна: {rect.right - rect.left} x {rect.bottom - rect.top}")
            print(f"\n🎯 Относительные координаты в окне:")
            print(f"X: {rel_x:.3f} (0.0-1.0)")
            print(f"Y: {rel_y:.3f} (0.0-1.0)")
            print(f"\n💡 Для автообновления используйте эти относительные координаты!")
            
        except Exception as e:
            print(f"\n❌ Ошибка получения информации об окне: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def continuous_mouse_tracking():
    """Непрерывное отслеживание позиции мыши"""
    print("🖱️ Непрерывное отслеживание позиции мыши")
    print("Нажмите Ctrl+C для выхода")
    print("-" * 50)
    
    try:
        while True:
            mouse_x, mouse_y = pyautogui.position()
            print(f"\r🖱️ ({mouse_x:4d}, {mouse_y:4d})", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n👋 Отслеживание остановлено")

def main():
    """Основная функция"""
    print("🖱️ Определение позиции мыши")
    print("=" * 40)
    print("1. Одноразовое определение")
    print("2. Непрерывное отслеживание")
    print("3. Выход")
    
    while True:
        try:
            choice = input("\nВыберите опцию (1-3): ").strip()
            
            if choice == "1":
                print("\n" + "=" * 40)
                get_mouse_info()
                print("=" * 40)
                
            elif choice == "2":
                print("\n" + "=" * 40)
                continuous_mouse_tracking()
                print("=" * 40)
                
            elif choice == "3":
                print("👋 До свидания!")
                break
                
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
