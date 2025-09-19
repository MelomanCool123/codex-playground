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
            result = number / 1000000
            if result.is_integer():
                return f"{int(result)}кк"
            else:
                return f"{result:.1f}кк".replace('.', ',')
        elif number >= 1000:
            # 1,000 = 1к
            result = number / 1000
            if result.is_integer():
                return f"{int(result)}к"
            else:
                return f"{result:.1f}к".replace('.', ',')
        else:
            # Меньше 1000 оставляем как есть
            return str(int(number))
        
    except Exception as e:
        print(f"Ошибка конвертации числа '{number}' в формат к/кк: {e}")
        return str(number)

def test_decimal_formatting():
    """Тестирование улучшенной функции форматирования чисел с поддержкой десятичных значений"""
    test_cases = [
        # Целые тысячи
        1000,        # 1к
        5000,        # 5к
        10000,       # 10к
        
        # Десятичные тысячи
        1600,        # 1,6к
        2500,        # 2,5к
        17600,       # 17,6к
        45600,       # 45,6к
        127585,      # 127,6к
        24800,       # 24,8к
        8000,        # 8к
        3200,        # 3,2к
        1200,        # 1,2к
        550,         # 550 (остается как есть)
        
        # Миллионы
        1000000,     # 1кк
        5000000,     # 5кк
        10000000,    # 10кк
        
        # Десятичные миллионы
        1500000,     # 1,5кк
        2500000,     # 2,5кк
        395000,      # 395к (меньше миллиона)
        
        # Строки
        "1000",      # Строка "1000" -> 1к
        "1,000",     # Строка "1,000" -> 1к
        "1 000",     # Строка "1 000" -> 1к
        "17600",     # Строка "17600" -> 17,6к
    ]
    
    print("Тестирование улучшенного форматирования чисел с поддержкой десятичных значений")
    print("=" * 70)
    
    for test_case in test_cases:
        result = convert_number_format(test_case)
        print(f"{test_case} -> {result}")
        print("-" * 40)

if __name__ == "__main__":
    test_decimal_formatting()
