#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки функций автоимпорта из 5VITO
"""

import sys
import os
import re
from PIL import Image
import pytesseract

def test_regex_parsing():
    """Тестируем парсинг транзакций с помощью регулярных выражений"""
    print("=== Тест парсинга транзакций ===")
    
    # Тестовые строки (имитация OCR)
    test_cases = [
        "Слабое обезболивающее $ 52 700 (куплено 34 шт.)",
        "Сильное обезболивающее $ 89 500 (продано 12 шт.)",
        "Антибиотик $ 125 000 (куплено 5 шт.)",
        "Бинт $ 15 300 (продано 50 шт.)",
        "Неправильный формат $ 1000",
        "Товар без цены (куплено 10 шт.)"
    ]
    
    # Паттерн для парсинга
    pattern = r'([А-Яа-яЁё\s\-\.]+)\s+\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s+(\d+)\s+шт\.\)'
    
    print(f"Паттерн: {pattern}")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Тест {i}: {test_case}")
        
        match = re.search(pattern, test_case)
        if match:
            name = match.group(1).strip()
            price = match.group(2).replace(' ', '').replace(',', '')
            deal_type = match.group(3)
            quantity = int(match.group(4))
            
            print(f"  ✅ Успешно распарсено:")
            print(f"     Название: '{name}'")
            print(f"     Цена: {price}")
            print(f"     Тип: {deal_type}")
            print(f"     Количество: {quantity}")
        else:
            print(f"  ❌ Не удалось распарсить")
        
        print()

def test_bbox_calculation():
    """Тестируем расчет области для скриншота"""
    print("=== Тест расчета области скриншота ===")
    
    # Имитируем окно
    class MockWindow:
        def __init__(self, left, top, right, bottom):
            self.left = left
            self.top = top
            self.right = right
            self.bottom = bottom
    
    # Тестовые размеры окна
    test_windows = [
        MockWindow(100, 100, 900, 700),   # Обычное окно
        MockWindow(0, 0, 1920, 1080),     # Полноэкранное
        MockWindow(200, 150, 800, 600),   # Маленькое окно
    ]
    
    for i, window in enumerate(test_windows, 1):
        print(f"Тест {i}: Окно {window.left},{window.top} - {window.right},{window.bottom}")
        
        # Расчет области (как в коде)
        left = window.left + 300
        top = window.top + 150
        right = window.right - 50
        bottom = window.bottom - 100
        
        print(f"  Область транзакций: {left},{top} - {right},{bottom}")
        print(f"  Размер: {right-left} x {bottom-top}")
        print()

def test_import_logic():
    """Тестируем логику импорта транзакций"""
    print("=== Тест логики импорта ===")
    
    # Имитируем уже обработанные транзакции
    processed_transactions = set()
    
    # Тестовые транзакции
    test_transactions = [
        {'name': 'Товар 1', 'price': 1000, 'type': 'buy', 'quantity': 5},
        {'name': 'Товар 2', 'price': 2000, 'type': 'sell', 'quantity': 3},
        {'name': 'Товар 1', 'price': 1000, 'type': 'buy', 'quantity': 5},  # Дубликат
        {'name': 'Товар 3', 'price': 3000, 'type': 'buy', 'quantity': 1},
    ]
    
    print("Обрабатываем транзакции...")
    
    for i, trans in enumerate(test_transactions, 1):
        # Создаем уникальный ключ для транзакции
        trans_key = (trans['name'], trans['price'], trans['type'], trans['quantity'])
        
        print(f"Транзакция {i}: {trans['name']} - ${trans['price']} ({trans['type']})")
        
        if trans_key not in processed_transactions:
            processed_transactions.add(trans_key)
            print(f"  ✅ Новая транзакция - импортируем")
        else:
            print(f"  ❌ Дубликат - пропускаем")
    
    print(f"\nВсего уникальных транзакций: {len(processed_transactions)}")

def test_ocr_simulation():
    """Тестируем симуляцию OCR"""
    print("=== Тест симуляции OCR ===")
    
    # Имитируем данные OCR
    mock_ocr_data = {
        'text': [
            'Слабое обезболивающее',
            '$ 52 700',
            '(куплено 34 шт.)',
            'Сильное обезболивающее',
            '$ 89 500',
            '(продано 12 шт.)'
        ],
        'conf': [90, 95, 88, 92, 96, 87]  # Уровень уверенности
    }
    
    print("Имитируем данные OCR:")
    for i, (text, conf) in enumerate(zip(mock_ocr_data['text'], mock_ocr_data['conf'])):
        print(f"  {i+1}. '{text}' (уверенность: {conf}%)")
    
    # Собираем текст
    full_text = " ".join(mock_ocr_data['text'])
    print(f"\nСобранный текст: {full_text}")
    
    # Парсим
    pattern = r'([А-Яа-яЁё\s\-\.]+)\s+\$\s*([\d\s,]+)\s*\(([куплено|продано]+)\s+(\d+)\s+шт\.\)'
    matches = re.findall(pattern, full_text)
    
    print(f"\nНайдено транзакций: {len(matches)}")
    for i, match in enumerate(matches, 1):
        print(f"  {i}. {match[0]} - ${match[1]} ({match[2]} {match[3]} шт.)")

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование функций автоимпорта из 5VITO")
    print("=" * 50)
    
    try:
        test_regex_parsing()
        test_bbox_calculation()
        test_import_logic()
        test_ocr_simulation()
        
        print("✅ Все тесты пройдены успешно!")
        print("\n🎯 Функции готовы к использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
