#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def convert_number_format(number):
    """Конвертация чисел в сокращенный формат для удобства отображения (например: 1000 = 1к, 1000000 = 1кк)"""
    try:
        if isinstance(number, str):
            # Если передана строка, пытаемся конвертировать в число
            number = float(number.replace(' ', '').replace(',', ''))
        
        if not isinstance(number, (int, float)):
            return str(number)
        
        # Конвертируем в сокращенный формат
        if number >= 1000000:
            # 1,000,000 = 1кк
            return f"{number // 1000000}кк"
        elif number >= 1000:
            # 1,000 = 1к
            return f"{number // 1000}к"
        else:
            # Меньше 1000 оставляем как есть
            return str(int(number))
        
    except Exception as e:
        print(f"Ошибка конвертации числа '{number}' в формат к/кк: {e}")
        return str(number)

def test_number_formatting():
    """Тестирование функции форматирования чисел"""
    test_cases = [
        1000,        # 1к
        5000,        # 5к
        10000,       # 10к
        1000000,     # 1кк
        5000000,     # 5кк
        10000000,    # 10кк
        999,         # 999 (остается как есть)
        500,         # 500 (остается как есть)
        50,          # 50 (остается как есть)
        "1000",      # Строка "1000" -> 1к
        "1,000",     # Строка "1,000" -> 1к
        "1 000",     # Строка "1 000" -> 1к
    ]
    
    print("Тестирование форматирования чисел в формат к/кк")
    print("=" * 50)
    
    for test_case in test_cases:
        result = convert_number_format(test_case)
        print(f"{test_case} -> {result}")
        print("-" * 30)

if __name__ == "__main__":
    test_number_formatting()
