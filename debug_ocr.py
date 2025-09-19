#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для диагностики проблем с OCR и парсингом транзакций 5VITO
"""
import sys
import os
import re
from PIL import Image, ImageGrab
import pytesseract
import pygetwindow as gw

def test_ocr_basic():
    """Тест базового OCR"""
    print("=== Тест базового OCR ===")
    try:
        # Пробуем сделать скриншот всего экрана
        print("Делаю скриншот экрана...")
        img = ImageGrab.grab()
        print(f"Скриншот создан: {img.size}, режим: {img.mode}")
        
        # Конвертируем в RGB если нужно
        if img.mode != 'RGB':
            img = img.convert('RGB')
            print("Изображение конвертировано в RGB")
        
        # Пробуем OCR
        print("Запускаю OCR...")
        text = pytesseract.image_to_string(img, lang='rus+eng')
        print(f"OCR завершен. Длина текста: {len(text)}")
        print(f"Первые 200 символов: {text[:200]}")
        
        return True
    except Exception as e:
        print(f"Ошибка OCR: {e}")
        return False

def test_window_detection():
    """Тест обнаружения окон"""
    print("\n=== Тест обнаружения окон ===")
    try:
        windows = gw.getAllWindows()
        print(f"Найдено окон: {len(windows)}")
        
        # Ищем окна с 5VITO
        vito_windows = []
        for win in windows:
            if '5VITO' in win.title or '5vito' in win.title.lower():
                vito_windows.append(win)
                print(f"Найдено окно 5VITO: {win.title}")
                print(f"  Позиция: {win.left}, {win.top}")
                print(f"  Размер: {win.width} x {win.height}")
        
        if not vito_windows:
            print("Окна 5VITO не найдены!")
            print("Доступные окна:")
            for i, win in enumerate(windows[:10]):  # Показываем первые 10
                print(f"  {i+1}. {win.title}")
        
        return vito_windows
    except Exception as e:
        print(f"Ошибка обнаружения окон: {e}")
        return []

def test_transaction_parsing():
    """Тест парсинга транзакций"""
    print("\n=== Тест парсинга транзакций ===")
    
    # Тестовые данные
    test_texts = [
        "Автомобиль $ 150,000 (куплено 1 шт.)",
        "Оружие $ 25,000 (продано 5 шт.)",
        "Недвижимость $ 500,000 (куплено 2 шт.)",
        "Телефон $ 1,500 (продано 10 шт.)"
    ]
    
    # Текущий паттерн
    pattern = r'([А-Яа-яЁё\s\-\.]+)\s+\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s+(\d+)\s+шт\.\)'
    
    print(f"Паттерн: {pattern}")
    print("\nТестирую на образцах:")
    
    for text in test_texts:
        matches = re.findall(pattern, text)
        print(f"  '{text}' -> {len(matches)} совпадений")
        for match in matches:
            print(f"    {match}")
    
    # Альтернативные паттерны
    print("\nАльтернативные паттерны:")
    
    # Паттерн 1: более гибкий
    pattern1 = r'([А-Яа-яЁё\s\-\.]+?)\s+\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s+(\d+)\s*шт\.?\)'
    
    # Паттерн 2: без обязательных пробелов
    pattern2 = r'([А-Яа-яЁё\s\-\.]+?)\s*\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s*(\d+)\s*шт\.?\)'
    
    # Паттерн 3: более простой
    pattern3 = r'([А-Яа-яЁё\s\-\.]+?)\s*\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s*(\d+)\s*шт'
    
    patterns = [pattern1, pattern2, pattern3]
    
    for i, p in enumerate(patterns, 1):
        print(f"\nПаттерн {i}: {p}")
        for text in test_texts:
            matches = re.findall(p, text)
            print(f"  '{text}' -> {len(matches)} совпадений")

def test_screenshot_area():
    """Тест области скриншота"""
    print("\n=== Тест области скриншота ===")
    
    vito_windows = test_window_detection()
    if not vito_windows:
        print("Не могу протестировать область без окна 5VITO")
        return
    
    window = vito_windows[0]
    print(f"Тестирую окно: {window.title}")
    
    try:
        # Рассчитываем область как в основном коде
        screen_width = 1920
        screen_height = 1080
        
        left = max(0, window.left + 300)
        top = max(0, window.top + 150)
        right = min(screen_width, window.right - 50)
        bottom = min(screen_height, window.bottom - 100)
        
        print(f"Рассчитанная область: {left}, {top} - {right}, {bottom}")
        print(f"Размер области: {right-left} x {bottom-top}")
        
        if right <= left or bottom <= top:
            print("ОШИБКА: Некорректная область!")
            return
        
        if (right - left) < 200 or (bottom - top) < 200:
            print("ПРЕДУПРЕЖДЕНИЕ: Область слишком маленькая!")
            return
        
        # Пробуем сделать скриншот
        print("Делаю скриншот области...")
        bbox = (left, top, right, bottom)
        img = ImageGrab.grab(bbox=bbox)
        
        if img is None:
            print("ОШИБКА: Не удалось создать скриншот")
            return
        
        print(f"Скриншот создан: {img.size}")
        
        # Сохраняем для проверки
        filename = "test_screenshot.png"
        img.save(filename)
        print(f"Скриншот сохранен как {filename}")
        
        # Пробуем OCR на этой области
        print("Запускаю OCR на области...")
        text = pytesseract.image_to_string(img, lang='rus+eng')
        print(f"OCR завершен. Длина текста: {len(text)}")
        print(f"Текст: {text[:300]}...")
        
        # Пробуем парсинг
        pattern = r'([А-Яа-яЁё\s\-\.]+?)\s*\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s*(\d+)\s*шт\.?\)'
        matches = re.findall(pattern, text)
        print(f"Найдено транзакций: {len(matches)}")
        
        for match in matches:
            print(f"  {match}")
        
    except Exception as e:
        print(f"Ошибка тестирования области: {e}")

def main():
    """Главная функция"""
    print("Диагностика OCR и парсинга транзакций 5VITO")
    print("=" * 50)
    
    # Проверяем доступность библиотек
    print("Проверка библиотек:")
    try:
        import PIL
        print(f"  PIL: {PIL.__version__}")
    except:
        print("  PIL: недоступна")
    
    try:
        print(f"  pytesseract: {pytesseract.get_tesseract_version()}")
    except:
        print("  pytesseract: недоступна")
    
    try:
        import pygetwindow
        print(f"  pygetwindow: доступна")
    except:
        print("  pygetwindow: недоступна")
    
    print()
    
    # Запускаем тесты
    test_ocr_basic()
    test_transaction_parsing()
    test_screenshot_area()
    
    print("\n" + "=" * 50)
    print("Диагностика завершена!")

if __name__ == "__main__":
    main()
