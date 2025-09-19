#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для настройки внешнего доступа к мобильному интерфейсу
"""

import socket
import subprocess
import sys
import os

def get_local_ip():
    """Получает локальный IP адрес"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def get_external_ip():
    """Получает внешний IP адрес"""
    try:
        import urllib.request
        with urllib.request.urlopen('https://api.ipify.org') as response:
            return response.read().decode('utf-8')
    except:
        return "Не удалось определить"

def check_port_open(port):
    """Проверяет, открыт ли порт"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

def open_firewall_port(port):
    """Открывает порт в брандмауэре Windows"""
    try:
        cmd = f'netsh advfirewall firewall add rule name="GTA5 RP Calculator Mobile Interface" dir=in action=allow protocol=TCP localport={port}'
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Порт {port} открыт в брандмауэре Windows")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Не удалось открыть порт {port} в брандмауэре")
        return False

def main():
    print("🌐 Настройка внешнего доступа к мобильному интерфейсу")
    print("=" * 60)
    
    # Получаем IP адреса
    local_ip = get_local_ip()
    external_ip = get_external_ip()
    
    print(f"📱 Локальный IP: {local_ip}")
    print(f"🌍 Внешний IP: {external_ip}")
    print()
    
    # Проверяем порт
    port = 5000
    if check_port_open(port):
        print(f"✅ Порт {port} уже открыт")
    else:
        print(f"⚠️  Порт {port} закрыт")
        response = input("Открыть порт в брандмауэре Windows? (y/n): ")
        if response.lower() == 'y':
            open_firewall_port(port)
    
    print()
    print("📋 Инструкции по настройке:")
    print("=" * 60)
    print()
    print("1. 🌐 Настройка роутера:")
    print(f"   • Войдите в панель управления роутером")
    print(f"   • Найдите раздел 'Port Forwarding' или 'Виртуальные серверы'")
    print(f"   • Добавьте правило:")
    print(f"     - Внешний порт: {port}")
    print(f"     - Внутренний порт: {port}")
    print(f"     - Внутренний IP: {local_ip}")
    print(f"     - Протокол: TCP")
    print()
    print("2. 📱 Доступ к интерфейсу:")
    print(f"   • Локально: http://localhost:{port}")
    print(f"   • В сети: http://{local_ip}:{port}")
    print(f"   • Из интернета: http://{external_ip}:{port}")
    print()
    print("3. ⚠️  Безопасность:")
    print("   • Используйте только в доверенных сетях")
    print("   • Рассмотрите добавление аутентификации")
    print("   • Регулярно проверяйте логи доступа")
    print()
    print("4. 🔧 Настройки в программе:")
    print("   • Откройте настройки программы")
    print("   • Перейдите на вкладку 'Мобильный'")
    print("   • Установите хост: 0.0.0.0")
    print(f"   • Установите порт: {port}")
    print()
    
    # Создаем QR код для быстрого доступа
    try:
        import qrcode
        from PIL import Image
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"http://{local_ip}:{port}")
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("mobile_interface_qr.png")
        print("📱 QR-код для быстрого доступа сохранен в mobile_interface_qr.png")
        
    except ImportError:
        print("💡 Для создания QR-кода установите: pip install qrcode[pil]")
    
    print()
    print("✅ Настройка завершена!")
    print("🔄 Перезапустите программу для применения изменений")

if __name__ == "__main__":
    main()
