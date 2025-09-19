#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор QR-кода для мобильного интерфейса GTA5 RP Calculator
"""

import qrcode
import socket
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import webbrowser
import os

class QRCodeGenerator:
    def __init__(self, url=None):
        self.root = tk.Tk()
        self.root.title("QR-код для мобильного интерфейса")
        self.root.geometry("400x500")
        self.root.configure(bg="#1e1e1e")
        
        self.qr_image = None
        self.url = url if url else self.get_local_ip()
        
        # Список для хранения ссылок на изображения (защита от сборщика мусора)
        self.image_refs = []
        
        self.setup_gui()
        self.generate_qr()
        
    def get_local_ip(self):
        """Получает локальный IP адрес"""
        try:
            # Подключаемся к внешнему адресу, чтобы узнать локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return f"http://{local_ip}:5000"
        except Exception as e:
            print(f"Ошибка получения IP: {e}")
            return "http://localhost:5000"
    
    def setup_gui(self):
        """Настройка GUI"""
        # Заголовок
        title_label = tk.Label(
            self.root, 
            text="📱 QR-код для мобильного интерфейса",
            font=("Arial", 16, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        )
        title_label.pack(pady=20)
        
        # URL
        url_label = tk.Label(
            self.root,
            text=f"URL: {self.url}",
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#00ff00",
            wraplength=350
        )
        url_label.pack(pady=10)
        
        # QR-код
        self.qr_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.qr_frame.pack(pady=20)
        
        # Кнопки
        button_frame = tk.Frame(self.root, bg="#1e1e1e")
        button_frame.pack(pady=20)
        
        # Кнопка обновления
        refresh_btn = tk.Button(
            button_frame,
            text="🔄 Обновить QR-код",
            command=self.generate_qr,
            bg="#0066cc",
            fg="#ffffff",
            font=("Arial", 12),
            padx=20,
            pady=10
        )
        refresh_btn.pack(side=tk.LEFT, padx=10)
        
        # Кнопка открытия в браузере
        open_btn = tk.Button(
            button_frame,
            text="🌐 Открыть в браузере",
            command=self.open_in_browser,
            bg="#00aa00",
            fg="#ffffff",
            font=("Arial", 12),
            padx=20,
            pady=10
        )
        open_btn.pack(side=tk.LEFT, padx=10)
        
        # Кнопка сохранения
        save_btn = tk.Button(
            button_frame,
            text="💾 Сохранить QR-код",
            command=self.save_qr,
            bg="#aa6600",
            fg="#ffffff",
            font=("Arial", 12),
            padx=20,
            pady=10
        )
        save_btn.pack(side=tk.LEFT, padx=10)
        
        # Кнопка копирования URL
        copy_btn = tk.Button(
            button_frame,
            text="📋 Копировать URL",
            command=self.copy_url,
            bg="#0066aa",
            fg="#ffffff",
            font=("Arial", 12),
            padx=20,
            pady=10
        )
        copy_btn.pack(side=tk.LEFT, padx=10)
        
        # Инструкции
        instructions = tk.Label(
            self.root,
            text="📋 Инструкции:\n1. Отсканируйте QR-код камерой телефона\n2. Или введите URL вручную\n3. Убедитесь, что телефон в той же Wi-Fi сети",
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#cccccc",
            justify=tk.LEFT
        )
        instructions.pack(pady=20)
        
    def generate_qr(self):
        """Генерирует QR-код"""
        try:
            print(f"🔧 Создание QR-кода для URL: {self.url}")
            
            # Создаем QR-код с простыми параметрами
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr.add_data(self.url)
            qr.make(fit=True)
            
            # Создаем изображение
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменяем размер для отображения
            img = img.resize((120, 120), Image.Resampling.LANCZOS)
            
            # Сохраняем во временный файл
            temp_file = "temp_qr.png"
            img.save(temp_file)
            
            # Загружаем из файла
            self.root.after(0, lambda: self._load_qr_from_file(temp_file))
            
        except Exception as e:
            print(f"❌ Ошибка создания QR-кода: {e}")
            import traceback
            traceback.print_exc()
            self._show_text_fallback()
    
    def _load_qr_from_file(self, temp_file):
        """Загружает QR-код из файла"""
        try:
            # Загружаем изображение из файла
            self.qr_image = ImageTk.PhotoImage(file=temp_file)
            
            # Добавляем в список ссылок для защиты от сборщика мусора
            self.image_refs.append(self.qr_image)
            
            # Отображаем QR-код
            if hasattr(self, 'qr_label'):
                self.qr_label.destroy()
                
            self.qr_label = tk.Label(self.qr_frame, image=self.qr_image, bg="#1e1e1e")
            self.qr_label.image = self.qr_image  # Сохраняем ссылку на изображение
            self.qr_label.pack()
            
            # Удаляем временный файл
            try:
                os.remove(temp_file)
            except:
                pass
            
            print(f"✅ QR-код успешно создан и отображен")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки изображения QR-кода: {e}")
            import traceback
            traceback.print_exc()
            self._show_text_fallback()
    
    def _show_text_fallback(self):
        """Показывает текстовое сообщение вместо QR-кода"""
        if hasattr(self, 'qr_label'):
            self.qr_label.destroy()
        self.qr_label = tk.Label(
            self.qr_frame, 
            text=f"📱 Мобильный интерфейс\n\nURL для ввода вручную:\n{self.url}\n\n📋 Инструкции:\n1. Откройте браузер на телефоне\n2. Введите URL выше\n3. Убедитесь, что телефон в той же Wi-Fi сети",
            bg="#1e1e1e",
            fg="#00ff00",
            font=("Arial", 11, "bold"),
            justify=tk.CENTER,
            wraplength=350
        )
        self.qr_label.pack()
    
    def open_in_browser(self):
        """Открывает URL в браузере"""
        try:
            webbrowser.open(self.url)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть браузер: {e}")
    
    def save_qr(self):
        """Сохраняет QR-код в файл"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                initialname="mobile_interface_qr.png"
            )
            
            if filename:
                # Создаем QR-код снова для сохранения
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(self.url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="white", back_color="black")
                img.save(filename)
                
                messagebox.showinfo("Успех", f"QR-код сохранен в {filename}")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить QR-код: {e}")
    
    def copy_url(self):
        """Копирует URL в буфер обмена"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.url)
            messagebox.showinfo("Успех", f"URL скопирован в буфер обмена:\n{self.url}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать URL: {e}")
    
    def run(self):
        """Запускает приложение"""
        self.root.mainloop()

if __name__ == "__main__":
    app = QRCodeGenerator()
    app.run()
