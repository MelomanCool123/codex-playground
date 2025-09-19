#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для установки зависимостей GTA5 RP Calculator
"""

import subprocess
import sys
import os

def install_package(package):
    """Установка пакета через pip"""
    try:
        print(f"📦 Устанавливаем {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} установлен успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки {package}: {e}")
        return False

def main():
    """Главная функция установки"""
    print("🚀 Установка зависимостей для GTA5 RP Calculator")
    print("=" * 50)
    
    # Основные зависимости
    packages = [
        "Pillow>=9.0.0",
        "qrcode[pil]>=7.3.1",
        "python-telegram-bot>=20.0",
        "Flask>=2.0.0",
        "requests>=2.25.0"
    ]
    
    # Опциональные зависимости для OCR
    optional_packages = [
        "pytesseract>=0.3.10",
        "pyautogui>=0.9.54",
        "keyboard>=0.13.5",
        "pygetwindow>=0.0.9"
    ]
    
    print("📦 Устанавливаем основные зависимости...")
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n✅ Установлено {success_count}/{len(packages)} основных пакетов")
    
    # Спрашиваем про опциональные пакеты
    print("\n🔧 Опциональные зависимости для OCR и автоматизации:")
    for package in optional_packages:
        print(f"  - {package}")
    
    response = input("\n❓ Установить опциональные зависимости? (y/n): ").lower().strip()
    
    if response in ['y', 'yes', 'да', 'д']:
        print("\n📦 Устанавливаем опциональные зависимости...")
        optional_success = 0
        for package in optional_packages:
            if install_package(package):
                optional_success += 1
        
        print(f"\n✅ Установлено {optional_success}/{len(optional_packages)} опциональных пакетов")
    
    print("\n🎉 Установка завершена!")
    print("\n📋 Следующие шаги:")
    print("1. Получите токен Telegram бота у @BotFather")
    print("2. Установите переменную окружения:")
    print("   set TELEGRAM_BOT_TOKEN=your_bot_token_here")
    print("3. Запустите программу: python gta5_rp_calculator17.py")
    
    # Проверяем наличие Tesseract
    print("\n🔍 Проверяем наличие Tesseract OCR...")
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        print("✅ Tesseract найден и работает")
    except Exception as e:
        print("⚠️ Tesseract не найден или не работает")
        print("Для работы OCR установите Tesseract:")
        print("https://github.com/UB-Mannheim/tesseract/wiki")

if __name__ == "__main__":
    main()
