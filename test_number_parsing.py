#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def parse_number_with_suffix(number_str):
    """Парсинг чисел с суффиксами к/кк (например: 1к = 1000, 5кк = 5000000)"""
    try:
        if not number_str:
            return None
            
        # Убираем пробелы и запятые
        clean_number = number_str.replace(' ', '').replace(',', '').strip()
        
        # Если это уже обычное число без суффикса
        if clean_number.isdigit():
            print(f"Распознано обычное число: {clean_number}")
            return int(clean_number)
        
        # Ищем паттерн с суффиксом к (тысячи)
        k_match = re.match(r'^(\d+)к$', clean_number, re.IGNORECASE)
        if k_match:
            number = int(k_match.group(1))
            result = number * 1000
            print(f"Распознан суффикс 'к': {clean_number} = {result}")
            return result
        
        # Ищем паттерн с суффиксом кк (миллионы)
        kk_match = re.match(r'^(\d+)кк$', clean_number, re.IGNORECASE)
        if kk_match:
            number = int(kk_match.group(1))
            result = number * 1000000
            print(f"Распознан суффикс 'кк': {clean_number} = {result}")
            return result
        
        # Если ничего не подошло, возвращаем None
        print(f"Не удалось распознать формат числа: '{clean_number}'")
        return None
        
    except Exception as e:
        print(f"Ошибка парсинга числа с суффиксом '{number_str}': {e}")
        return None

def test_number_parsing():
    """Тестирование функции парсинга чисел"""
    test_cases = [
        "1000",      # Обычное число
        "1к",        # 1 тысяча
        "5к",        # 5 тысяч
        "10к",       # 10 тысяч
        "1кк",       # 1 миллион
        "5кк",       # 5 миллионов
        "2.5к",      # С точкой (должно не распознаться)
        "abc",       # Не число
        "1m",        # Неправильный суффикс
        " 1к ",      # С пробелами
        "1,000",     # С запятой
        "1 000",     # С пробелом
    ]
    
    print("Тестирование парсинга чисел с суффиксами к/кк")
    print("=" * 50)
    
    for test_case in test_cases:
        result = parse_number_with_suffix(test_case)
        print(f"'{test_case}' -> {result}")
        print("-" * 30)

if __name__ == "__main__":
    test_number_parsing()
