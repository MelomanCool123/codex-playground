# gta5_rp_calculator_enhanced.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv, os, json, threading, time, logging, traceback, sys, random, re, webbrowser
from queue import Queue
from datetime import datetime
from mobile_interface import MobileInterface
# from qr_generator import QRCodeGenerator

# Удалены импорты для автоимпорта 5vito
import gc  # Для сборки мусора

# Проверка наличия опциональных модулей
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    
try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pytesseract
    from PIL import Image, ImageGrab, ImageEnhance, ImageTk
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    import pygetwindow as gw
    HAS_GETWINDOW = True
except ImportError:
    HAS_GETWINDOW = False
    gw = None

# Telegram бот удален
TELEGRAM_BOT_AVAILABLE = False

# Файлы
ITEMS_FILE = "items.csv"
DEAL_FILE = "deal_history.csv"
SETTINGS_FILE = "settings.json"
ERROR_LOG = "error.log"

# --- ЛОГИРОВАНИЕ ---
logger = logging.getLogger("TraderApp")
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(fmt)
fh = logging.FileHandler(ERROR_LOG, encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(ch)
logger.addHandler(fh)

# Глобальная обработка необработанных исключений — пишем в error.log и в консоль
def excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    # Также печатаем трассировку в консоль (на случай двойного клика)
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = excepthook

# Путь к tesseract (автоматически определяется)
def setup_tesseract_path():
    """Автоматически находит и устанавливает путь к Tesseract"""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
        r"C:\tesseract\tesseract.exe"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract найден: {path}")
            return True
    
    # Если не найден в стандартных местах, попробуем найти через поиск
    try:
        import subprocess
        result = subprocess.run(['where', 'tesseract'], capture_output=True, text=True, shell=True)
        if result.returncode == 0 and result.stdout.strip():
            tesseract_path = result.stdout.strip().split('\n')[0]
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract найден через поиск: {tesseract_path}")
            return True
    except Exception as e:
        logger.debug(f"Ошибка поиска Tesseract: {e}")
    
    logger.warning("Tesseract не найден в стандартных местах")
    return False

# Пытаемся настроить Tesseract
if HAS_TESSERACT:
    setup_tesseract_path()


# ================= УЛУЧШЕННЫЙ ОВЕРЛЕЙ =================
class OverlayWindow:
    def __init__(self, app, alpha=0.8, geometry="300x500+100+100"):
        self.app = app
        self.alpha = alpha
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)
        try:
            self.root.attributes("-alpha", self.alpha)
        except Exception:
            pass
        self.root.configure(bg="#1e1e1e")
        self.root.geometry(geometry)
        self.visible = True

        # Заголовок с кнопками
        self.title_bar = tk.Frame(self.root, bg="#333333", height=28)
        self.title_bar.pack(fill=tk.X)
        self.title_bar.pack_propagate(False)
        
        tk.Label(self.title_bar, text="Оверлей GTA5", bg="#333333", fg="#fff", 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=8)
        
        # Кнопка переключения прозрачности
        self.alpha_btn = tk.Button(self.title_bar, text="α", bg="#555555", fg="#fff", 
                                 command=self.toggle_alpha, width=3, font=("Arial", 9))
        self.alpha_btn.pack(side=tk.RIGHT, padx=2)
        
        # Улучшенная обработка событий для кнопки прозрачности
        self.alpha_btn.bind("<KeyPress>", self._on_button_key_press)
        self.alpha_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.alpha_btn.bind("<FocusOut>", self._on_button_focus_out)

        # Кнопка автоматического сканирования
        self.auto_scan_btn = tk.Button(self.title_bar, text="⏸", bg="#aa0000", fg="#fff",
                                      command=self.toggle_auto_scan, width=3, font=("Arial", 9))
        self.auto_scan_btn.pack(side=tk.RIGHT, padx=2)
        
        # Улучшенная обработка событий для кнопки автосканирования
        self.auto_scan_btn.bind("<KeyPress>", self._on_button_key_press)
        self.auto_scan_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.auto_scan_btn.bind("<FocusOut>", self._on_button_focus_out)
        
        # Кнопка сканирования
        self.scan_btn = tk.Button(self.title_bar, text="🔍", bg="#555555", fg="#fff",
                                 command=self.scan_and_update, width=3, font=("Arial", 9))
        self.scan_btn.pack(side=tk.RIGHT, padx=2)
        
        # Улучшенная обработка событий для кнопки сканирования
        self.scan_btn.bind("<KeyPress>", self._on_button_key_press)
        self.scan_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.scan_btn.bind("<FocusOut>", self._on_button_focus_out)
        
        # Кнопка закрытия
        self.close_btn = tk.Button(self.title_bar, text="×", bg="#333333", fg="#fff", 
                                 bd=0, command=self.hide, font=("Arial", 12, "bold"), width=3)
        self.close_btn.pack(side=tk.RIGHT, padx=2)
        
        # Улучшенная обработка событий для кнопки закрытия
        self.close_btn.bind("<KeyPress>", self._on_button_key_press)
        self.close_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.close_btn.bind("<FocusOut>", self._on_button_focus_out)

        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)

        # Стиль Treeview
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Overlay.Treeview",
                        background="#2e2e2e", fieldbackground="#2e2e2e", foreground="#ffffff", rowheight=22)
        style.map("Overlay.Treeview", background=[("selected", "#555555")], foreground=[("selected", "#ffffff")])
        
        # Стиль для выгодных товаров (зеленый фон) - используем теги
        style.configure("Treeview", background="#2e2e2e", fieldbackground="#2e2e2e", foreground="#ffffff")
        style.map("Treeview", background=[("selected", "#555555")], foreground=[("selected", "#ffffff")])
        

        # === ПОИСК ТОВАРОВ ===
        self.search_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.search_frame.pack(fill=tk.X, padx=8, pady=5)
        
        tk.Label(self.search_frame, text="Поиск:", bg="#1e1e1e", fg="#fff").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, width=20, bg="#333333", fg="#fff")
        self.search_entry.pack(side=tk.LEFT, padx=5)
        # Исправлено: trace_variable -> trace_add
        self.search_var.trace_add("write", lambda *args: self.filter_items())
        
        # Улучшенная обработка событий для поля поиска
        self.search_entry.bind("<KeyPress>", self._on_search_key_press)
        self.search_entry.bind("<FocusIn>", self._on_input_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_input_focus_out)
        
        # Кнопка очистки поиска
        self.clear_search_btn = tk.Button(self.search_frame, text="×", bg="#555555", fg="#fff",
                                        command=self.clear_search, width=3)
        self.clear_search_btn.pack(side=tk.LEFT, padx=2)
        
        # Улучшенная обработка событий для кнопки очистки поиска
        self.clear_search_btn.bind("<KeyPress>", self._on_button_key_press)
        self.clear_search_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.clear_search_btn.bind("<FocusOut>", self._on_button_focus_out)

        # === ФОРМА ДОБАВЛЕНИЯ ===
        self.add_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.add_frame.pack(fill=tk.X, padx=8, pady=5)
        
        tk.Label(self.add_frame, text="Название:", bg="#1e1e1e", fg="#fff").grid(row=0, column=0, sticky="w")
        
        # Автодополнение названий
        self.name_combo = ttk.Combobox(self.add_frame, width=18)
        self.name_combo.grid(row=0, column=1, padx=2)
        self.name_combo.bind("<Return>", lambda e: self.price_entry.focus())
        self.name_combo.bind("<KeyPress>", self._on_input_key_press)
        self.name_combo.bind("<FocusIn>", self._on_input_focus_in)
        self.name_combo.bind("<FocusOut>", self._on_input_focus_out)
        
        tk.Label(self.add_frame, text="Цена:", bg="#1e1e1e", fg="#fff").grid(row=0, column=2, sticky="w")
        self.price_var = tk.StringVar()
        self.price_entry = tk.Entry(self.add_frame, textvariable=self.price_var, width=10, bg="#333333", fg="#fff")
        self.price_entry.grid(row=0, column=3, padx=2)
        self.price_entry.bind("<Return>", lambda e: self.add_item_from_overlay())
        self.price_entry.bind("<KeyPress>", self._on_input_key_press)
        self.price_entry.bind("<FocusIn>", self._on_input_focus_in)
        self.price_entry.bind("<FocusOut>", self._on_input_focus_out)
        
        # Привязываем обновление цветовой индикации к изменению цены с задержкой
        self.update_timer = None
        self.price_var.trace_add('write', lambda *args: self.schedule_profit_update())

        # === TREEVIEW ===
        self.tree_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        
        self.tree = ttk.Treeview(self.tree_frame, columns=("Название", "Средняя цена", "Комментарий"), 
                               show="headings", style="Overlay.Treeview", height=8)
        
        # Настройка колонок
        self.tree.heading("Название", text="Название", command=lambda: self.sort_treeview("Название", False))
        self.tree.heading("Средняя цена", text="Цена", command=lambda: self.sort_treeview("Средняя цена", False))
        self.tree.heading("Комментарий", text="Комментарий", command=lambda: self.sort_treeview("Комментарий", False))
        self.tree.column("Название", width=120, anchor=tk.W)
        self.tree.column("Средняя цена", width=60, anchor=tk.CENTER)
        self.tree.column("Комментарий", width=80, anchor=tk.W)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Настройки стилей для Treeview
        style = ttk.Style()
        style.configure("Overlay.Treeview", background="#2d2d2d", foreground="#ffffff")
        style.map("Overlay.Treeview", 
                 background=[('selected', '#404040'), ('active', '#2d2d2d')],
                 foreground=[('selected', '#ffffff'), ('active', '#ffffff')])
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # === КНОПКА ДОБАВЛЕНИЯ ===
        self.add_button_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.add_button_frame.pack(fill=tk.X, padx=8, pady=5)
        
        self.add_btn = tk.Button(
            self.add_button_frame, 
            text="ДОБАВИТЬ ТОВАР", 
            bg="#444444", 
            fg="#00ff00",
            command=self.add_item_from_overlay,
            font=("Arial", 10, "bold"),
            width=25,
            height=1,
            relief="raised",
            bd=2
        )
        self.add_btn.pack(pady=3)
        
        # Улучшенная обработка событий для кнопки добавления
        self.add_btn.bind("<KeyPress>", self._on_button_key_press)
        self.add_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.add_btn.bind("<FocusOut>", self._on_button_focus_out)

        # === КНОПКА АВТОЭНТЕРА ===
        self.auto_enter_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.auto_enter_frame.pack(fill=tk.X, padx=8, pady=3)
        
        self.auto_enter_btn = tk.Button(
            self.auto_enter_frame, 
            text="AUTO-ENTER: ВЫКЛ", 
            bg="#aa0000", 
            fg="#ffffff",
            command=self.toggle_auto_enter_from_overlay,
            font=("Arial", 8, "bold"),
            width=20,
            height=1,
            relief="raised",
            bd=1
        )
        self.auto_enter_btn.pack(pady=1)
        
        # Улучшенная обработка событий для кнопки автоэнтера
        self.auto_enter_btn.bind("<KeyPress>", self._on_button_key_press)
        self.auto_enter_btn.bind("<FocusIn>", self._on_button_focus_in)
        self.auto_enter_btn.bind("<FocusOut>", self._on_button_focus_out)

        # === СТАТУС БАР ===
        self.status_bar = tk.Label(self.root, text="Готов к работе", bg="#333333", fg="#00ff00", 
                                  anchor=tk.W, font=("Arial", 9))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Переменная для отслеживания состояния автоэнтера
        self.auto_enter_status = False

        # === ОБРАБОТЧИКИ СОБЫТИЙ ===
        self.tree.bind("<Double-1>", self.edit_item_from_overlay)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Улучшенная обработка событий для Treeview
        self.tree.bind("<KeyPress>", self._on_tree_key_press)
        self.tree.bind("<FocusIn>", self._on_tree_focus_in)
        self.tree.bind("<FocusOut>", self._on_tree_focus_out)
        self.tree.bind("<Button-1>", self._on_tree_click)
        
        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#333333", fg="#fff")
        self.context_menu.add_command(label="Редактировать", command=self.edit_selected)
        self.context_menu.add_command(label="Удалить", command=self.delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Копировать название", command=self.copy_name)
        self.context_menu.add_command(label="Копировать цену", command=self.copy_price)

        # Обработчик изменения размера
        self.root.bind("<Configure>", self.on_resize)
        
        # === УЛУЧШЕННАЯ ОБРАБОТКА СОБЫТИЙ ===
        # Принудительная обработка событий клавиатуры для всех кнопок
        self._setup_button_events()
        
        # Обработка событий клавиатуры для всего окна
        self.root.bind("<KeyPress>", self._handle_key_press)
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)
        
        # Принудительная обработка событий мыши для кнопок
        self._setup_mouse_events()

    # === ОСНОВНЫЕ МЕТОДЫ ===
    def add_item_from_overlay(self):
        try:
            name = self.name_combo.get().strip()
            price = self.price_var.get().strip()
            
            if not name:
                self.show_notification("Введите название товара!", "#ff6666")
                self.name_combo.config(background="#ff6666")
                self.root.after(300, lambda: self.name_combo.config(background="white"))
                return
                
            if not price:
                price = "0"
                
            # Добавляем в основное приложение
            self.app.name_var.set(name)
            self.app.avg_price_var.set(price)
            self.app.add_or_update()
            
            # Очищаем поля
            self.name_combo.set("")
            self.price_var.set("")
            
            # Фокусируемся на поле названия
            self.name_combo.focus()
            
            # Обновляем список и автодополнение
            self.update_list_from_app()
            self.update_autocomplete()
            
            self.show_notification(f"Товар '{name}' добавлен!", "#00ff00")
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка добавления товара: {e}")

    def edit_item_from_overlay(self, event):
        try:
            selection = self.tree.selection()
            if selection:
                item = self.tree.item(selection[0])
                values = item['values']
                if values:
                    self.name_combo.set(values[0])
                    self.price_var.set(values[1] if len(values) > 1 else "")
                    self.price_entry.focus()
                    # Принудительно устанавливаем фокус на окно
                    self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка редактирования товара: {e}")

    def update_list_from_app(self):
        """Обновляет список из данных основного приложения"""
        try:
            items = []
            for child in self.app.tree.get_children():
                vals = self.app.tree.item(child)["values"]
                if len(vals) >= 7:  # Убеждаемся, что есть все поля включая среднюю цену
                    items.append((vals[0], vals[6]))  # vals[6] - это средняя цена
            self.update_list(items)
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка обновления списка из приложения: {e}")

    def scan_and_update(self):
        """Сканирует экран и обновляет список товаров с найденными ценами"""
        try:
            # Оптимизация: не очищаем кэш при каждом сканировании для экономии ресурсов
            # Кэш будет обновляться автоматически по истечении TTL
            
            scanned_items = self.app.scan_items_with_prices()
            self.update_list_with_scanned_data(scanned_items)
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка сканирования: {e}")

    def update_list(self, items, update_indicators=True):
        try:
            # Оптимизация: обновляем только если список действительно изменился
            current_items = [(self.tree.item(child)["values"][0], self.tree.item(child)["values"][1]) 
                           for child in self.tree.get_children()]
            new_items = [(name, str(avg)) for name, avg in items]
            
            # Если списки одинаковые, не обновляем
            if current_items == new_items:
                return
                
            self.tree.delete(*self.tree.get_children())
            for name, avg in items:
                # Получаем комментарий для товара
                comment = self._get_item_comment(name)
                # Форматируем цену в сокращенном виде
                formatted_price = self._format_number(avg)
                # Вставляем товар без тега (цветовая индикация будет обновлена отдельно)
                self.tree.insert("", tk.END, values=(name, formatted_price, comment))
                
            # Обновляем статус бар
            count = len(items)
            self.status_bar.config(text=f"Товаров: {count} | Готов")
            
            # Обновляем цветовую индикацию только если нужно
            if update_indicators:
                self.update_profit_indicators()
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
            
        except Exception as e:
            logger.exception(f"Ошибка при обновлении списка оверлея: {e}")

    def update_list_with_scanned_data(self, scanned_items):
        """Обновляет список с отсканированными данными"""
        try:
            # Оптимизация: обновляем только если данные действительно изменились
            current_items = [(self.tree.item(child)["values"][0], self.tree.item(child)["values"][1]) 
                           for child in self.tree.get_children()]
            new_items = [(item_name, str(found_price)) for item_name, found_price, avg_price in scanned_items]
            
            # Если списки одинаковые, не обновляем
            if current_items == new_items:
                return
                
            # Очищаем список
            self.tree.delete(*self.tree.get_children())
            
            # Добавляем все найденные товары
            for item_name, found_price, avg_price in scanned_items:
                # Ищем комментарий для товара в основной базе
                comment = self._get_item_comment(item_name)
                # Форматируем цену в сокращенном виде
                formatted_price = self._format_number(found_price)
                self.tree.insert("", tk.END, values=(item_name, formatted_price, comment))
                
            # Обновляем статус бар
            total_count = len(scanned_items)
            self.status_bar.config(text=f"Товаров: {total_count} | Готов")
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
            
        except Exception as e:
            logger.exception(f"Ошибка при обновлении списка с отсканированными данными: {e}")

    def _get_item_comment(self, item_name):
        """Получает комментарий для товара из основной базы"""
        try:
            for child in self.app.tree.get_children():
                vals = self.app.tree.item(child)["values"]
                if len(vals) >= 8 and vals[0] == item_name:
                    # Комментарий находится в колонке 1 (индекс 1)
                    if len(vals) > 1 and vals[1] and str(vals[1]).strip():
                        comment = str(vals[1]).strip()
                        # Проверяем, что это не число (не "0.00", "0", и т.д.)
                        try:
                            float(comment)
                            # Если это число, то это не текстовый комментарий
                            return "—"
                        except ValueError:
                            # Если не число, то это текстовый комментарий
                            return comment
            return "—"  # Показываем тире для пустых комментариев
        except Exception as e:
            logger.exception(f"Ошибка получения комментария товара: {e}")
            return "—"
    
    def _format_number(self, number):
        """Форматирует число в сокращенном виде (1к, 1.5к, 1кк)"""
        try:
            if isinstance(number, str):
                number = float(number)
            
            if number >= 1000000:  # 1 миллион и больше
                return f"{number/1000000:.1f}кк".replace('.0', '')
            elif number >= 1000:  # 1 тысяча и больше
                return f"{number/1000:.1f}к".replace('.0', '')
            else:
                return str(int(number))
        except Exception as e:
            logger.exception(f"Ошибка форматирования числа: {e}")
            return str(number)

    def schedule_profit_update(self):
        """Планирует обновление цветовой индикации с задержкой для избежания лагов"""
        try:
            if self.update_timer:
                self.root.after_cancel(self.update_timer)
            self.update_timer = self.root.after(500, self.update_profit_indicators)  # 500ms задержка для лучшей производительности
        except Exception as e:
            logger.exception(f"Ошибка планирования обновления цветовой индикации: {e}")

    def update_profit_indicators(self):
        """Обновляет цветовую индикацию для всех товаров в оверлее"""
        try:
            current_price = self.price_var.get().strip()
            if not current_price:
                # Если цена пустая, убираем все теги
                for child in self.tree.get_children():
                    self.tree.item(child, tags=())
                return
                
            current_price_f = float(current_price)
            profitable_count = 0
            
            # Оптимизация: обновляем теги только для товаров, которые действительно изменились
            for child in self.tree.get_children():
                values = self.tree.item(child)["values"]
                if values and len(values) >= 2:
                    try:
                        avg_price_f = float(values[1])  # Средняя цена
                        is_profitable = avg_price_f > 0 and current_price_f > 0 and current_price_f < avg_price_f
                        
                        # Проверяем текущий тег
                        current_tags = self.tree.item(child, "tags")
                        should_have_tag = is_profitable
                        
                        # Обновляем тег только если он изменился
                        if should_have_tag and "profitable" not in current_tags:
                            self.tree.item(child, tags=("profitable",))
                            profitable_count += 1
                        elif not should_have_tag and "profitable" in current_tags:
                            self.tree.item(child, tags=())
                        elif should_have_tag:
                            profitable_count += 1
                            
                    except (ValueError, TypeError):
                        # Убираем тег только если он есть
                        if "profitable" in self.tree.item(child, "tags"):
                            self.tree.item(child, tags=())
            
            # Обновляем статус бар с информацией о выгодных товарах
            total_count = len(self.tree.get_children())
            if profitable_count > 0:
                self.status_bar.config(text=f"Товаров: {total_count} | Выгодных: {profitable_count}")
            else:
                self.status_bar.config(text=f"Товаров: {total_count} | Готов")
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
                
        except (ValueError, TypeError) as e:
            # Если цена некорректная, убираем все теги
            for child in self.tree.get_children():
                self.tree.item(child, tags=())
            logger.exception(f"Ошибка обновления цветовой индикации: {e}")
        except Exception as e:
            logger.exception(f"Ошибка обновления цветовой индикации: {e}")


    def toggle_auto_scan(self):
        """Переключает автоматическое сканирование"""
        try:
            self.app.auto_scan_enabled = not self.app.auto_scan_enabled
            
            if self.app.auto_scan_enabled:
                self.auto_scan_btn.config(text="▶", bg="#00aa00")
                self.start_auto_scan()
                self.show_notification("Автосканирование включено", "#00ff00")
            else:
                self.auto_scan_btn.config(text="⏸", bg="#aa0000")
                self.stop_auto_scan()
                self.show_notification("Автосканирование выключено", "#ff6666")
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка переключения автосканирования: {e}")

    def start_auto_scan(self):
        """Запускает автоматическое сканирование"""
        try:
            if self.app.auto_scan_timer:
                self.root.after_cancel(self.app.auto_scan_timer)
            
            def auto_scan_loop():
                if self.app.auto_scan_enabled and self.visible:
                    self.scan_and_update()
                    # Планируем следующее сканирование
                    self.app.auto_scan_timer = self.root.after(self.app.auto_scan_interval, auto_scan_loop)
            
            # Запускаем первое сканирование
            self.app.auto_scan_timer = self.root.after(100, auto_scan_loop)
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка запуска автосканирования: {e}")

    def stop_auto_scan(self):
        """Останавливает автоматическое сканирование"""
        try:
            if self.app.auto_scan_timer:
                self.root.after_cancel(self.app.auto_scan_timer)
                self.app.auto_scan_timer = None
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка остановки автосканирования: {e}")
        
    def update_autocomplete(self):
        """Обновляет список автодополнения"""
        try:
            names = [self.app.tree.item(c)["values"][0] for c in self.app.tree.get_children()]
            self.name_combo['values'] = names
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка обновления автодополнения: {e}")

    # === ФИЛЬТРАЦИЯ И ПОИСК ===
    def filter_items(self):
        try:
            search_text = self.search_var.get().lower()
            if not search_text:
                self.update_list_from_app()
                return
                
            filtered_items = []
            for child in self.app.tree.get_children():
                vals = self.app.tree.item(child)["values"]
                if len(vals) >= 7 and search_text in vals[0].lower():
                    filtered_items.append((vals[0], vals[6]))  # vals[6] - средняя цена
                    
            self.update_list(filtered_items)
            self.status_bar.config(text=f"Найдено: {len(filtered_items)} товаров")
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка фильтрации товаров: {e}")

    def clear_search(self):
        try:
            self.search_var.set("")
            self.update_list_from_app()
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка очистки поиска: {e}")

    # === КОНТЕКСТНОЕ МЕНЮ ===
    def show_context_menu(self, event):
        try:
            selection = self.tree.identify_row(event.y)
            if selection:
                self.tree.selection_set(selection)
                # Принудительно устанавливаем фокус на окно
                self.root.focus_set()
                try:
                    self.context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    self.context_menu.grab_release()
        except Exception as e:
            logger.exception(f"Ошибка показа контекстного меню: {e}")

    def edit_selected(self):
        try:
            self.edit_item_from_overlay(None)
        except Exception as e:
            logger.exception(f"Ошибка редактирования выбранного элемента: {e}")

    def delete_selected(self):
        try:
            selection = self.tree.selection()
            if selection:
                item_name = self.tree.item(selection[0])["values"][0]
                
                # Найти и удалить из основного приложения
                for child in self.app.tree.get_children():
                    vals = self.app.tree.item(child)["values"]
                    if vals[0] == item_name:
                        self.app.tree.delete(child)
                        self.app.save_items()
                        break
                
                self.update_list_from_app()
                self.update_autocomplete()
                self.show_notification(f"Товар '{item_name}' удален!", "#ff6666")
                
                # Принудительно устанавливаем фокус на окно
                self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка удаления товара: {e}")

    def copy_name(self):
        try:
            selection = self.tree.selection()
            if selection:
                name = self.tree.item(selection[0])["values"][0]
                self.root.clipboard_clear()
                self.root.clipboard_append(name)
                self.show_notification("Название скопировано!", "#00ff00")
                # Принудительно устанавливаем фокус на окно
                self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка копирования названия: {e}")

    def copy_price(self):
        try:
            selection = self.tree.selection()
            if selection and len(self.tree.item(selection[0])["values"]) > 1:
                price = self.tree.item(selection[0])["values"][1]
                self.root.clipboard_clear()
                self.root.clipboard_append(str(price))
                self.show_notification("Цена скопирована!", "#00ff00")
                # Принудительно устанавливаем фокус на окно
                self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка копирования цены: {e}")

    # === ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ===
    def toggle_alpha(self):
        try:
            self.alpha = 0.3 if self.alpha == 0.8 else 0.8
            self.set_alpha(self.alpha)
            status = "Прозрачный" if self.alpha == 0.3 else "Непрозрачный"
            self.show_notification(f"Режим: {status}", "#00ff00")
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка переключения прозрачности: {e}")

    def show_notification(self, message, color="#00ff00", duration=3000):
        """Показывает уведомление в статус баре"""
        try:
            self.status_bar.config(text=message, fg=color)
            self.root.after(duration, lambda: self.status_bar.config(text="Готов", fg="#00ff00"))
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка показа уведомления: {e}")
    
    def update_auto_enter_status(self, enabled):
        """Обновляет статус автообновления и показывает уведомление"""
        try:
            self.auto_enter_status = enabled
            status_text = "Автообновление: ВКЛ" if enabled else "Автообновление: ВЫКЛ"
            color = "#00ff00" if enabled else "#ff6666"
            self.show_notification(status_text, color)
            
            # Обновляем кнопку в оверлее
            if hasattr(self, 'auto_enter_btn'):
                self.auto_enter_btn.config(
                    text=status_text,
                    bg="#00aa00" if enabled else "#aa0000",
                    fg="#ffffff"
                )
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка обновления статуса автообновления: {e}")
    
    def toggle_auto_enter_from_overlay(self):
        """Переключение автообновления из оверлея"""
        try:
            # Вызываем функцию переключения автообновления из основного приложения
            self.app.toggle_page_refresh()
            
            # Обновляем статус кнопки внизу
            if hasattr(self.app, 'page_refresh_enabled'):
                enabled = self.app.page_refresh_enabled
                status_text = "AUTO-ENTER: ВКЛ" if enabled else "AUTO-ENTER: ВЫКЛ"
                bg_color = "#00aa00" if enabled else "#aa0000"
                
                self.auto_enter_btn.config(
                    text=status_text,
                    bg=bg_color,
                    fg="#ffffff"
                )
                
                # Показываем уведомление
                self.show_notification(status_text, "#00ff00" if enabled else "#ff6666")
                
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
                
        except Exception as e:
            self.show_notification("Ошибка переключения автообновления", "#ff0000")
            logger.exception(f"Ошибка переключения автообновления: {e}")

    def sort_treeview(self, col, reverse):
        """Сортировка Treeview"""
        try:
            items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
            
            def try_float(x):
                try:
                    return float(str(x).replace(",", "."))
                except ValueError:
                    return str(x).lower()
                    
            items.sort(key=lambda t: try_float(t[0]), reverse=reverse)
            
            for index, (_, k) in enumerate(items):
                self.tree.move(k, '', index)
                
            self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))
            
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка сортировки Treeview: {e}")

    def on_resize(self, event):
        """Обработчик изменения размера окна"""
        try:
            if event.widget == self.root:
                self.status_bar.config(text=f"Размер: {event.width}x{event.height}")
                # Принудительно устанавливаем фокус на окно
                self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка изменения размера окна: {e}")

    # === БАЗОВЫЕ МЕТОДЫ ===
    def start_move(self, event):
        try:
            self.x = event.x
            self.y = event.y
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка начала перемещения: {e}")

    def do_move(self, event):
        try:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка перемещения: {e}")

    def hide(self):
        if self.visible:
            try:
                self.root.withdraw()
                # Очищаем фокус с кнопок
                self.root.focus_set()
            except Exception:
                pass
            self.visible = False
            # Останавливаем автоматическое сканирование при скрытии оверлея
            self.stop_auto_scan()

    def show(self):
        if not self.visible:
            try:
                self.root.deiconify()
                self.root.lift()
                # Принудительно устанавливаем фокус на окно
                self.root.focus_set()
                # Обновляем состояние кнопок
                self._update_button_states()
            except Exception:
                pass
            self.visible = True
            self.update_list_from_app()
            self.update_autocomplete()
            self.name_combo.focus()

    def set_alpha(self, alpha):
        try:
            self.alpha = alpha
            self.root.attributes("-alpha", alpha)
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка установки прозрачности: {e}")

    def get_geometry(self):
        try:
            return self.root.geometry()
        except Exception as e:
            logger.exception(f"Ошибка получения геометрии окна: {e}")
            return ""

    def _setup_button_events(self):
        """Настраивает улучшенную обработку событий для всех кнопок"""
        try:
            # Список всех кнопок в оверлее
            buttons = [
                self.alpha_btn,
                self.auto_scan_btn,
                self.scan_btn,
                self.close_btn,
                self.clear_search_btn,
                self.add_btn,
                self.auto_enter_btn
            ]
            
            for button in buttons:
                if button:
                    # Принудительная обработка событий мыши
                    button.bind("<Button-1>", self._on_button_click)
                    button.bind("<ButtonRelease-1>", self._on_button_release)
                    
                    # Обработка событий клавиатуры
                    button.bind("<KeyPress>", self._on_button_key_press)
                    button.bind("<Return>", self._on_button_enter)
                    button.bind("<space>", self._on_button_space)
                    
                    # Обработка фокуса
                    button.bind("<FocusIn>", self._on_button_focus_in)
                    button.bind("<FocusOut>", self._on_button_focus_out)
                    
            # Дополнительная настройка для полей ввода
            input_widgets = [self.name_combo, self.price_entry, self.search_entry]
            for widget in input_widgets:
                if widget:
                    widget.bind("<KeyPress>", self._on_input_key_press)
                    widget.bind("<FocusIn>", self._on_input_focus_in)
                    widget.bind("<FocusOut>", self._on_input_focus_out)
                    
            # Дополнительная настройка для Treeview
            if hasattr(self, 'tree'):
                self.tree.bind("<KeyPress>", self._on_tree_key_press)
                self.tree.bind("<FocusIn>", self._on_tree_focus_in)
                self.tree.bind("<FocusOut>", self._on_tree_focus_out)
                self.tree.bind("<Button-1>", self._on_tree_click)
                    
        except Exception as e:
            logger.exception(f"Ошибка настройки событий кнопок: {e}")

    def _setup_mouse_events(self):
        """Настраивает обработку событий мыши для всего окна"""
        try:
            # Обработка кликов по всему окну
            self.root.bind("<Button-1>", self._on_window_click)
            self.root.bind("<ButtonRelease-1>", self._on_window_release)
            
            # Обработка движения мыши
            self.root.bind("<Motion>", self._on_mouse_motion)
            
        except Exception as e:
            logger.exception(f"Ошибка настройки событий мыши: {e}")

    def _on_button_click(self, event):
        """Обработчик клика по кнопке"""
        try:
            # Принудительно устанавливаем фокус на кнопку
            event.widget.focus_set()
            # Вызываем команду кнопки
            if hasattr(event.widget, 'cget'):
                command = event.widget.cget('command')
                if command:
                    command()
        except Exception as e:
            logger.exception(f"Ошибка обработки клика кнопки: {e}")

    def _on_button_release(self, event):
        """Обработчик отпускания кнопки мыши"""
        try:
            # Дополнительная обработка при необходимости
            pass
        except Exception as e:
            logger.exception(f"Ошибка обработки отпускания кнопки: {e}")

    def _on_button_key_press(self, event):
        """Обработчик нажатия клавиши на кнопке"""
        try:
            # Принудительно вызываем команду кнопки
            if hasattr(event.widget, 'cget'):
                command = event.widget.cget('command')
                if command:
                    command()
        except Exception as e:
            logger.exception(f"Ошибка обработки клавиши кнопки: {e}")

    def _on_button_enter(self, event):
        """Обработчик нажатия Enter на кнопке"""
        try:
            if hasattr(event.widget, 'cget'):
                command = event.widget.cget('command')
                if command:
                    command()
        except Exception as e:
            logger.exception(f"Ошибка обработки Enter кнопки: {e}")

    def _on_button_space(self, event):
        """Обработчик нажатия пробела на кнопке"""
        try:
            if hasattr(event.widget, 'cget'):
                command = event.widget.cget('command')
                if command:
                    command()
        except Exception as e:
            logger.exception(f"Ошибка обработки пробела кнопки: {e}")

    def _on_button_focus_in(self, event):
        """Обработчик получения фокуса кнопкой"""
        try:
            # Подсвечиваем кнопку при получении фокуса
            event.widget.config(relief="raised", bd=2)
        except Exception as e:
            logger.exception(f"Ошибка обработки фокуса кнопки: {e}")

    def _on_button_focus_out(self, event):
        """Обработчик потери фокуса кнопкой"""
        try:
            # Убираем подсветку при потере фокуса
            event.widget.config(relief="raised", bd=1)
        except Exception as e:
            logger.exception(f"Ошибка обработки потери фокуса кнопки: {e}")

    def _on_window_click(self, event):
        """Обработчик клика по окну"""
        try:
            # Принудительно устанавливаем фокус на окно
            self.root.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка обработки клика окна: {e}")

    def _on_window_release(self, event):
        """Обработчик отпускания кнопки мыши в окне"""
        try:
            # Дополнительная обработка при необходимости
            pass
        except Exception as e:
            logger.exception(f"Ошибка обработки отпускания в окне: {e}")

    def _on_mouse_motion(self, event):
        """Обработчик движения мыши"""
        try:
            # Дополнительная обработка при необходимости
            pass
        except Exception as e:
            logger.exception(f"Ошибка обработки движения мыши: {e}")

    def _handle_key_press(self, event):
        """Обработчик нажатий клавиш для всего окна"""
        try:
            # Обработка специальных клавиш
            if event.keysym == "Return":
                # Если фокус на поле ввода, добавляем товар
                if event.widget == self.name_combo or event.widget == self.price_entry:
                    self.add_item_from_overlay()
            elif event.keysym == "Escape":
                # Закрываем оверлей
                self.hide()
            elif event.keysym == "F1":
                # Переключаем прозрачность
                self.toggle_alpha()
            elif event.keysym == "F2":
                # Переключаем автосканирование
                self.toggle_auto_scan()
            elif event.keysym == "F3":
                # Сканируем
                self.scan_and_update()
            elif event.keysym == "F4":
                # Переключаем автообновление
                self.toggle_auto_enter_from_overlay()
                
        except Exception as e:
            logger.exception(f"Ошибка обработки клавиши: {e}")

    def _on_focus_in(self, event):
        """Обработчик получения фокуса окном"""
        try:
            # Принудительно обновляем состояние кнопок
            self._update_button_states()
        except Exception as e:
            logger.exception(f"Ошибка обработки фокуса окна: {e}")

    def _on_focus_out(self, event):
        """Обработчик потери фокуса окном"""
        try:
            # Дополнительная обработка при необходимости
            pass
        except Exception as e:
            logger.exception(f"Ошибка обработки потери фокуса окна: {e}")

    def _update_button_states(self):
        """Обновляет состояние всех кнопок"""
        try:
            # Обновляем состояние кнопки автосканирования
            if hasattr(self, 'auto_scan_btn'):
                if self.app.auto_scan_enabled:
                    self.auto_scan_btn.config(text="▶", bg="#00aa00")
                else:
                    self.auto_scan_btn.config(text="⏸", bg="#aa0000")
            
            # Обновляем состояние кнопки автообновления
            if hasattr(self, 'auto_enter_btn'):
                if hasattr(self.app, 'page_refresh_enabled') and self.app.page_refresh_enabled:
                    self.auto_enter_btn.config(text="AUTO-ENTER: ВКЛ", bg="#00aa00")
                else:
                    self.auto_enter_btn.config(text="AUTO-ENTER: ВЫКЛ", bg="#aa0000")
                    
        except Exception as e:
            logger.exception(f"Ошибка обновления состояния кнопок: {e}")

    def _on_input_key_press(self, event):
        """Обработчик нажатий клавиш в полях ввода"""
        try:
            # Обработка специальных клавиш
            if event.keysym == "Return":
                # Переходим к следующему полю или добавляем товар
                if event.widget == self.name_combo:
                    self.price_entry.focus()
                elif event.widget == self.price_entry:
                    self.add_item_from_overlay()
            elif event.keysym == "Escape":
                # Очищаем поля
                self.name_combo.set("")
                self.price_var.set("")
                self.name_combo.focus()
            elif event.keysym == "Tab":
                # Переключаемся между полями
                if event.widget == self.name_combo:
                    self.price_entry.focus()
                elif event.widget == self.price_entry:
                    self.name_combo.focus()
                    
        except Exception as e:
            logger.exception(f"Ошибка обработки клавиши в поле ввода: {e}")

    def _on_input_focus_in(self, event):
        """Обработчик получения фокуса полем ввода"""
        try:
            # Подсвечиваем поле при получении фокуса
            if hasattr(event.widget, 'config'):
                event.widget.config(relief="solid", bd=2)
        except Exception as e:
            logger.exception(f"Ошибка обработки фокуса поля ввода: {e}")

    def _on_input_focus_out(self, event):
        """Обработчик потери фокуса полем ввода"""
        try:
            # Убираем подсветку при потере фокуса
            if hasattr(event.widget, 'config'):
                event.widget.config(relief="flat", bd=1)
        except Exception as e:
            logger.exception(f"Ошибка обработки потери фокуса поля ввода: {e}")

    def _on_search_key_press(self, event):
        """Обработчик нажатий клавиш в поле поиска"""
        try:
            # Обработка специальных клавиш
            if event.keysym == "Escape":
                # Очищаем поле поиска
                self.search_var.set("")
                self.search_entry.focus()
            elif event.keysym == "Return":
                # Применяем поиск
                self.filter_items()
            elif event.keysym == "Tab":
                # Переходим к полю названия
                self.name_combo.focus()
                
        except Exception as e:
            logger.exception(f"Ошибка обработки клавиши в поле поиска: {e}")

    def _on_tree_key_press(self, event):
        """Обработчик нажатий клавиш в Treeview"""
        try:
            # Обработка специальных клавиш
            if event.keysym == "Return":
                # Редактируем выбранный элемент
                self.edit_item_from_overlay(None)
            elif event.keysym == "Delete":
                # Удаляем выбранный элемент
                self.delete_selected()
            elif event.keysym == "Escape":
                # Очищаем выбор
                self.tree.selection_remove(self.tree.selection())
            elif event.keysym == "Tab":
                # Переходим к полю названия
                self.name_combo.focus()
                
        except Exception as e:
            logger.exception(f"Ошибка обработки клавиши в Treeview: {e}")

    def _on_tree_focus_in(self, event):
        """Обработчик получения фокуса Treeview"""
        try:
            # Дополнительная обработка при необходимости
            pass
        except Exception as e:
            logger.exception(f"Ошибка обработки фокуса Treeview: {e}")

    def _on_tree_focus_out(self, event):
        """Обработчик потери фокуса Treeview"""
        try:
            # Дополнительная обработка при необходимости
            pass
        except Exception as e:
            logger.exception(f"Ошибка обработки потери фокуса Treeview: {e}")

    def _on_tree_click(self, event):
        """Обработчик клика по Treeview"""
        try:
            # Принудительно устанавливаем фокус на Treeview
            self.tree.focus_set()
        except Exception as e:
            logger.exception(f"Ошибка обработки клика Treeview: {e}")

    def destroy(self):
        try:
            self.root.destroy()
        except Exception as e:
            logger.exception(f"Ошибка уничтожения окна: {e}")


# ================= Окно статистики =================
class StatisticsWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.stats_vars = {
            "count": tk.StringVar(value="0"),
            "profit": tk.StringVar(value="0.00"),
            "income": tk.StringVar(value="0.00"),
            "expenses": tk.StringVar(value="0.00"),
            "net": tk.StringVar(value="0.00"),
            "avg_profit": tk.StringVar(value="0.00"),
            "avg_income": tk.StringVar(value="0.00"),
        }
        
    def create_window(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.focus()
            return
            
        self.window = tk.Toplevel(self.app.root)
        self.window.title("Статистика сделок")
        self.window.geometry("400x300")
        self.window.configure(bg="#1e1e1e")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Заголовок
        title_frame = tk.Frame(self.window, bg="#1e1e1e")
        title_frame.pack(fill="x", pady=10)
        tk.Label(title_frame, text="Статистика сделок", font=("Arial", 14, "bold"), 
                bg="#1e1e1e", fg="#ffffff").pack()
        
        # Статистика
        stats_frame = tk.Frame(self.window, bg="#1e1e1e")
        stats_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        labels = [
            ("Сделок", "count"),
            ("Прибыль", "profit"),
            ("Доход", "income"),
            ("Расходы", "expenses"),
            ("Итого", "net"),
            ("Средняя прибыль", "avg_profit"),
            ("Средний доход", "avg_income"),
        ]
        
        for i, (lbl, key) in enumerate(labels):
            row_frame = tk.Frame(stats_frame, bg="#1e1e1e")
            row_frame.pack(fill="x", pady=2)
            
            tk.Label(row_frame, text=lbl + ":", bg="#1e1e1e", fg="#fff", 
                    width=20, anchor="w").pack(side="left")
            tk.Label(row_frame, textvariable=self.stats_vars[key], bg="#1e1e1e", 
                    fg="#00ffcc", width=15, anchor="w").pack(side="left")
        
        # Кнопка закрытия
        btn_frame = tk.Frame(self.window, bg="#1e1e1e")
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="Закрыть", command=self.hide, 
                 bg="#333333", fg="#fff", width=15).pack()
    
    def show(self):
        self.create_window()
        self.update_stats()
    
    def hide(self):
        if self.window and self.window.winfo_exists():
            self.window.withdraw()
    
    def update_stats(self):
        """Обновить статистику из главного приложения"""
        if hasattr(self.app, 'stats_vars'):
            for key in self.stats_vars:
                if key in self.app.stats_vars:
                    self.stats_vars[key].set(self.app.stats_vars[key].get())


# ================= Редактор интерфейса =================
class UIEditor(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Редактор интерфейса")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)

        tk.Label(self, text="Отображение панелей:", bg="#1e1e1e", fg="#fff").pack(anchor="w", padx=10, pady=(10, 2))
        self.panel_vars = {}
        for key, label in [("items", "Товары"), ("history", "История сделок"), ("stats", "Статистика"), ("overlay", "Оверлей")]:
            var = tk.BooleanVar(value=self.app.ui_config.get("panels", {}).get(key, True))
            cb = tk.Checkbutton(self, text=label, variable=var, bg="#1e1e1e", fg="#fff", selectcolor="#444444", activebackground="#1e1e1e")
            cb.pack(anchor="w", padx=20, pady=2)
            self.panel_vars[key] = var

        tk.Label(self, text="Подписи кнопок:", bg="#1e1e1e", fg="#fff").pack(anchor="w", padx=10, pady=(10, 2))
        self.button_entries = {}
        btnframe = tk.Frame(self, bg="#1e1e1e")
        btnframe.pack(fill="x", padx=10, pady=5)
        for key in ["add_item", "export_items", "clear_form", "delete_item", "add_deal", "toggle_overlay", "show_stats"]:
            lbl = tk.Label(btnframe, text=key, bg="#1e1e1e", fg="#fff")
            ent = tk.Entry(btnframe)
            ent.insert(0, self.app.ui_config.get("buttons", {}).get(key, self.app.default_button_texts.get(key, key)))
            lbl.pack(anchor="w")
            ent.pack(fill="x", pady=2)
            self.button_entries[key] = ent

        save_btn = tk.Button(self, text="Сохранить", command=self.save, bg="#333333", fg="#fff")
        save_btn.pack(pady=10)

    def save(self):
        try:
            self.app.ui_config["panels"] = {k: v.get() for k, v in self.panel_vars.items()}
            self.app.ui_config["buttons"] = {k: e.get() for k, e in self.button_entries.items()}
            self.app.save_settings()
            self.app.apply_ui_config()
            self.destroy()
        except Exception:
            logger.exception("Ошибка при сохранении UI-конфига")


# ================= Оверлей выделения области =================
class SelectionOverlay:
    def __init__(self, master):
        self.master = master
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.done = threading.Event()
        self.result_bbox = None  # (left, top, right, bottom)

        self.top = tk.Toplevel(master)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.25)
        self.top.configure(bg="#000000")
        self.top.configure(cursor="crosshair")
        # Создаем канвас ПЕРЕД привязками и используем валидный цвет
        self.canvas = tk.Canvas(self.top, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Привязываем события к канвасу
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda e: self._cancel())

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="#00ff00", width=2)

    def on_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x0, y0 = self.start_x, self.start_y
        x1, y1 = event.x, event.y
        left, right = sorted([x0, x1])
        top, bottom = sorted([y0, y1])
        # Переводим в координаты экрана
        abs_left = left
        abs_top = top
        abs_right = right
        abs_bottom = bottom
        self.result_bbox = (abs_left, abs_top, abs_right, abs_bottom)
        try:
            self.top.destroy()
        finally:
            self.done.set()

    def get_bbox(self, timeout=None):
        self.done.wait(timeout=timeout)
        return self.result_bbox

    def _cancel(self):
        try:
            self.top.destroy()
        finally:
            self.result_bbox = None
            self.done.set()

# ================= Автоматическая покупка товаров =================
# Класс AutoBuyer удален

# ================= Основное приложение =================
class TraderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GTA5 RP Перекуп-Калькулятор")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e1e")

        # Данные и состояния
        self.history = []
        self.running = True
        self.items_data = []

        # OCR/overlay настройки по умолчанию
        self.overlay_alpha = 0.8
        self.overlay_refresh = 0.2  # Увеличена скорость обработки оверлея (0.2 сек вместо 1.0)
        self.bbox = None
        self.overlays_enabled = True
        self.overlay_geometry = "350x650+100+100"

        # UI-config (панели, подписи кнопок и др.)
        self.ui_config = {}
        self.default_button_texts = {
            "add_item": "Сохранить товар",
            "export_items": "Экспорт CSV товаров",
            "clear_form": "Очистить форму",
            "delete_item": "Удалить запись",
            "add_deal": "Добавить сделку",
            "toggle_overlay": "Оверлей Вкл",
            "show_stats": "Показать статистику",
            "auto_buy": "Авто-покупка"
        }

        # Переменные tkinter
        self.name_var = tk.StringVar()
        self.buy_var = tk.StringVar()
        self.sell_var = tk.StringVar()
        self.repair_var = tk.StringVar(value="0")
        self.tax_var = tk.StringVar(value="0")
        self.avg_price_var = tk.StringVar()
        self.total_profit_var = tk.StringVar(value="0.00")
        self.window_var = tk.StringVar()
        self.deal_price_var = tk.StringVar()
        self.deal_type_var = tk.StringVar(value="buy")
        self.main_search_var = tk.StringVar()  # Для поиска в основном окне
        self.comment_var = tk.StringVar()  # Для комментария к товару

        # Статистика vars
        self.stats_vars = {
            "count": tk.StringVar(value="0"),
            "profit": tk.StringVar(value="0.00"),
            "income": tk.StringVar(value="0.00"),
            "expenses": tk.StringVar(value="0.00"),
            "net": tk.StringVar(value="0.00"),
            "avg_profit": tk.StringVar(value="0.00"),
            "avg_income": tk.StringVar(value="0.00"),
        }

        # GUI элементы, которые будут менять подписи/видимость
        self.reg_buttons = {}   # словарь для кнопок {key: widget}
        self.panels_frames = {}  # словарь фреймов панелей

        # OCR очередь
        self.ocr_queue = Queue()
        self.ocr_thread = None
        self.ocr_enabled = True
        
        # Автоматическое сканирование оверлея
        self.auto_scan_enabled = False
        self.auto_scan_interval = 5000  # 5 секунд по умолчанию для снижения нагрузки
        self.auto_scan_timer = None
        
        # Оптимизированное кэширование для снижения потребления памяти
        self.window_cache = None
        self.window_cache_time = 0
        self.window_cache_ttl = 5000  # 5 секунд кэш для снижения частоты обновлений
        
        # Адаптивные интервалы для автосканирования
        self.scan_count = 0
        self.last_scan_time = 0
        self.adaptive_interval = 5000  # Увеличенный начальный интервал
        
        # Кэширование названий товаров
        self.item_names_cache = None
        self.item_names_cache_time = 0
        self.item_names_cache_ttl = 10000  # 10 секунд кэш для снижения частоты обновлений
        
        # Оптимизированные настройки OCR для снижения потребления ресурсов
        self.ocr_settings = {
            'contrast_factor': 1.2,      # Уменьшенный фактор контрастности
            'sharpness_factor': 1.0,     # Отключена резкость для экономии ресурсов
            'min_confidence': 25,        # Снижена минимальная уверенность OCR
            'min_price': 1,              # Минимальная цена
            'max_price': 1000000,        # Максимальная цена
            'min_match_score': 60,       # Снижена минимальная оценка совпадения
            'image_scale_factor': 1.0    # Отключено масштабирование для экономии памяти
        }
        
        # Предкомпилированные регулярные выражения (для производительности)
        try:
            self._re_price_in_text = re.compile(r"(\d[\d\s.,]{2,})")
            self._re_digits = re.compile(r"\d+")
            self._re_clean_text = re.compile(r"[^\w\s.,:()/-]")
            self._re_only_specials = re.compile(r"^[^\w]*$")
            # Паттерны из _is_valid_text
            garbage_patterns = [
                r'^[^\w]*$',
                r'^[а-яё]{1,2}$',
                r'^[a-z]{1,2}$',
                r'^[0-9]+$',
                r'^[^\w\s]*$',
                r'^[а-яё]*[ыы]+[а-яё]*$',
                r'^[а-яё]*[а-яё]{1,2}[а-яё]*$',
                r'^[а-яё]*[а-яё]{1,3}$',
                r'^[а-яё]*[а-яё]{1,3}[а-яё]*$',
                r'^[а-яё]*[а-яё]{1,3}[а-яё]*[а-яё]{1,3}[а-яё]*$',
            ]
            suspicious_patterns = [
                r'^[а-яё]{1,3}[а-яё]{1,3}$',
                r'^[а-яё]{1,2}[а-яё]{1,2}[а-яё]{1,2}$',
                r'^[а-яё]*[а-яё]{1,2}[а-яё]*[а-яё]{1,2}[а-яё]*$',
            ]
            self._re_garbage_list = [re.compile(p, re.IGNORECASE) for p in garbage_patterns]
            self._re_suspicious_list = [re.compile(p, re.IGNORECASE) for p in suspicious_patterns]
        except Exception:
            # В случае ошибок компиляции оставляем как есть — функции ниже имеют запасной путь
            self._re_price_in_text = None
            self._re_digits = None
            self._re_clean_text = None
            self._re_only_specials = None
            self._re_garbage_list = []
            self._re_suspicious_list = []
        
        # Окно статистики
        self.stats_window = None
        
        # Telegram бот удален

        # Автообновление страницы
        self.page_refresh_enabled = False
        self.page_refresh_thread = None
        self.auto_enter_min_delay = 0.2  # Минимальная задержка между обновлениями (сек) - 5 раз в секунду
        self.auto_enter_max_delay = 0.33  # Максимальная задержка между обновлениями (сек) - 3 раза в секунду
        self.auto_enter_status_var = tk.StringVar(value="Автообновление: Выкл")
        
        # Координаты поля поиска для автообновления
        self.search_field_x = 0.695  # Относительная позиция X (0.0-1.0, где 0.5 = центр)
        self.search_field_y = 0.142  # Относительная позиция Y (0.0-1.0, где 0.1 = 10% от верха)
        
        # Состояние автообновления
        self.search_field_clicked = False  # Флаг того, что поле поиска уже активировано
        
        # Переменные автоимпорта удалены
        
        # Мониторинг горячих клавиш
        self.hotkeys_monitor_enabled = True
        self.hotkeys_last_check = time.time()
        
        # Уведомления о PayDay
        self.payday_notifications_enabled = True
        self.last_payday_notification = None
        
        # Автоматическая покупка товаров со скидкой удалена

        # Мобильный веб-интерфейс
        self.mobile_interface = None
        self.mobile_interface_thread = None
        self.mobile_interface_enabled = True  # Включаем по умолчанию

        # Загружаем настройки/данные
        self.load_settings()
        self.setup_gui()
        self.load_items()
        self.load_deals()
        self.update_total_profit()
        
        # Синхронизация с ботом удалена

        # Проверяем Tesseract
        self.check_tesseract()
        
        # Устанавливаем путь к Tesseract (если доступен)
        if HAS_TESSERACT:
            try:
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                logger.info("Путь к Tesseract установлен")
            except Exception as e:
                logger.warning(f"Не удалось установить путь к Tesseract: {e}")
        else:
            logger.info("Tesseract OCR не установлен - пропускаем настройку пути")

        # Оверлей - создаем после setup_gui
        self.overlay_window = OverlayWindow(self, alpha=self.overlay_alpha, geometry=self.overlay_geometry)
        if not self.overlays_enabled:
            self.overlay_window.hide()

        # Показываем начальный статус автообновления в оверлее
        if hasattr(self, 'overlay_window'):
            self.overlay_window.update_auto_enter_status(self.page_refresh_enabled)

        # Запускаем OCR-поток если включён
        if self.ocr_enabled:
            self.ocr_thread = threading.Thread(target=self.ocr_loop, daemon=True, name="OCRThread")
            self.ocr_thread.start()
            self.root.after(100, self.update_overlay_safe)

        # Регистрируем горячие клавиши
        self._register_hotkeys()
        
        # Запускаем мониторинг горячих клавиш
        self._start_hotkeys_monitor()
        
        # Запускаем мониторинг PayDay уведомлений
        self._start_payday_monitor()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Обработчик сворачивания окна - останавливаем автоэнтер
        self.root.bind("<Unmap>", self._on_window_minimize)
        self.root.bind("<Map>", self._on_window_restore)

        # Применяем UI конфиг (подписи кнопок, видимость панелей)
        self.apply_ui_config()
        
        # Обновляем комбобокс после создания оверлея
        self.update_combobox_values()
        
        # Обновляем список окон
        self.update_window_list()
        
        # Запускаем мобильный интерфейс
        self.start_mobile_interface()
        
        # Telegram бот удален

    def start_mobile_interface(self):
        """Запуск мобильного интерфейса"""
        try:
            # Создаем экземпляр мобильного интерфейса
            self.mobile_interface = MobileInterface(self)
            
            # Запускаем в отдельном потоке
            mobile_thread = threading.Thread(target=self.mobile_interface.run, daemon=True)
            mobile_thread.start()
            
            logger.info("📱 Мобильный интерфейс запущен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мобильного интерфейса: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить мобильный интерфейс:\n{str(e)}")

    # ---------------- GUI ----------------
    def setup_gui(self):
        top_frame = tk.Frame(self.root, bg="#1e1e1e")
        top_frame.grid(row=0, column=0, columnspan=8, sticky="ew", padx=5, pady=5)
        top_frame.grid_columnconfigure(1, weight=1)

        tk.Label(top_frame, text="Общий заработок: ", bg="#1e1e1e", fg="#ffffff",
                 font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        self.profit_label = tk.Label(top_frame, textvariable=self.total_profit_var, bg="#1e1e1e", fg="#00ff00",
                                     font=("Arial", 12, "bold"))
        self.profit_label.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(top_frame, text="Выбор окна:", bg="#1e1e1e", fg="#ffffff").grid(row=0, column=2, sticky="e")
        self.window_cb = ttk.Combobox(top_frame, textvariable=self.window_var, width=30)
        self.window_cb.grid(row=0, column=3, sticky="w", padx=5)
        tk.Button(top_frame, text="Обновить окна", command=self.update_window_list, bg="#333333", fg="#fff")\
            .grid(row=0, column=4, padx=5)

        self.toggle_overlay_btn = tk.Button(top_frame, text=self.default_button_texts["toggle_overlay"], command=self.toggle_overlay, bg="#333333", fg="#fff")
        self.toggle_overlay_btn.grid(row=0, column=5, padx=5)
        self.reg_buttons["toggle_overlay"] = self.toggle_overlay_btn
        
        self.show_stats_btn = tk.Button(top_frame, text=self.default_button_texts["show_stats"], command=self.show_stats, bg="#333333", fg="#fff")
        self.show_stats_btn.grid(row=0, column=6, padx=5)
        self.reg_buttons["show_stats"] = self.show_stats_btn

        self.settings_btn = tk.Button(top_frame, text="Настройки", command=self.open_settings, bg="#333333", fg="#fff")
        self.settings_btn.grid(row=0, column=7, padx=5)
        
        # Кнопка перезагрузки горячих клавиш
        self.reload_hotkeys_btn = tk.Button(top_frame, text="🔄 Hotkeys", command=self.reload_hotkeys, 
                                          bg="#555555", fg="#fff", width=10)
        self.reload_hotkeys_btn.grid(row=0, column=8, padx=5)
        
        # Кнопка тестирования автообновления
        self.test_auto_enter_btn = tk.Button(top_frame, text="🔄 Auto Enter", command=self.toggle_page_refresh, 
                                           bg="#0066cc", fg="#fff", width=12)
        self.test_auto_enter_btn.grid(row=0, column=9, padx=5)
        
        # Кнопка настройки мобильного интерфейса
        self.mobile_setup_btn = tk.Button(top_frame, text="📱 Mobile", command=self.setup_mobile_access, 
                                         bg="#0088cc", fg="#fff", width=10)
        self.mobile_setup_btn.grid(row=0, column=10, padx=5)

        
        # Кнопка и статус автопокупки
        # Кнопка автопокупки удалена

        # Меню -> Редактор интерфейса
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        ui_menu = tk.Menu(menu, tearoff=0)
        ui_menu.add_command(label="Редактор интерфейса", command=lambda: UIEditor(self))
        menu.add_cascade(label="Интерфейс", menu=ui_menu)

        # Форма товара и таблица товаров (панель items)
        items_frame = tk.LabelFrame(self.root, text="Товары", bg="#1e1e1e", fg="#fff")
        items_frame.grid(row=1, column=0, columnspan=8, sticky="nsew", padx=10, pady=6)
        self.panels_frames["items"] = items_frame

        tk.Label(items_frame, text="Название", bg="#1e1e1e", fg="#fff").grid(row=0, column=0, padx=5, pady=5)
        self.name_cb = ttk.Combobox(items_frame, textvariable=self.name_var, width=20)
        self.name_cb.grid(row=0, column=1, padx=5, pady=5)
        self.name_cb.bind("<<ComboboxSelected>>", self.fill_form_from_selection)

        tk.Label(items_frame, text="Цена покупки", bg="#1e1e1e", fg="#fff").grid(row=0, column=2, padx=5, pady=5)
        self.buy_entry = tk.Entry(items_frame, textvariable=self.buy_var, width=10)
        self.buy_entry.grid(row=0, column=3, padx=5, pady=5)
        tk.Label(items_frame, text="Цена продажи", bg="#1e1e1e", fg="#fff").grid(row=0, column=4, padx=5, pady=5)
        self.sell_entry = tk.Entry(items_frame, textvariable=self.sell_var, width=10)
        self.sell_entry.grid(row=0, column=5, padx=5, pady=5)

        tk.Label(items_frame, text="Ремонт/тюнинг", bg="#1e1e1e", fg="#fff").grid(row=1, column=0, padx=5, pady=5)
        self.repair_entry = tk.Entry(items_frame, textvariable=self.repair_var, width=10)
        self.repair_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(items_frame, text="Налог/Комиссия %", bg="#1e1e1e", fg="#fff").grid(row=1, column=2, padx=5, pady=5)
        self.tax_entry = tk.Entry(items_frame, textvariable=self.tax_var, width=10)
        self.tax_entry.grid(row=1, column=3, padx=5, pady=5)
        tk.Label(items_frame, text="Средняя цена", bg="#1e1e1e", fg="#fff").grid(row=1, column=4, padx=5, pady=5)
        self.avg_entry = tk.Entry(items_frame, textvariable=self.avg_price_var, width=10)
        self.avg_entry.grid(row=1, column=5, padx=5, pady=5)

        tk.Label(items_frame, text="Комментарий", bg="#1e1e1e", fg="#fff").grid(row=1, column=6, padx=5, pady=5)
        self.comment_entry = tk.Entry(items_frame, textvariable=self.comment_var, width=15)
        self.comment_entry.grid(row=1, column=7, padx=5, pady=5)

        # Кнопки управления товарами
        btn_frame = tk.Frame(items_frame, bg="#1e1e1e")
        btn_frame.grid(row=2, column=0, columnspan=8, sticky="ew", pady=5)
        for i in range(8):
            btn_frame.grid_columnconfigure(i, weight=1)

        b1 = tk.Button(btn_frame, text=self.default_button_texts["add_item"], command=self.add_or_update, bg="#333333", fg="#fff")
        b1.grid(row=0, column=0, padx=5, sticky="ew")
        self.reg_buttons["add_item"] = b1

        b2 = tk.Button(btn_frame, text=self.default_button_texts["export_items"], command=self.export_items_csv, bg="#333333", fg="#fff")
        b2.grid(row=0, column=1, padx=5, sticky="ew")
        self.reg_buttons["export_items"] = b2

        b3 = tk.Button(btn_frame, text=self.default_button_texts["clear_form"], command=self.clear_form, bg="#333333", fg="#fff")
        b3.grid(row=0, column=2, padx=5, sticky="ew")
        self.reg_buttons["clear_form"] = b3

        b4 = tk.Button(btn_frame, text=self.default_button_texts["delete_item"], command=self.delete_selected_item, bg="#333333", fg="#fff")
        b4.grid(row=0, column=3, padx=5, sticky="ew")
        self.reg_buttons["delete_item"] = b4

        # Кнопка Telegram бота удалена
        
        # Индикатор статуса бота удален

        # Таблица товаров
        self.tree_frame = tk.Frame(items_frame, bg="#1e1e1e")
        self.tree_frame.grid(row=3, column=0, columnspan=8, sticky="nsew", padx=5, pady=5)

        self.tree = ttk.Treeview(self.tree_frame, columns=("Название", "Комментарий", "Покупка", "Продажа", "Ремонт", "Налог", "Средняя", "Прибыль"), show="headings")
        self.tree.heading("Название", text="Название")
        self.tree.heading("Комментарий", text="Комментарий")
        self.tree.heading("Покупка", text="Покупка")
        self.tree.heading("Продажа", text="Продажа")
        self.tree.heading("Ремонт", text="Ремонт")
        self.tree.heading("Налог", text="Налог")
        self.tree.heading("Средняя", text="Средняя")
        self.tree.heading("Прибыль", text="Прибыль")
        self.tree.column("Название", width=120)
        self.tree.column("Комментарий", width=100)
        self.tree.column("Покупка", width=70)
        self.tree.column("Продажа", width=70)
        self.tree.column("Ремонт", width=70)
        self.tree.column("Налог", width=70)
        self.tree.column("Средняя", width=70)
        self.tree.column("Прибыль", width=70)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.fill_form_from_tree)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # === ПОИСК ТОВАРОВ В ОСНОВНОМ ОКНЕ ===
        search_frame = tk.Frame(items_frame, bg="#1e1e1e")
        search_frame.grid(row=4, column=0, columnspan=8, sticky="ew", padx=5, pady=5)
        
        tk.Label(search_frame, text="Поиск товаров:", bg="#1e1e1e", fg="#fff").pack(side=tk.LEFT)
        self.main_search_entry = tk.Entry(search_frame, textvariable=self.main_search_var, width=30, bg="#333333", fg="#fff")
        self.main_search_entry.pack(side=tk.LEFT, padx=5)
        # Исправлено: trace_variable -> trace_add
        self.main_search_var.trace_add("write", lambda *args: self.filter_main_items())
        
        clear_btn = tk.Button(search_frame, text="×", bg="#555555", fg="#fff", command=self.clear_main_search, width=3)
        clear_btn.pack(side=tk.LEFT, padx=2)

        # История сделок (панель history)
        history_frame = tk.LabelFrame(self.root, text="История сделок", bg="#1e1e1e", fg="#fff")
        history_frame.grid(row=2, column=0, columnspan=8, sticky="nsew", padx=10, pady=6)
        self.panels_frames["history"] = history_frame

        tk.Label(history_frame, text="Цена сделки", bg="#1e1e1e", fg="#fff").grid(row=0, column=0, padx=5, pady=5)
        self.deal_price_entry = tk.Entry(history_frame, textvariable=self.deal_price_var, width=10)
        self.deal_price_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(history_frame, text="Тип", bg="#1e1e1e", fg="#fff").grid(row=0, column=2, padx=5, pady=5)
        self.deal_type_cb = ttk.Combobox(history_frame, textvariable=self.deal_type_var, values=["buy", "sell"], width=10)
        self.deal_type_cb.grid(row=0, column=3, padx=5, pady=5)

        self.add_deal_btn = tk.Button(history_frame, text=self.default_button_texts["add_deal"], command=self.add_deal, bg="#333333", fg="#fff")
        self.add_deal_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # Кнопка автоимпорта из 5VITO
        # Кнопка автоимпорта удалена
        self.reg_buttons["add_deal"] = self.add_deal_btn
        
        # Кнопка очистки дублей удалена
        
        # Кнопка удаления всей истории сделок
        self.clear_history_btn = tk.Button(history_frame, text="🗑️ Удалить историю", 
                                         command=self.clear_all_history, bg="#aa0000", fg="#fff", width=15)
        self.clear_history_btn.grid(row=0, column=5, padx=5, pady=5)
        
        # Кнопки быстрого режима и очистки мусора удалены
        
        # Кнопка мобильного интерфейса
        self.mobile_interface_btn = tk.Button(history_frame, text="📱 Мобильный интерфейс", 
                                            command=self.toggle_mobile_interface, bg="#0066cc", fg="#fff", width=15)
        self.mobile_interface_btn.grid(row=0, column=6, padx=5, pady=5)
        
        # Кнопка QR-кода
        self.qr_code_btn = tk.Button(history_frame, text="📱 QR-код", 
                                    command=self.show_qr_code, bg="#cc6600", fg="#fff", width=15)
        self.qr_code_btn.grid(row=0, column=7, padx=5, pady=5)
        
        # Кнопка тестирования мобильного интерфейса
        self.test_mobile_btn = tk.Button(history_frame, text="🧪 Тест Mobile", 
                                       command=self.test_mobile_interface, bg="#0066cc", fg="#fff", width=15)
        self.test_mobile_btn.grid(row=0, column=8, padx=5, pady=5)
        
        # Кнопка синхронизации
        self.sync_btn = tk.Button(history_frame, text="🔄 Синхронизация", 
                                 command=self.sync_with_mobile_interface, bg="#aa6600", fg="#fff", width=15)
        self.sync_btn.grid(row=0, column=9, padx=5, pady=5)
        
        # Кнопка очистки фантомных сделок
        self.clean_phantom_btn = tk.Button(history_frame, text="🧹 Очистить фантомы", 
                                          command=self.clean_phantom_deals, bg="#cc0000", fg="#fff", width=15)
        self.clean_phantom_btn.grid(row=0, column=10, padx=5, pady=5)

        self.history_tree = ttk.Treeview(history_frame, columns=("Дата", "Тип", "Цена", "Товар"), show="headings")
        self.history_tree.heading("Дата", text="Дата")
        self.history_tree.heading("Тип", text="Тип")
        self.history_tree.heading("Цена", text="Цена")
        self.history_tree.heading("Товар", text="Товар")
        self.history_tree.column("Дата", width=120)
        self.history_tree.column("Тип", width=80)
        self.history_tree.column("Цена", width=100)
        self.history_tree.column("Товар", width=150)

        scrollbar2 = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar2.set)
        self.history_tree.grid(row=1, column=0, columnspan=11, sticky="nsew", padx=5, pady=5)
        scrollbar2.grid(row=1, column=11, sticky="ns")
        
        # Привязка контекстного меню для истории сделок
        self.history_tree.bind("<Button-3>", self.show_history_context_menu)
        
        # Статус автоимпорта удален

        # Статистика (панель stats)
        stats_frame = tk.LabelFrame(self.root, text="Статистика", bg="#1e1e1e", fg="#fff")
        stats_frame.grid(row=3, column=0, columnspan=8, sticky="nsew", padx=10, pady=6)
        self.panels_frames["stats"] = stats_frame

        stats_labels = [
            ("Сделок", "count"),
            ("Прибыль", "profit"),
            ("Доход", "income"),
            ("Расходы", "expenses"),
            ("Итого", "net"),
            ("Средняя прибыль", "avg_profit"),
            ("Средний доход", "avg_income"),
        ]

        for i, (lbl, key) in enumerate(stats_labels):
            tk.Label(stats_frame, text=lbl + ":", bg="#1e1e1e", fg="#fff").grid(row=i//4, column=(i%4)*2, sticky="e", padx=5, pady=2)
            tk.Label(stats_frame, textvariable=self.stats_vars[key], bg="#1e1e1e", fg="#00ffcc").grid(row=i//4, column=(i%4)*2+1, sticky="w", padx=5, pady=2)

        # Настройка весов строк и колонок
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=0)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_columnconfigure(4, weight=1)
        self.root.grid_columnconfigure(5, weight=1)
        self.root.grid_columnconfigure(6, weight=1)
        self.root.grid_columnconfigure(7, weight=1)
        self.root.grid_columnconfigure(8, weight=1)
        self.root.grid_columnconfigure(9, weight=1)
        self.root.grid_columnconfigure(10, weight=1)
        self.root.grid_columnconfigure(11, weight=0)

        items_frame.grid_rowconfigure(3, weight=1)
        items_frame.grid_columnconfigure(0, weight=1)
        items_frame.grid_columnconfigure(1, weight=1)
        items_frame.grid_columnconfigure(2, weight=1)
        items_frame.grid_columnconfigure(3, weight=1)
        items_frame.grid_columnconfigure(4, weight=1)
        items_frame.grid_columnconfigure(5, weight=1)
        items_frame.grid_columnconfigure(6, weight=1)
        items_frame.grid_columnconfigure(7, weight=1)

        history_frame.grid_rowconfigure(1, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_columnconfigure(1, weight=1)
        history_frame.grid_columnconfigure(2, weight=1)
        history_frame.grid_columnconfigure(3, weight=1)
        history_frame.grid_columnconfigure(4, weight=1)
        history_frame.grid_columnconfigure(5, weight=1)
        history_frame.grid_columnconfigure(6, weight=1)
        history_frame.grid_columnconfigure(7, weight=1)
        history_frame.grid_columnconfigure(8, weight=1)
        history_frame.grid_columnconfigure(9, weight=1)
        history_frame.grid_columnconfigure(10, weight=1)

    # ---------------- ФИЛЬТРАЦИЯ ТОВАРОВ В ОСНОВНОМ ОКНЕ ----------------
    def filter_main_items(self):
        search_text = self.main_search_var.get().lower()
        if not search_text:
            # Если поиск пустой, показываем все товары
            for child in self.tree.get_children():
                self.tree.delete(child)
            for item in self.items_data:
                self.tree.insert("", tk.END, values=item)
            return
            
        # Фильтруем товары
        for child in self.tree.get_children():
            self.tree.delete(child)
            
        for item in self.items_data:
            if search_text in item[0].lower():
                self.tree.insert("", tk.END, values=item)

    def clear_main_search(self):
        self.main_search_var.set("")
        self.filter_main_items()

    # ---------------- ОСТАЛЬНЫЕ МЕТОДЫ ----------------
    def apply_ui_config(self):
        # Применяем видимость панелей
        panels = self.ui_config.get("panels", {})
        for key, frame in self.panels_frames.items():
            visible = panels.get(key, True)
            if visible:
                frame.grid()
            else:
                frame.grid_remove()
                
        # Применяем подписи кнопок
        buttons = self.ui_config.get("buttons", {})
        for key, btn in self.reg_buttons.items():
            text = buttons.get(key, self.default_button_texts.get(key, key))
            btn.config(text=text)
            
        # Обновляем текст кнопки оверлея
        if hasattr(self, 'overlay_window') and self.overlay_window.visible:
            self.toggle_overlay_btn.config(text="Оверлей Выкл")
        else:
            self.toggle_overlay_btn.config(text="Оверлей Вкл")

    def show_stats(self):
        if not self.stats_window:
            self.stats_window = StatisticsWindow(self)
        self.stats_window.show()

    def update_total_profit(self):
        total = 0.0
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            if len(values) >= 8:  # Теперь 8 полей вместо 7
                try:
                    total += float(values[7])  # Прибыль теперь в 8-м поле (индекс 7)
                except ValueError:
                    pass
        self.total_profit_var.set(f"{total:.2f}")

    def add_or_update(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введите название товара!")
            return

        buy = self.buy_var.get() or "0"
        sell = self.sell_var.get() or "0"
        repair = self.repair_var.get() or "0"
        tax = self.tax_var.get() or "0"
        avg = self.avg_price_var.get() or "0"
        comment = self.comment_var.get().strip()  # Добавляем комментарий

        try:
            buy_f = float(buy)
            sell_f = float(sell)
            repair_f = float(repair)
            tax_f = float(tax)
            avg_f = float(avg)
            profit = sell_f - buy_f - repair_f - (sell_f * tax_f / 100)
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректные числовые значения!")
            return

        # Ищем существующий товар
        found = None
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            if values and values[0] == name:
                found = child
                break

        values = (name, comment, buy, sell, repair, tax, avg, f"{profit:.2f}")  # Добавляем комментарий
        if found:
            self.tree.item(found, values=values)
        else:
            self.tree.insert("", tk.END, values=values)

        self.save_items()
        self.update_total_profit()
        self.update_combobox_values()
        self.clear_form()
        
        # Синхронизация с ботом удалена

    def clear_form(self):
        self.name_var.set("")
        self.buy_var.set("")
        self.sell_var.set("")
        self.repair_var.set("0")
        self.tax_var.set("0")
        self.avg_price_var.set("")
        self.comment_var.set("")  # Добавляем очистку комментария
        self.name_cb.focus()

    def fill_form_from_tree(self, event):
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0])["values"]
            if values:
                self.name_var.set(values[0])
                self.comment_var.set(values[1] if len(values) > 1 else "")  # Комментарий
                self.buy_var.set(values[2] if len(values) > 2 else "")
                self.sell_var.set(values[3] if len(values) > 3 else "")
                self.repair_var.set(values[4] if len(values) > 4 else "")
                self.tax_var.set(values[5] if len(values) > 5 else "")
                self.avg_price_var.set(values[6] if len(values) > 6 else "")

    def fill_form_from_selection(self, event):
        name = self.name_var.get()
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            if values and values[0] == name:
                self.comment_var.set(values[1] if len(values) > 1 else "")  # Комментарий
                self.buy_var.set(values[2] if len(values) > 2 else "")
                self.sell_var.set(values[3] if len(values) > 3 else "")
                self.repair_var.set(values[4] if len(values) > 4 else "")
                self.tax_var.set(values[5] if len(values) > 5 else "")
                self.avg_price_var.set(values[6] if len(values) > 6 else "")
                break

    def delete_selected_item(self):
        selection = self.tree.selection()
        if selection:
            name = self.tree.item(selection[0])["values"][0]
            if messagebox.askyesno("Подтверждение", f"Удалить товар '{name}'?"):
                self.tree.delete(selection[0])
                self.save_items()
                self.update_total_profit()
                self.update_combobox_values()
                
                # Синхронизируем товары с ботом
                self.sync_items_with_bot()

    def show_context_menu(self, event):
        selection = self.tree.identify_row(event.y)
        if selection:
            self.tree.selection_set(selection)
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Редактировать", command=self.fill_form_from_tree)
            menu.add_command(label="Удалить", command=self.delete_selected_item)
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def update_combobox_values(self):
        names = [self.tree.item(c)["values"][0] for c in self.tree.get_children()]
        self.name_cb['values'] = names
        if hasattr(self, 'overlay_window'):
            self.overlay_window.update_autocomplete()

    def add_deal(self):
        price = self.deal_price_var.get().strip()
        deal_type = self.deal_type_var.get().strip()
        name = self.name_var.get().strip()

        if not price or not deal_type:
            messagebox.showerror("Ошибка", "Заполните цену и тип сделки!")
            return

        try:
            price_f = float(price)
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректная цена!")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Форматируем цену для отображения в формате к/кк
        formatted_price = self._convert_number_format(price_f)
        
        # Добавляем запись в историю (только один раз)
        self._add_to_history(now, deal_type, price_f, name, formatted_price)
        
        self.save_deals()
        self.update_stats()
        self.deal_price_var.set("")

    def update_stats(self):
        count = len(self.history)
        profit = 0.0
        income = 0.0
        expenses = 0.0

        for deal in self.history:
            # Исправлено: ожидаем 4 значения вместо 6
            if len(deal) >= 4:
                dt, typ, price, name = deal[:4]  # Берем только первые 4 значения
                # Убедимся, что price - число
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = 0.0
                    
                if typ == "sell":
                    income += price
                    logger.debug(f"Продажа: {name} за ${price}, доход увеличен до ${income}")
                    # Найти товар и вычислить прибыль
                    for child in self.tree.get_children():
                        vals = self.tree.item(child)["values"]
                        if vals and vals[0] == name:
                            try:
                                buy = float(vals[2] if len(vals) > 2 else 0)  # Покупка теперь в 3-м поле
                                repair = float(vals[4] if len(vals) > 4 else 0)  # Ремонт теперь в 5-м поле
                                tax_pct = float(vals[5] if len(vals) > 5 else 0)  # Налог теперь в 6-м поле
                                tax_amt = price * tax_pct / 100
                                profit += price - buy - repair - tax_amt
                                logger.debug(f"Прибыль по {name}: ${price} - ${buy} - ${repair} - ${tax_amt} = ${price - buy - repair - tax_amt}")
                            except (ValueError, IndexError):
                                logger.warning(f"Не удалось вычислить прибыль для {name}: {vals}")
                                pass
                            break
                elif typ == "buy":
                    expenses += price
                    logger.debug(f"Покупка: {name} за ${price}, расходы увеличены до ${expenses}")

        # Статистика рассчитывается только из истории сделок

        net = income - expenses
        avg_profit = profit / count if count > 0 else 0
        avg_income = income / count if count > 0 else 0
        
        # Логируем статистику для отладки
        logger.info(f"Статистика обновлена: Всего сделок={count}, Доход={income}, Расходы={expenses}, Чистая прибыль={net}, Средняя прибыль={avg_profit}")

        self.stats_vars["count"].set(str(count))
        self.stats_vars["profit"].set(self._convert_number_format(profit))
        self.stats_vars["income"].set(self._convert_number_format(income))
        self.stats_vars["expenses"].set(self._convert_number_format(expenses))
        self.stats_vars["net"].set(self._convert_number_format(net))
        self.stats_vars["avg_profit"].set(self._convert_number_format(avg_profit))
        self.stats_vars["avg_income"].set(self._convert_number_format(avg_income))

    def toggle_overlay(self):
        if hasattr(self, 'overlay_window') and self.overlay_window.visible:
            self.overlay_window.hide()
            self.toggle_overlay_btn.config(text="Оверлей Вкл")
        else:
            self.overlay_window.show()
            self.toggle_overlay_btn.config(text="Оверлей Выкл")

    def get_visible_items(self):
        items = []
        win = None
        try:
            if self.window_var.get():
                wins = [w for w in gw.getWindowsWithTitle(self.window_var.get()) if w.isActive]
                win = wins[0] if wins else None
            else:
                win = gw.getActiveWindow()
        except Exception:
            logger.debug("Ошибка получения окна для OCR")
            return items

        if not win:
            return items
            
        try:
            if self.bbox:
                left = win.left + self.bbox[0]
                top = win.top + self.bbox[1]
                right = win.left + self.bbox[2]
                bottom = win.top + self.bbox[3]
                img = ImageGrab.grab(bbox=(left, top, right, bottom))
            else:
                img = ImageGrab.grab(bbox=(win.left, win.top, win.right, win.bottom))
                
            data = pytesseract.image_to_data(img, lang='rus+eng', output_type=pytesseract.Output.DICT)
            texts = [t.lower() for t in data.get('text', []) if str(t).strip()]
            
            for c in self.tree.get_children():
                vals = self.tree.item(c)["values"]
                name = str(vals[0]).lower()
                avg = vals[6] if len(vals) > 6 else "0"  # Средняя цена в 6-м поле
                if all(word in texts for word in name.split()):
                    items.append((vals[0], avg))
                    
        except Exception:
            logger.debug("OCR ошибка (подробности в логах)", exc_info=True)
            
        return items

    def scan_items_with_prices(self):
        """Сканирует экран и извлекает товары с ценами, сравнивает с базой данных"""
        scanned_items = []
        win = None
        
        try:
            # Используем кэширование для поиска окон
            import time
            current_time = time.time() * 1000  # в миллисекундах
            
            if (self.window_cache is None or 
                current_time - self.window_cache_time > self.window_cache_ttl):
                
                if self.window_var.get():
                    wins = [w for w in gw.getWindowsWithTitle(self.window_var.get()) if w.isActive]
                    win = wins[0] if wins else None
                else:
                    # Ищем окно RAGE Multiplayer
                    rage_windows = [w for w in gw.getAllWindows() if 'rage' in w.title.lower() or 'multiplayer' in w.title.lower()]
                    if rage_windows:
                        win = rage_windows[0]
                        # Автоматически ставим окно в фокус
                        try:
                            win.activate()
                        except Exception:
                            pass
                    else:
                        # Если RAGE Multiplayer не найдено, ищем окно GTA5
                        gta_windows = [w for w in gw.getAllWindows() if 'gta' in w.title.lower() or 'grand theft auto' in w.title.lower()]
                        if gta_windows:
                            win = gta_windows[0]
                            # Автоматически ставим окно в фокус
                            try:
                                win.activate()
                            except Exception:
                                pass
                        else:
                            # Если GTA5 не найдено, используем активное окно, но исключаем наше приложение
                            active_win = gw.getActiveWindow()
                            if active_win and 'перекуп' not in active_win.title.lower() and 'калькулятор' not in active_win.title.lower():
                                win = active_win
                            else:
                                # Ищем любое другое окно
                                all_windows = [w for w in gw.getAllWindows() if w.title and 'перекуп' not in w.title.lower() and 'калькулятор' not in w.title.lower()]
                                if all_windows:
                                    win = all_windows[0]
                                else:
                                    return scanned_items
                
                # Кэшируем результат
                self.window_cache = win
                self.window_cache_time = current_time
            else:
                # Используем кэшированное окно
                win = self.window_cache
        except Exception as e:
            logger.debug("Ошибка получения окна для OCR")
            return scanned_items

        if not win:
            return scanned_items
            
        try:
            # Оптимизация: уменьшаем размер изображения для OCR
            if self.bbox:
                left = win.left + self.bbox[0]
                top = win.top + self.bbox[1]
                right = win.left + self.bbox[2]
                bottom = win.top + self.bbox[3]
                img = ImageGrab.grab(bbox=(left, top, right, bottom))
            else:
                img = ImageGrab.grab(bbox=(win.left, win.top, win.right, win.bottom))
            
            # Оптимизированная предобработка изображения для снижения потребления памяти
            # Уменьшаем размер изображения для экономии памяти
            max_width, max_height = 1200, 800  # Ограничиваем максимальный размер
            if img.size[0] > max_width or img.size[1] > max_height:
                ratio = min(max_width / img.size[0], max_height / img.size[1])
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Конвертируем в оттенки серого для экономии памяти
            if img.mode != 'L':
                img = img.convert('L')
            
            # Упрощенная обработка изображения для экономии ресурсов
            # Только базовая контрастность без избыточной обработки
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)  # Уменьшенный фактор контрастности
                
            # OCR обработка (если Tesseract доступен)
            if HAS_TESSERACT and self.ocr_enabled:
                # Оптимизированные настройки OCR для экономии ресурсов
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюяABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:()/- '
                data = pytesseract.image_to_data(img, lang='rus+eng', output_type=pytesseract.Output.DICT, config=custom_config)
            else:
                # Заглушка для случая, когда Tesseract недоступен
                logger.debug("OCR недоступен - пропускаем сканирование")
                messagebox.showinfo("OCR недоступен", 
                                  "Функция автоматического поиска товаров недоступна.\n\n"
                                  "Для работы этой функции необходимо установить Tesseract OCR.\n"
                                  "Скачайте и установите Tesseract с официального сайта:\n"
                                  "https://github.com/UB-Mannheim/tesseract/releases")
                return scanned_items
            
            # Принудительная сборка мусора для освобождения памяти
            gc.collect()
            
            # Оптимизация: предварительно фильтруем тексты
            import re
            texts = data.get('text', [])
            lefts = data.get('left', [])
            tops = data.get('top', [])
            
            # Улучшенная фильтрация текстов для повышения точности
            filtered_texts = []
            filtered_lefts = []
            filtered_tops = []
            confidences = data.get('conf', [])
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    # Очищаем текст от мусорных символов
                    cleaned_text = (self._re_clean_text.sub('', text.strip()) if self._re_clean_text else re.sub(r'[^\w\s.,:()/-]', '', text.strip()))
                    
                    # Дополнительная фильтрация искаженных названий
                    if self._is_valid_text(cleaned_text):
                        # Фильтруем по длине и уверенности распознавания
                        if (len(cleaned_text) >= 2 and 
                            confidences[i] > self.ocr_settings['min_confidence'] and
                            not (self._re_only_specials.match(cleaned_text) if self._re_only_specials else re.match(r'^[^\w]*$', cleaned_text))):  # Не только спецсимволы
                            
                            filtered_texts.append(cleaned_text)
                            filtered_lefts.append(lefts[i])
                            filtered_tops.append(tops[i])
            
            texts = filtered_texts
            lefts = filtered_lefts
            tops = filtered_tops
            
            # Улучшенное извлечение цен с валидацией
            prices = []
            for i, text in enumerate(texts):
                if text and text.strip():
                    # Ищем числа в тексте (цены)
                    numbers = (self._re_digits.findall(text) if self._re_digits else re.findall(r'\d+', text))
                    if numbers:
                        x = lefts[i]
                        y = tops[i]
                        for num in numbers:
                            price = int(num)
                            # Фильтруем нереалистичные цены
                            if (self.ocr_settings['min_price'] <= price <= 
                                self.ocr_settings['max_price']):
                                prices.append((price, x, y))
            
            # Оптимизация: кэшируем названия товаров
            import time
            current_time = time.time() * 1000  # в миллисекундах
            
            if (self.item_names_cache is None or 
                current_time - self.item_names_cache_time > self.item_names_cache_ttl):
                
                item_names = []
                for c in self.tree.get_children():
                    vals = self.tree.item(c)["values"]
                    if len(vals) >= 7:
                        item_name = vals[0]
                        avg_price = float(vals[6]) if vals[6] else 0
                        item_names.append((item_name, avg_price))
                
                # Кэшируем результат
                self.item_names_cache = item_names
                self.item_names_cache_time = current_time
            else:
                # Используем кэшированные названия товаров
                item_names = self.item_names_cache
            
            # Для каждого товара в базе ищем его на экране и ближайшую цену
            for item_name, avg_price in item_names:
                found = False
                item_name_lower = item_name.lower()
                
                # Улучшенный поиск с нечетким сопоставлением
                item_words = item_name_lower.split()
                found_words = []
                item_positions = []
                match_scores = []
                
                # Ищем каждое слово из названия товара с нечетким сопоставлением
                for word in item_words:
                    best_match = None
                    best_score = 0
                    best_position = None
                    
                    for i, text in enumerate(texts):
                        if text:
                            text_lower = text.lower()
                            
                            # Точное совпадение
                            if word in text_lower:
                                score = 100
                            # Частичное совпадение (начало слова)
                            elif any(text_lower.startswith(w) for w in [word[:3], word[:4], word[:5]]):
                                score = 80
                            # Частичное совпадение (содержит часть слова)
                            elif any(w in text_lower for w in [word[:3], word[:4]]):
                                score = 60
                            else:
                                continue
                                
                            if score > best_score:
                                best_score = score
                                best_match = word
                                best_position = (lefts[i], tops[i])
                    
                    if best_match and best_score >= 60:
                        found_words.append(best_match)
                        item_positions.append(best_position)
                        match_scores.append(best_score)
                
                # Если найдено достаточно слов с хорошими оценками
                if (len(found_words) >= len(item_words) // 2 + 1 and 
                    sum(match_scores) / len(match_scores) >= self.ocr_settings['min_match_score']):
                    # Берем позицию первого найденного слова
                    item_x, item_y = item_positions[0]
                    
                    # Находим ближайшую цену по Y-координате (в той же строке)
                    closest_price = None
                    min_distance = float('inf')
                    
                    # Увеличиваем диапазон поиска цен - ищем в более широкой области
                    for price, px, py in prices:
                        # Проверяем, что цена в той же строке (разница по Y не больше 50 пикселей)
                        y_diff = abs(py - item_y)
                        if y_diff <= 50:
                            distance = abs(px - item_x)
                            if distance < min_distance:
                                min_distance = distance
                                closest_price = price
                    
                    # Если не нашли в расширенном диапазоне, ищем ближайшую цену вообще
                    if not closest_price and prices:
                        for price, px, py in prices:
                            # Вычисляем общее расстояние (X + Y)
                            total_distance = abs(px - item_x) + abs(py - item_y)
                            if total_distance < min_distance:
                                min_distance = total_distance
                                closest_price = price
                    
                    if closest_price:
                        scanned_items.append((item_name, str(closest_price), str(avg_price)))
                        found = True
                        break
                
                if not found:
                    # Товар не найден на экране, но показываем его с нулевой ценой
                    scanned_items.append((item_name, "0", str(avg_price)))
                        
        except Exception:
            logger.debug("OCR ошибка при сканировании товаров с ценами", exc_info=True)
        finally:
            # Принудительная очистка памяти после сканирования
            gc.collect()
            
        return scanned_items

    def _is_valid_text(self, text):
        """Проверяет, является ли текст валидным названием товара"""
        if not text or len(text) < 3:  # Увеличиваем минимальную длину
            return False
            
        # Фильтруем мусорные тексты
        garbage_patterns = [
            r'^[^\w]*$',  # Только спецсимволы
            r'^[а-яё]{1,2}$',  # Очень короткие русские слова
            r'^[a-z]{1,2}$',  # Очень короткие английские слова
            r'^[0-9]+$',  # Только цифры
            r'^[^\w\s]*$',  # Только знаки препинания
            r'^[а-яё]*[ыы]+[а-яё]*$',  # Содержит "ыы" (мусор)
            r'^[а-яё]*[а-яё]{1,2}[а-яё]*$',  # Слишком короткие части
            r'^[а-яё]*[а-яё]{1,3}$',  # Слишком короткие слова
            r'^[а-яё]*[а-яё]{1,3}[а-яё]*$',  # Содержит очень короткие части
            r'^[а-яё]*[а-яё]{1,3}[а-яё]*[а-яё]{1,3}[а-яё]*$',  # Много коротких частей
        ]
        
        for pattern in garbage_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
                
        # Проверяем на слишком много спецсимволов
        special_chars = len(re.findall(r'[^\w\s]', text))
        if special_chars > len(text) * 0.2:  # Уменьшаем до 20% спецсимволов
            return False
            
        # Проверяем на подозрительные паттерны
        suspicious_patterns = [
            r'^[а-яё]{1,3}[а-яё]{1,3}$',  # Два очень коротких слова
            r'^[а-яё]{1,2}[а-яё]{1,2}[а-яё]{1,2}$',  # Три очень коротких слова
            r'^[а-яё]*[а-яё]{1,2}[а-яё]*[а-яё]{1,2}[а-яё]*$',  # Много коротких частей
        ]
        
        for pattern in suspicious_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
            
        return True

    # ---------------- ИНТЕЛЛЕКТУАЛЬНЫЙ СКАНЕР ЛОТОВ (F7) ----------------
    def intelligent_lot_scanner(self):
        """F7: Выделение области, OCR, извлечение названия и цены, автозаполнение формы."""
        try:
            overlay = SelectionOverlay(self.root)
            # Ждем выбор области в отдельном потоке, чтобы не блокировать UI
            def worker():
                bbox = overlay.get_bbox()
                if not bbox:
                    return
                try:
                    img = ImageGrab.grab(bbox=bbox)
                    data = pytesseract.image_to_data(img, lang='rus+eng', output_type=pytesseract.Output.DICT)
                    text_lines = []
                    n = len(data.get('text', []))
                    for i in range(n):
                        t = str(data['text'][i]).strip()
                        if t:
                            text_lines.append(t)
                    full_text = " ".join(text_lines)
                    name, price = self._extract_name_and_price(full_text)
                    # Показать предпросмотр и подтверждение перед добавлением
                    def show_preview():
                        self._show_scan_preview(name, price)
                    self.root.after(0, show_preview)
                except Exception:
                    logger.exception("Ошибка в сканере лотов")
            threading.Thread(target=worker, daemon=True).start()
        except Exception:
            logger.exception("Ошибка запуска сканера лотов")

    def _handle_key_press(self, event):
        """Обработчик нажатий клавиш для tkinter (альтернатива keyboard)"""
        if event.keysym == "backslash":
            self.toggle_page_refresh()
        elif event.keysym == "F8":
            self.toggle_overlay()
        elif event.keysym == "F7":
            self.intelligent_lot_scanner()
    
    def reload_hotkeys(self):
        """Перезагрузить горячие клавиши"""
        try:
            if HAS_KEYBOARD:
                # Используем новую систему регистрации
                self._register_hotkeys()
                messagebox.showinfo("Горячие клавиши", "Горячие клавиши успешно перезагружены!")
                logger.info("Горячие клавиши перезагружены")
            else:
                messagebox.showinfo("Горячие клавиши", "Библиотека keyboard недоступна.\nИспользуются tkinter горячие клавиши.")
        except Exception as e:
            logger.exception("Ошибка при перезагрузке горячих клавиш")
            messagebox.showerror("Ошибка", f"Не удалось перезагрузить горячие клавиши:\n{str(e)}")
    
    def _register_hotkeys(self):
        """Регистрация горячих клавиш с улучшенной обработкой ошибок"""
        if HAS_KEYBOARD:
            try:
                # Очищаем все существующие горячие клавиши перед регистрацией
                keyboard.unhook_all()
                time.sleep(0.1)  # Небольшая задержка для стабильности
                
                # Регистрируем горячие клавиши с детальным логированием
                logger.info("Регистрирую горячую клавишу F8 для переключения оверлея")
                keyboard.add_hotkey("F8", self._safe_toggle_overlay, suppress=True)
                
                logger.info("Регистрирую горячую клавишу \\ для автообновления страницы")
                try:
                    # Пробуем разные варианты клавиши \
                    keyboard.add_hotkey("\\", self._safe_toggle_page_refresh, suppress=True)
                except Exception as e:
                    logger.warning(f"Не удалось зарегистрировать \\: {e}")
                    try:
                        # Альтернативный вариант
                        keyboard.add_hotkey("backslash", self._safe_toggle_page_refresh, suppress=True)
                    except Exception as e2:
                        logger.warning(f"Не удалось зарегистрировать backslash: {e2}")
                        try:
                            # Еще один вариант
                            keyboard.add_hotkey("ctrl+\\", self._safe_toggle_page_refresh, suppress=True)
                        except Exception as e3:
                            logger.error(f"Не удалось зарегистрировать ctrl+\\: {e3}")
                            # Используем F9 как альтернативу
                            keyboard.add_hotkey("F9", self._safe_toggle_page_refresh, suppress=True)
                            logger.info("Использую F9 как альтернативу для \\")
                
                logger.info("Регистрирую горячую клавишу F7 для сканера лотов")
                keyboard.add_hotkey("F7", self._safe_intelligent_lot_scanner, suppress=True)
                
                logger.info("Регистрирую горячую клавишу F6 для определения позиции мыши")
                keyboard.add_hotkey("F6", self._safe_get_mouse_position, suppress=True)
                
                logger.info("Все горячие клавиши успешно зарегистрированы")
                
            except Exception as e:
                logger.exception(f"Не удалось зарегистрировать горячие клавиши: {e}")
                # Показываем пользователю информацию об ошибке
                messagebox.showerror("Ошибка горячих клавиш", 
                                   f"Не удалось зарегистрировать горячие клавиши:\n{str(e)}\n\n"
                                   "Попробуйте запустить приложение от имени администратора.")
        else:
            logger.warning("Библиотека keyboard недоступна - регистрирую горячие клавиши через tkinter")
            # Альтернативный способ через tkinter (работает только когда окно в фокусе)
            self.root.bind("<F8>", lambda e: self.toggle_overlay())
            self.root.bind("<F7>", lambda e: self.intelligent_lot_scanner())
            self.root.bind("<F9>", lambda e: self.toggle_page_refresh())  # Альтернатива для \
            self.root.bind("<Key>", self._handle_key_press)
            messagebox.showinfo("Горячие клавиши", 
                              "Библиотека keyboard недоступна.\n"
                              "Горячие клавиши F8, F7, F9 работают только когда окно в фокусе.\n"
                              "F9 - автообновление страницы (альтернатива \\)")
    
    def _safe_toggle_overlay(self):
        """Безопасное переключение оверлея с обработкой ошибок"""
        try:
            self.toggle_overlay()
        except Exception as e:
            logger.exception("Ошибка при переключении оверлея через горячую клавишу")
    
    def _safe_toggle_page_refresh(self):
        """Безопасное переключение автообновления с обработкой ошибок"""
        try:
            self.toggle_page_refresh()
        except Exception as e:
            logger.exception("Ошибка при переключении автообновления через горячую клавишу")
    
    def _safe_intelligent_lot_scanner(self):
        """Безопасный запуск сканера лотов с обработкой ошибок"""
        try:
            self.intelligent_lot_scanner()
        except Exception as e:
            logger.exception("Ошибка при запуске сканера лотов через горячую клавишу")
    
    def _safe_get_mouse_position(self):
        """Безопасное определение позиции мыши с обработкой ошибок"""
        try:
            self.get_mouse_position()
        except Exception as e:
            logger.exception("Ошибка при определении позиции мыши через горячую клавишу")
    
    def _start_hotkeys_monitor(self):
        """Запуск мониторинга горячих клавиш"""
        if HAS_KEYBOARD and self.hotkeys_monitor_enabled:
            # Запускаем периодическую проверку каждые 30 секунд
            self._check_hotkeys_periodically()
    
    def _start_payday_monitor(self):
        """Запуск мониторинга PayDay уведомлений"""
        if self.payday_notifications_enabled:
            # Запускаем периодическую проверку каждые 30 секунд
            self._check_payday_notification()
            logger.info("Мониторинг PayDay уведомлений запущен")
    
    def _check_hotkeys_periodically(self):
        """Периодическая проверка и перерегистрация горячих клавиш"""
        if not self.hotkeys_monitor_enabled or not self.running:
            return
            
        try:
            current_time = time.time()
            # Проверяем каждые 30 секунд
            if current_time - self.hotkeys_last_check > 30:
                self.hotkeys_last_check = current_time
                
                # Проверяем, работают ли горячие клавиши
                # Если нет, перерегистрируем их
                try:
                    # Простая проверка - пытаемся зарегистрировать тестовую клавишу
                    test_key = f"ctrl+alt+{int(time.time()) % 10}"
                    keyboard.add_hotkey(test_key, lambda: None, suppress=True)
                    keyboard.remove_hotkey(test_key)
                    logger.debug("Горячие клавиши работают нормально")
                except Exception:
                    logger.warning("Обнаружена проблема с горячими клавишами, перерегистрирую...")
                    self._register_hotkeys()
                    
        except Exception as e:
            logger.exception("Ошибка при проверке горячих клавиш")
        
        # Планируем следующую проверку
        if self.running:
            self.root.after(30000, self._check_hotkeys_periodically)  # 30 секунд
    
    def _check_payday_notification(self):
        """Проверка времени для уведомления о PayDay"""
        if not self.payday_notifications_enabled or not self.running:
            return
            
        try:
            now = datetime.now()
            current_minute = now.minute
            current_hour = now.hour
            
            # Проверяем, если сейчас 49 минута
            if current_minute == 49:
                # Проверяем, не показывали ли мы уже уведомление в этот час
                notification_key = f"{current_hour}:49"
                if self.last_payday_notification != notification_key:
                    self.last_payday_notification = notification_key
                    self._show_payday_notification()
            else:
                # Сбрасываем уведомление, если не 49 минута
                self.last_payday_notification = None
                
        except Exception as e:
            logger.exception("Ошибка при проверке времени PayDay")
        
        # Планируем следующую проверку через 30 секунд
        if self.running:
            self.root.after(30000, self._check_payday_notification)
    
    def _show_payday_notification(self):
        """Показывает уведомление о PayDay"""
        try:
            now = datetime.now()
            next_hour = now.hour + 1
            if next_hour >= 24:
                next_hour = 0
            
            message = f"⚠️ PAYDAY ЧЕРЕЗ 11 МИНУТ! ⚠️\n\nСледующий PayDay в {next_hour:02d}:00"
            
            # Показываем уведомление в оверлее, если он открыт
            if hasattr(self, 'overlay_window') and self.overlay_window.visible:
                self.overlay_window.show_notification("PAYDAY ЧЕРЕЗ 11 МИНУТ!", "#ff6600", 10000)
            
            # Показываем системное уведомление
            try:
                import tkinter.messagebox as mb
                mb.showwarning("PayDay Alert", message)
            except Exception:
                pass
            
            # Логируем уведомление
            logger.info(f"PayDay уведомление показано: {message}")
            
        except Exception as e:
            logger.exception("Ошибка при показе уведомления PayDay")
    
    def _on_window_minimize(self, event):
        """Обработчик сворачивания окна - останавливаем автообновление"""
        if self.page_refresh_enabled:
            logger.info("Окно свернуто - останавливаем автообновление")
            self.page_refresh_enabled = False
            self.auto_enter_status_var.set("Автообновление: Выкл (окно свернуто)")
            
            # Обновляем статус в оверлее
            if hasattr(self, 'overlay_window'):
                self.overlay_window.update_auto_enter_status(False)
    
    def _on_window_restore(self, event):
        """Обработчик восстановления окна"""
        # Убираем избыточное логирование - это событие срабатывает слишком часто
        # logger.info("Окно восстановлено")
        # Здесь можно добавить логику восстановления состояния, если нужно
    
    # Функции автоимпорта удалены
    
    # Функции автоимпорта удалены
    # Функции автоимпорта удалены
    
    # Функции автоимпорта удалены
    
    # Функции автоимпорта удалены
    
    # Функции автоимпорта удалены
    
    # Функции автоимпорта удалены
    
    def clear_all_history(self):
        """Удаляет всю историю сделок с подтверждением"""
        try:
            # Подсчитываем количество записей
            record_count = len(self.history)
            
            if record_count == 0:
                messagebox.showinfo("Информация", "История сделок уже пуста!")
                return
            
            # Показываем диалог подтверждения
            result = messagebox.askyesno(
                "Подтверждение удаления", 
                f"Вы уверены, что хотите удалить ВСЮ историю сделок?\n\n"
                f"Будет удалено {record_count} записей.\n"
                f"Это действие нельзя отменить!",
                icon="warning"
            )
            
            if result:
                # Очищаем TreeView
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
                
                # Очищаем список истории
                self.history.clear()
                
                # Сохраняем изменения
                self.save_deals()
                
                # Обновляем статистику
                self.update_stats()
                
                # Показываем сообщение об успехе
                messagebox.showinfo("Готово", f"История сделок полностью очищена!\nУдалено {record_count} записей.")
                
                logger.info(f"История сделок полностью очищена: удалено {record_count} записей")
                
        except Exception as e:
            logger.exception("Ошибка при удалении истории сделок")
            messagebox.showerror("Ошибка", f"Не удалось удалить историю сделок:\n{str(e)}")
    
    def clean_garbage_history(self):
        """Очищает мусорные записи из истории"""
        try:
            garbage_words = ['выкл', 'сделок', 'брееа', 'line', 'woos', 'ежа', 'j 8', 'ьа', 'ен4', 'ба и', 'cae ke', '.', '..', '...', '....', '.....']
            removed_count = 0
            
            # Фильтруем историю
            filtered_history = []
            for record in self.history:
                name = record[3] if len(record) > 3 else ''  # Название товара
                
                # Проверяем на мусорные названия
                is_garbage = False
                
                # Проверка на мусорные слова
                if any(word in name.lower() for word in garbage_words):
                    is_garbage = True
                
                # Проверка на названия из цифр
                if re.match(r'^[\d\.\s]+$', name):
                    is_garbage = True
                
                # Проверка на короткие названия
                if len(name) < 3:
                    is_garbage = True
                
                if not is_garbage:
                    filtered_history.append(record)
                else:
                    removed_count += 1
            
            if removed_count > 0:
                self.history = filtered_history
                
                # Обновляем TreeView
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
                
                for record in self.history:
                    self.history_tree.insert('', 'end', values=record)
                
                # Сохраняем изменения
                self.save_deals()
                
                # Обновляем статистику
                self.update_stats()
                
                messagebox.showinfo("Очистка завершена", f"Удалено {removed_count} мусорных записей из истории")
                logger.info(f"Очищено {removed_count} мусорных записей из истории")
            else:
                messagebox.showinfo("Очистка завершена", "Мусорные записи не найдены")
                    
        except Exception as e:
            logger.exception("Ошибка при очистке мусорных записей")
            messagebox.showerror("Ошибка", f"Не удалось очистить мусорные записи:\n{str(e)}")
    
    def show_history_context_menu(self, event):
        """Показывает контекстное меню для истории сделок"""
        try:
            # Получаем выбранный элемент
            item = self.history_tree.selection()[0] if self.history_tree.selection() else None
            
            if not item:
                return
            
            # Создаем контекстное меню
            context_menu = tk.Menu(self.root, tearoff=0, bg="#2e2e2e", fg="#ffffff")
            
            # Добавляем пункты меню
            context_menu.add_command(label="🗑️ Удалить запись", command=lambda: self.delete_history_record(item))
            context_menu.add_separator()
            context_menu.add_command(label="📋 Копировать данные", command=lambda: self.copy_history_record(item))
            
            # Показываем меню
            context_menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            logger.exception("Ошибка при показе контекстного меню истории")
    
    def delete_history_record(self, item):
        """Удаляет выбранную запись из истории"""
        try:
            # Получаем данные записи
            values = self.history_tree.item(item)["values"]
            if not values:
                return
            
            # Показываем диалог подтверждения
            result = messagebox.askyesno(
                "Подтверждение удаления",
                f"Удалить запись?\n\n"
                f"Дата: {values[0]}\n"
                f"Тип: {values[1]}\n"
                f"Цена: {values[2]}\n"
                f"Товар: {values[3]}",
                icon="warning"
            )
            
            if result:
                print(f"🔍 Поиск записи для удаления: {values}")
                
                # Находим индекс записи в списке истории
                record_index = None
                for i, record in enumerate(self.history):
                    print(f"🔍 Проверяем запись {i}: {record}")
                    if (len(record) >= 4 and 
                        record[0] == values[0] and 
                        record[1] == values[1] and 
                        record[3] == values[3]):
                        # Сравниваем цену с учетом форматирования
                        record_price = float(record[2])
                        try:
                            # Пытаемся преобразовать отформатированную цену обратно в число
                            formatted_price_str = values[2].replace(',', '.').replace(' ', '')
                            print(f"🔍 Преобразуем '{values[2]}' → '{formatted_price_str}'")
                            
                            if formatted_price_str.endswith('к'):
                                formatted_price = float(formatted_price_str.replace('к', '')) * 1000
                            elif formatted_price_str.endswith('кк'):
                                formatted_price = float(formatted_price_str.replace('кк', '')) * 1000000
                            else:
                                formatted_price = float(formatted_price_str)
                            
                            print(f"🔍 Сравниваем: {record_price} vs {formatted_price} (разница: {abs(record_price - formatted_price)})")
                            
                            # Более точное сравнение с учетом округления
                            if abs(record_price - formatted_price) < 1.0:  # Учитываем погрешность округления
                                record_index = i
                                print(f"✅ Найдена запись для удаления на позиции {i} (цена: {record_price} ≈ {formatted_price})")
                                break
                        except ValueError:
                            # Если не удалось преобразовать, сравниваем как строки
                            if str(record[2]) == values[2]:
                                record_index = i
                                print(f"✅ Найдена запись для удаления на позиции {i}")
                                break
                
                if record_index is not None:
                    # Удаляем из списка истории
                    deleted_record = self.history.pop(record_index)
                    
                    # Удаляем из TreeView
                    self.history_tree.delete(item)
                    
                    # Сохраняем изменения
                    self.save_deals()
                    
                    # Обновляем статистику
                    self.update_stats()
                    
                    logger.info(f"Удалена запись из истории: {deleted_record}")
                    messagebox.showinfo("Готово", "Запись удалена из истории!")
                else:
                    print(f"⚠️ Запись не найдена в истории")
                    messagebox.showerror("Ошибка", "Не удалось найти запись в истории!")
            
        except Exception as e:
            logger.exception("Ошибка при удалении записи из истории")
            messagebox.showerror("Ошибка", f"Не удалось удалить запись:\n{str(e)}")
    
    def copy_history_record(self, item):
        """Копирует данные записи в буфер обмена"""
        try:
            values = self.history_tree.item(item)["values"]
            if not values:
                    return
            
            # Формируем текст для копирования
            text_to_copy = f"Дата: {values[0]}\nТип: {values[1]}\nЦена: {values[2]}\nТовар: {values[3]}"
            
            # Копируем в буфер обмена
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            
            messagebox.showinfo("Готово", "Данные скопированы в буфер обмена!")
            
        except Exception as e:
            logger.exception("Ошибка при копировании записи")
            messagebox.showerror("Ошибка", f"Не удалось скопировать данные:\n{str(e)}")
    
    def toggle_fast_mode(self):
        """Переключает быстрый режим автоимпорта"""
        try:
            self.auto_import_fast_mode = not self.auto_import_fast_mode
            
            if self.auto_import_fast_mode:
                self.fast_mode_btn.config(text="⚡ Быстрый режим", bg="#006600")
                messagebox.showinfo("Режим изменен", 
                    "Включен БЫСТРЫЙ режим!\n\n"
                    "• Меньше задержек между операциями\n"
                    "• Быстрее прокрутка и сканирование\n"
                    "• Может быть менее стабильным")
            else:
                self.fast_mode_btn.config(text="🐌 Обычный режим", bg="#666600")
                messagebox.showinfo("Режим изменен", 
                    "Включен ОБЫЧНЫЙ режим!\n\n"
                    "• Стандартные задержки\n"
                    "• Более стабильная работа\n"
                    "• Медленнее, но надежнее")
            
            logger.info(f"Быстрый режим автоимпорта: {'включен' if self.auto_import_fast_mode else 'выключен'}")
            
        except Exception as e:
            logger.exception("Ошибка при переключении быстрого режима")
            messagebox.showerror("Ошибка", f"Не удалось переключить режим:\n{str(e)}")
    
    def _scroll_page_down(self, window):
        """Оптимизированная прокрутка страницы вниз"""
        try:
            if HAS_PYAUTOGUI:
                # Активируем окно
                window.activate()
                time.sleep(0.05)  # Уменьшили задержку активации
                
                # Улучшенная прокрутка с адаптивным размером
                window_height = window.bottom - window.top
                scroll_amount = max(25, min(60, window_height // 15))  # Увеличили размер прокрутки
                
                # Адаптивное количество прокруток
                scroll_count = 2 if self.auto_import_fast_mode else 3
                scroll_delay = 0.02 if self.auto_import_fast_mode else 0.03
                
                # Делаем прокрутки
                for i in range(scroll_count):
                    pyautogui.scroll(-scroll_amount)
                    time.sleep(scroll_delay)
                
                # Пауза для стабилизации (адаптивная)
                stabilization_delay = self.auto_import_scroll_delay * 0.7 if self.auto_import_fast_mode else self.auto_import_scroll_delay
                time.sleep(stabilization_delay)
                
                logger.debug(f"Прокрутка выполнена: {scroll_amount}px x {scroll_count} (задержка: {stabilization_delay:.2f}s)")
                
        except Exception as e:
            logger.exception("Ошибка прокрутки страницы")
    
    # Функция _save_auto_import_settings удалена
    
    def _extract_name_and_price(self, text):
        """Грубый парсер: пытается выделить цену и разумное название из строки OCR.
        Возвращает (name:str|None, price:float|None).
        """
        if not text:
            return None, None
        # Нормализуем
        t = text.replace("\n", " ").replace("$", " ")
        # Ищем цену: число с возможными пробелами и запятыми как тысячи/разделители
        price = None
        price_match = (self._re_price_in_text.search(t) if self._re_price_in_text else re.search(r"(\d[\d\s.,]{2,})", t))
        if price_match:
            raw = price_match.group(1)
            # Удаляем пробелы-разделители тысяч, заменяем запятую на точку, но если формат тысяч через запятую, просто удалим запятые
            cleaned = raw.replace(" ", "")
            # Если есть и запятые, и точки, уберем запятые как разделители тысяч
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(",", "")
            else:
                cleaned = cleaned.replace(",", ".")
            try:
                price_val = float(cleaned)
                # Отсекаем нереалистично маленькие/большие цифры, если нужно
                if 0 < price_val < 1e10:
                    price = price_val
            except Exception:
                pass

        # Имя: возьмем текст до цены как черновик, уберем служебные символы
        name = None
        if price_match:
            prefix = t[:price_match.start()].strip()
            prefix = (self._re_clean_text.sub(" ", prefix) if self._re_clean_text else re.sub(r"[^\w\s\-._А-Яа-яЁё]", " ", prefix))
            prefix = re.sub(r"\s+", " ", prefix).strip()
            if prefix:
                name = prefix

        return name, price

    def _show_scan_preview(self, name, price):
        """Окно подтверждения: показывает распознанные название и среднюю цену.
        При подтверждении проставляет Название и Средняя цена, и добавляет/обновляет запись.
        """
        win = tk.Toplevel(self.root)
        win.title("Подтверждение лота")
        win.configure(bg="#1e1e1e")
        win.resizable(False, False)

        tk.Label(win, text="Распознанный лот", bg="#1e1e1e", fg="#ffffff", font=("Arial", 12, "bold")).pack(padx=12, pady=(10, 6))

        form = tk.Frame(win, bg="#1e1e1e")
        form.pack(padx=12, pady=6, fill="x")

        tk.Label(form, text="Название:", bg="#1e1e1e", fg="#ffffff").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        name_var = tk.StringVar(value=name or "")
        name_entry = tk.Entry(form, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, sticky="w", padx=5, pady=4)

        tk.Label(form, text="Средняя цена:", bg="#1e1e1e", fg="#ffffff").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        avg_var = tk.StringVar(value=(f"{price:.0f}" if isinstance(price, (int, float)) else ""))
        avg_entry = tk.Entry(form, textvariable=avg_var, width=20)
        avg_entry.grid(row=1, column=1, sticky="w", padx=5, pady=4)

        tk.Label(form, text="Комментарий:", bg="#1e1e1e", fg="#ffffff").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        comment_var = tk.StringVar()
        comment_entry = tk.Entry(form, textvariable=comment_var, width=40)
        comment_entry.grid(row=2, column=1, sticky="w", padx=5, pady=4)

        btns = tk.Frame(win, bg="#1e1e1e")
        btns.pack(padx=12, pady=(8, 12))

        def on_ok():
            try:
                self.name_var.set(name_var.get().strip())
                self.avg_price_var.set(avg_var.get().strip())
                self.comment_var.set(comment_var.get().strip())  # Добавляем комментарий
                # Добавляем или обновляем позицию
                self.add_or_update()
                win.destroy()
            except Exception:
                logger.exception("Ошибка подтверждения лота")

        def on_cancel():
            win.destroy()

        tk.Button(btns, text="Добавить", command=on_ok, bg="#333333", fg="#ffffff", width=14).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="Отмена", command=on_cancel, bg="#333333", fg="#ffffff", width=14).pack(side=tk.LEFT, padx=6)

        # Фокус на комментарии для удобства ввода
        comment_entry.focus_set()

    # ---------------- МАТЕМАТИЧЕСКИЙ СКАНЕР (F6) ----------------
    

    def ocr_loop(self):
        while self.running and self.ocr_enabled:
            if self.overlays_enabled:
                items = self.get_visible_items()
                try:
                    self.ocr_queue.put(items, timeout=0.5)
                except Exception:
                    pass
            time.sleep(self.overlay_refresh)

    def update_overlay_safe(self):
        if self.running and self.overlays_enabled:
            # Если в оверлее активен поиск, игнорируем OCR-обновления и чистим очередь
            try:
                if hasattr(self, 'overlay_window') and self.overlay_window.search_var.get().strip():
                    while not self.ocr_queue.empty():
                        try:
                            self.ocr_queue.get_nowait()
                        except Exception:
                            break
                elif not self.ocr_queue.empty():
                    new_items = self.ocr_queue.get()
                    try:
                        if hasattr(self, 'overlay_window'):
                            self.overlay_window.update_list(new_items)
                    except Exception:
                        logger.exception("Ошибка обновления оверлея")
            except Exception:
                logger.exception("Ошибка обработки очереди OCR")
        if self.running and self.ocr_enabled:
            # Оптимизация: увеличиваем интервал обновления для лучшей производительности
            self.root.after(200, self.update_overlay_safe)  # 200мс для лучшей производительности

    def update_window_list(self):
        try:
            if HAS_GETWINDOW and gw:
                titles = [w.title for w in gw.getAllWindows() if w.title]
                self.window_cb['values'] = titles
            else:
                self.window_cb['values'] = ["Модуль pygetwindow не установлен"]
        except Exception:
            logger.exception("Ошибка получения списка окон")

    def check_tesseract(self):
        try:
            if HAS_TESSERACT:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR найден и готов к работе")
                self.ocr_enabled = True
            else:
                self.ocr_enabled = False
                logger.warning("Tesseract OCR не установлен. Функция автоматического поиска товаров отключена.")
                messagebox.showinfo("Tesseract OCR не установлен", 
                                  "Для работы функции автоматического поиска товаров необходимо установить Tesseract OCR.\n\n"
                                  "Скачайте и установите Tesseract с официального сайта:\n"
                                  "https://github.com/UB-Mannheim/tesseract/releases\n\n"
                                  "После установки перезапустите приложение.")
        except Exception as e:
            self.ocr_enabled = False
            logger.warning(f"Tesseract OCR не найден: {e}. Функция автоматического поиска товаров отключена.")
            messagebox.showwarning("Tesseract OCR не найден", 
                                  f"Не удалось найти Tesseract OCR: {e}\n\n"
                                  "Функция автоматического поиска товаров будет отключена.\n"
                                  "Для включения установите Tesseract OCR.")

    # Метод get_coords_and_set удален
    
    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Настройки")
        settings_win.geometry("500x600")
        settings_win.configure(bg="#1e1e1e")

        # Создаем notebook (вкладки)
        notebook = ttk.Notebook(settings_win)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Вкладка основных настроек
        main_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(main_frame, text="Основные")
        
        tk.Label(main_frame, text="Прозрачность оверлея (0-1):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        alpha_var = tk.StringVar(value=str(self.overlay_alpha))
        alpha_entry = tk.Entry(main_frame, textvariable=alpha_var)
        alpha_entry.pack(pady=5)

        tk.Label(main_frame, text="Интервал обновления (сек):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        interval_var = tk.StringVar(value=str(self.overlay_refresh))
        interval_entry = tk.Entry(main_frame, textvariable=interval_var)
        interval_entry.pack(pady=5)

        tk.Label(main_frame, text="Интервал автосканирования (мс):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        auto_scan_interval_var = tk.StringVar(value=str(self.auto_scan_interval))
        auto_scan_interval_entry = tk.Entry(main_frame, textvariable=auto_scan_interval_var)
        auto_scan_interval_entry.pack(pady=5)

        tk.Label(main_frame, text="Область скриншота (left,top,right,bottom):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        bbox_var = tk.StringVar(value=str(self.bbox) if self.bbox else "")
        bbox_entry = tk.Entry(main_frame, textvariable=bbox_var, width=40)
        bbox_entry.pack(pady=5)
        
        # Вкладка настроек мобильного интерфейса
        mobile_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(mobile_frame, text="Мобильный")
        
        tk.Label(mobile_frame, text="Хост для мобильного интерфейса:", bg="#1e1e1e", fg="#fff").pack(pady=5)
        mobile_host_var = tk.StringVar(value=self.settings.get('mobile_host', '0.0.0.0'))
        mobile_host_entry = tk.Entry(mobile_frame, textvariable=mobile_host_var)
        mobile_host_entry.pack(pady=5)
        
        tk.Label(mobile_frame, text="Порт для мобильного интерфейса:", bg="#1e1e1e", fg="#fff").pack(pady=5)
        mobile_port_var = tk.StringVar(value=str(self.settings.get('mobile_port', 8080)))
        mobile_port_entry = tk.Entry(mobile_frame, textvariable=mobile_port_var)
        mobile_port_entry.pack(pady=5)
        
        # Информация о доступе
        info_text = """🌐 Настройки внешнего доступа:

• 0.0.0.0 - доступ из любой сети (по умолчанию)
• 127.0.0.1 - только локальный доступ
• [IP] - доступ только с указанного IP

📱 Для внешнего доступа:
1. Настройте проброс портов в роутере
2. Откройте порт в брандмауэре Windows
3. Используйте внешний IP адрес

⚠️ Будьте осторожны с безопасностью!"""
        
        info_label = tk.Label(mobile_frame, text=info_text, bg="#1e1e1e", fg="#ffff00", 
                             justify="left", font=("Arial", 9))
        info_label.pack(pady=10, padx=10)
        
        # Вкладка настроек OCR
        ocr_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(ocr_frame, text="OCR")
        
        tk.Label(ocr_frame, text="Фактор контрастности (1.0-3.0):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        contrast_var = tk.StringVar(value=str(self.ocr_settings['contrast_factor']))
        contrast_entry = tk.Entry(ocr_frame, textvariable=contrast_var)
        contrast_entry.pack(pady=5)
        
        tk.Label(ocr_frame, text="Фактор резкости (1.0-3.0):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        sharpness_var = tk.StringVar(value=str(self.ocr_settings['sharpness_factor']))
        sharpness_entry = tk.Entry(ocr_frame, textvariable=sharpness_var)
        sharpness_entry.pack(pady=5)
        
        tk.Label(ocr_frame, text="Минимальная уверенность OCR (0-100):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        confidence_var = tk.StringVar(value=str(self.ocr_settings['min_confidence']))
        confidence_entry = tk.Entry(ocr_frame, textvariable=confidence_var)
        confidence_entry.pack(pady=5)
        
        tk.Label(ocr_frame, text="Минимальная цена:", bg="#1e1e1e", fg="#fff").pack(pady=5)
        min_price_var = tk.StringVar(value=str(self.ocr_settings['min_price']))
        min_price_entry = tk.Entry(ocr_frame, textvariable=min_price_var)
        min_price_entry.pack(pady=5)
        
        tk.Label(ocr_frame, text="Максимальная цена:", bg="#1e1e1e", fg="#fff").pack(pady=5)
        max_price_var = tk.StringVar(value=str(self.ocr_settings['max_price']))
        max_price_entry = tk.Entry(ocr_frame, textvariable=max_price_var)
        max_price_entry.pack(pady=5)
        
        tk.Label(ocr_frame, text="Минимальная оценка совпадения (0-100):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        match_score_var = tk.StringVar(value=str(self.ocr_settings['min_match_score']))
        match_score_entry = tk.Entry(ocr_frame, textvariable=match_score_var)
        match_score_entry.pack(pady=5)
        
        tk.Label(ocr_frame, text="Фактор масштабирования изображения (1.0-2.0):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        scale_var = tk.StringVar(value=str(self.ocr_settings['image_scale_factor']))
        scale_entry = tk.Entry(ocr_frame, textvariable=scale_var)
        scale_entry.pack(pady=5)

        # Вкладка Автообновление страницы
        auto_enter_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(auto_enter_frame, text="Автообновление")
        
        tk.Label(auto_enter_frame, text="Мин задержка между обновлениями (сек)", bg="#1e1e1e", fg="#fff").pack(pady=(10, 2))
        ae_min_var = tk.StringVar(value=str(self.auto_enter_min_delay))
        ae_min_entry = tk.Entry(auto_enter_frame, textvariable=ae_min_var)
        ae_min_entry.pack(pady=2)

        tk.Label(auto_enter_frame, text="Макс задержка между обновлениями (сек)", bg="#1e1e1e", fg="#fff").pack(pady=2)
        ae_max_var = tk.StringVar(value=str(self.auto_enter_max_delay))
        ae_max_entry = tk.Entry(auto_enter_frame, textvariable=ae_max_var)
        ae_max_entry.pack(pady=2)
        
        # Настройки координат поля поиска
        tk.Label(auto_enter_frame, text="Позиция поля поиска X (0.0-1.0, 0.5=центр)", bg="#1e1e1e", fg="#fff").pack(pady=(10, 2))
        search_x_var = tk.StringVar(value=str(self.search_field_x))
        search_x_entry = tk.Entry(auto_enter_frame, textvariable=search_x_var, width=10)
        search_x_entry.pack(pady=2)
        
        tk.Label(auto_enter_frame, text="Позиция поля поиска Y (0.0-1.0, 0.1=10% от верха)", bg="#1e1e1e", fg="#fff").pack(pady=2)
        search_y_var = tk.StringVar(value=str(self.search_field_y))
        search_y_entry = tk.Entry(auto_enter_frame, textvariable=search_y_var, width=10)
        search_y_entry.pack(pady=2)
        
        # Кнопка тестирования координат
        def test_search_coordinates():
            try:
                if not self.window_var.get():
                    messagebox.showwarning("Предупреждение", "Сначала выберите окно в выпадающем списке!")
                    return
                
                # Получаем активное окно
                windows = gw.getWindowsWithTitle(self.window_var.get())
                if not windows:
                    messagebox.showerror("Ошибка", f"Окно '{self.window_var.get()}' не найдено!")
                    return
                
                active_win = windows[0]
                window_rect = active_win._rect
                
                # Вычисляем координаты
                search_x = window_rect.left + int(window_rect.width * float(search_x_var.get()))
                search_y = window_rect.top + int(window_rect.height * float(search_y_var.get()))
                
                # Кликаем в указанную точку
                if HAS_PYAUTOGUI:
                    pyautogui.click(search_x, search_y)
                    messagebox.showinfo("Тест", f"Клик выполнен в координатах ({search_x}, {search_y})\n\nЕсли клик попал в поле поиска, координаты настроены правильно!")
                else:
                    messagebox.showerror("Ошибка", "pyautogui недоступен для тестирования координат")
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при тестировании координат: {e}")
        
        # Кнопка определения позиции мыши
        def get_mouse_position():
            try:
                if HAS_PYAUTOGUI:
                    # Получаем текущую позицию мыши
                    mouse_x, mouse_y = pyautogui.position()
                    
                    # Получаем информацию об окне под курсором
                    try:
                        import ctypes
                        from ctypes import wintypes
                        
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
                        
                        message = f"""Позиция мыши: ({mouse_x}, {mouse_y})

Окно под курсором: "{window_title}"
Координаты окна: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})
Размер окна: {rect.right - rect.left} x {rect.bottom - rect.top}

Относительные координаты в окне:
X: {rel_x:.3f} (0.0-1.0)
Y: {rel_y:.3f} (0.0-1.0)

Для автообновления используйте эти относительные координаты!"""
                        
                    except Exception as e:
                        message = f"Позиция мыши: ({mouse_x}, {mouse_y})\n\nОшибка получения информации об окне: {e}"
                    
                    messagebox.showinfo("Позиция мыши", message)
                else:
                    messagebox.showerror("Ошибка", "pyautogui недоступен для определения позиции мыши")
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при определении позиции мыши: {e}")
        
        tk.Button(auto_enter_frame, text="🎯 Тест координат", command=test_search_coordinates, 
                 bg="#555555", fg="#fff").pack(pady=5)
        
        tk.Button(auto_enter_frame, text="🖱️ Позиция мыши", command=get_mouse_position, 
                 bg="#555555", fg="#fff").pack(pady=2)
        
        # Информация о автообновлении
        info_text = """Автообновление страницы:
• Один раз кликает в поле поиска при запуске
• Затем симулирует нажатие Enter 3-5 раз в секунду
• Избегает конфликтов с системными горячими клавишами
• Работает только когда целевое окно активно
• Быстрая частота обновления для активного мониторинга

ВАЖНО: Выберите окно и настройте координаты!"""
        tk.Label(auto_enter_frame, text=info_text, bg="#1e1e1e", fg="#ffff00", 
                justify=tk.LEFT, font=("Consolas", 9)).pack(pady=10)
        
        # Вкладка автоимпорта 5VITO
        # Вкладка автоимпорта удалена
        
        # Вкладка горячих клавиш
        hotkeys_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(hotkeys_frame, text="Горячие клавиши")
        
        # Статус библиотеки keyboard
        keyboard_status = "✅ Доступна" if HAS_KEYBOARD else "❌ Недоступна"
        tk.Label(hotkeys_frame, text=f"Библиотека keyboard: {keyboard_status}", 
                bg="#1e1e1e", fg="#00ff00" if HAS_KEYBOARD else "#ff0000").pack(pady=10)
        
        # Информация о горячих клавишах
        hotkeys_info = """F8 - Переключение оверлея
F7 - Сканер лотов  
F6 - Позиция мыши
\\ - Автообновление страницы (основная)
F9 - Автообновление страницы (альтернатива)

Примечание: Если библиотека keyboard недоступна,
горячие клавиши работают только когда окно в фокусе."""
        tk.Label(hotkeys_frame, text=hotkeys_info, bg="#1e1e1e", fg="#ffffff", 
                justify=tk.LEFT, font=("Consolas", 10)).pack(pady=10)
        
        # Кнопка перезагрузки горячих клавиш
        tk.Button(hotkeys_frame, text="🔄 Перезагрузить горячие клавиши", 
                 command=self.reload_hotkeys, bg="#555555", fg="#fff").pack(pady=10)
        
        # Вкладка PayDay уведомлений
        payday_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(payday_frame, text="PayDay")
        
        # Настройка включения/выключения уведомлений
        payday_var = tk.BooleanVar(value=self.payday_notifications_enabled)
        payday_check = tk.Checkbutton(payday_frame, text="Включить уведомления о PayDay", 
                                     variable=payday_var, bg="#1e1e1e", fg="#fff", 
                                     selectcolor="#333333", activebackground="#1e1e1e")
        payday_check.pack(pady=10)
        
        # Информация о PayDay уведомлениях
        payday_info = """Уведомления о PayDay показываются каждый час в 49 минут.

⚠️ PAYDAY ЧЕРЕЗ 11 МИНУТ! ⚠️

Уведомления отображаются:
• В оверлее (если открыт)
• В системном окне
• В логах приложения

Следующий PayDay происходит каждый час в :00"""
        tk.Label(payday_frame, text=payday_info, bg="#1e1e1e", fg="#ffffff", 
                justify=tk.LEFT, font=("Consolas", 9)).pack(pady=10)
        
        # Вкладка автопокупки удалена

        def save():
            try:
                self.overlay_alpha = float(alpha_var.get())
                self.overlay_refresh = float(interval_var.get())
                # Сохранение задержек автообновления
                min_d = float(ae_min_var.get())
                max_d = float(ae_max_var.get())
                if min_d <= 0 or max_d <= 0 or min_d > max_d:
                    raise ValueError("Некорректные значения задержек автообновления")
                self.auto_enter_min_delay = min_d
                self.auto_enter_max_delay = max_d
                
                # Сохранение координат поля поиска
                search_x = float(search_x_var.get())
                search_y = float(search_y_var.get())
                if not (0.0 <= search_x <= 1.0) or not (0.0 <= search_y <= 1.0):
                    raise ValueError("Координаты поля поиска должны быть от 0.0 до 1.0")
                self.search_field_x = search_x
                self.search_field_y = search_y
                
                # Сохранение настроек автоимпорта удалено
                
                # Сохранение настройки PayDay уведомлений
                self.payday_notifications_enabled = payday_var.get()
                
                # Сохранение настройки интервала автосканирования
                self.auto_scan_interval = int(auto_scan_interval_var.get())
                
                # Сохранение настроек мобильного интерфейса
                self.settings['mobile_host'] = mobile_host_var.get()
                self.settings['mobile_port'] = int(mobile_port_var.get())
                
                # Сохранение настроек OCR
                self.ocr_settings['contrast_factor'] = float(contrast_var.get())
                self.ocr_settings['sharpness_factor'] = float(sharpness_var.get())
                self.ocr_settings['min_confidence'] = int(confidence_var.get())
                self.ocr_settings['min_price'] = int(min_price_var.get())
                self.ocr_settings['max_price'] = int(max_price_var.get())
                self.ocr_settings['min_match_score'] = int(match_score_var.get())
                self.ocr_settings['image_scale_factor'] = float(scale_var.get())
                
                # Настройки автопокупки удалены
                
                bbox_text = bbox_var.get().strip()
                if bbox_text:
                    # Удаляем скобки, квадратные скобки и пробелы, затем разделяем по запятой
                    cleaned_text = bbox_text.replace('(', '').replace(')', '').replace('[', '').replace(']', '').strip()
                    parts = cleaned_text.split(",")
                    # Удаляем пробелы из каждой части
                    parts = [part.strip() for part in parts]
                    self.bbox = tuple(map(int, parts)) if parts else None
                else:
                    self.bbox = None
                # применяем прозрачность в оверлее
                try:
                    self.overlay_window.set_alpha(self.overlay_alpha)
                except Exception:
                    pass
                self.save_settings()
                settings_win.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
                logger.exception("Ошибка в настройках")

        tk.Button(settings_win, text="Сохранить", command=save, bg="#333333", fg="#fff").pack(pady=10)

    def load_settings(self):
        try:
            # Инициализируем settings как словарь
            self.settings = {}
            
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.overlay_alpha = data.get("overlay_alpha", 0.8)
                    self.overlay_refresh = data.get("overlay_refresh", 1.0)
                    self.bbox = data.get("bbox")
                    self.ocr_enabled = data.get("ocr_enabled", True)
                    self.overlays_enabled = data.get("overlays_enabled", True)
                    self.overlay_geometry = data.get("overlay_geometry", "350x650+100+100")
                    self.ui_config = data.get("ui_config", {})
                    
                    # Загружаем настройки мобильного интерфейса
                    self.settings['mobile_host'] = data.get("mobile_host", "0.0.0.0")
                    self.settings['mobile_port'] = data.get("mobile_port", 5000)
                    pr = data.get("page_refresh", {})
                    try:
                        self.auto_enter_min_delay = float(pr.get("min_delay", self.auto_enter_min_delay))
                        self.auto_enter_max_delay = float(pr.get("max_delay", self.auto_enter_max_delay))
                        self.search_field_x = float(pr.get("search_field_x", self.search_field_x))
                        self.search_field_y = float(pr.get("search_field_y", self.search_field_y))
                    except Exception:
                        pass
                        
                    # Загрузка настроек автоимпорта
                    # Загрузка настроек автоимпорта удалена
                        
                    # Загрузка настройки PayDay уведомлений
                    self.payday_notifications_enabled = data.get("payday_notifications_enabled", True)
                    
                    # Загрузка настройки интервала автосканирования
                    self.auto_scan_interval = data.get("auto_scan_interval", 2000)
                    
                    # Загрузка настроек OCR
                    ocr_settings = data.get("ocr_settings", {})
                    self.ocr_settings.update({
                        'contrast_factor': ocr_settings.get('contrast_factor', 1.5),
                        'sharpness_factor': ocr_settings.get('sharpness_factor', 2.0),
                        'min_confidence': ocr_settings.get('min_confidence', 30),
                        'min_price': ocr_settings.get('min_price', 1),
                        'max_price': ocr_settings.get('max_price', 1000000),
                        'min_match_score': ocr_settings.get('min_match_score', 70),
                        'image_scale_factor': ocr_settings.get('image_scale_factor', 1.2)
                    })
                        
                    # Загрузка настроек автопокупки удалена
            else:
                # Если файл настроек не существует, устанавливаем значения по умолчанию
                self.settings['mobile_host'] = "0.0.0.0"
                self.settings['mobile_port'] = 8080
        except Exception:
            logger.exception("Ошибка при загрузке настроек")
            # Устанавливаем значения по умолчанию в случае ошибки
            self.settings = {
                'mobile_host': "0.0.0.0",
                'mobile_port': 8080
            }

    def save_settings(self):
        try:
            data = {
                "overlay_alpha": self.overlay_alpha,
                "overlay_refresh": self.overlay_refresh,
                "bbox": self.bbox,
                "ocr_enabled": self.ocr_enabled,
                "overlays_enabled": self.overlays_enabled,
                "overlay_geometry": self.overlay_window.get_geometry() if hasattr(self, 'overlay_window') else self.overlay_geometry,
                "ui_config": self.ui_config,
                "page_refresh": {
                    "min_delay": self.auto_enter_min_delay,
                    "max_delay": self.auto_enter_max_delay,
                    "search_field_x": self.search_field_x,
                    "search_field_y": self.search_field_y
                },
                # Настройки автоимпорта удалены
                "payday_notifications_enabled": self.payday_notifications_enabled,
                "auto_scan_interval": self.auto_scan_interval,
                "ocr_settings": self.ocr_settings,
                # Настройки мобильного интерфейса
                "mobile_host": self.settings.get('mobile_host', '0.0.0.0'),
                "mobile_port": self.settings.get('mobile_port', 5000),
                # Настройки автопокупки удалены
            }
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Ошибка при сохранении настроек")

    def load_items(self):
        self.items_data = []
        if os.path.exists(ITEMS_FILE):
            try:
                with open(ITEMS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 7:  # Минимум 7 полей для старых файлов
                            # Если комментарий отсутствует, добавляем пустую строку
                            if len(row) == 7:
                                row.insert(1, "")  # Вставляем пустой комментарий после названия
                            # Если средняя цена отсутствует, добавляем "0"
                            if len(row) == 8:
                                row.append("0")  # Добавляем пустую прибыль
                            self.tree.insert("", tk.END, values=row)
                            self.items_data.append(row)
            except Exception:
                logger.exception("Ошибка при загрузке товаров")

    def save_items(self):
        try:
            with open(ITEMS_FILE, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for child in self.tree.get_children():
                    writer.writerow(self.tree.item(child)["values"])
            
            # Обновляем items_data после сохранения
            self.items_data = []
            for child in self.tree.get_children():
                self.items_data.append(self.tree.item(child)["values"])
                
            # Синхронизация с ботом удалена
        except Exception:
            logger.exception("Ошибка при сохранении товаров")
    
    # Метод синхронизации с ботом удален
    
    # Метод get_items_for_bot удален
    
    # Метод get_items_from_file_for_bot удален
    
    def update_item(self, item_name: str, item_data: dict) -> bool:
        """Обновление товара в основном приложении"""
        try:
            # Сначала пытаемся обновить в дереве, если оно существует
            if hasattr(self, 'tree') and self.tree:
                for child in self.tree.get_children():
                    values = self.tree.item(child)["values"]
                    if len(values) >= 7 and values[0] == item_name:
                        # Обновляем значения
                        new_values = list(values)
                        new_values[2] = str(item_data.get('buy_price', 0))  # Покупка
                        new_values[3] = str(item_data.get('sell_price', 0))  # Продажа
                        new_values[4] = str(item_data.get('repair', 0))  # Ремонт
                        new_values[5] = str(item_data.get('tax', 0))  # Налог
                        new_values[6] = str(item_data.get('avg_price', 0))  # Средняя
                        
                        # Обновляем в дереве
                        self.tree.item(child, values=new_values)
                        
                        # Сохраняем изменения
                        self.save_items()
                        
                        logger.info(f"✅ Товар {item_name} обновлен в дереве и файле")
                        return True
            
            # Если дерево не существует или товар не найден, обновляем через файл
            logger.info(f"🔄 Обновляем товар {item_name} через файл")
            return self.update_item_in_file(item_name, item_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления товара {item_name}: {e}")
            return False
    
    def update_item_in_file(self, item_name: str, item_data: dict) -> bool:
        """Обновление товара в файле"""
        try:
            import csv
            import os
            
            # Загружаем существующие товары
            items = []
            if os.path.exists(ITEMS_FILE):
                with open(ITEMS_FILE, 'r', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    items = list(reader)
            
            # Обновляем товар
            item_updated = False
            for i, existing_item in enumerate(items):
                if len(existing_item) >= 7 and existing_item[0].strip() == item_name:
                    # Обновляем значения
                    items[i][2] = str(item_data.get('buy_price', 0))  # Покупка
                    items[i][3] = str(item_data.get('sell_price', 0))  # Продажа
                    items[i][4] = str(item_data.get('repair', 0))  # Ремонт
                    items[i][5] = str(item_data.get('tax', 0))  # Налог
                    items[i][6] = str(item_data.get('avg_price', 0))  # Средняя
                    item_updated = True
                    break
            
            if not item_updated:
                logger.warning(f"⚠️ Товар {item_name} не найден в файле для обновления")
                return False
            
            # Сохраняем обратно в файл
            with open(ITEMS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(items)
            
            logger.info(f"✅ Товар {item_name} обновлен в файле")
            
            # Обновляем items_data если она существует
            if hasattr(self, 'items_data'):
                self.items_data = []
                for child in self.tree.get_children():
                    self.items_data.append(self.tree.item(child)["values"])
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления товара в файле {item_name}: {e}")
            return False

    def load_deals(self):
        self.history = []
        if os.path.exists(DEAL_FILE):
            try:
                with open(DEAL_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 4:
                            # Берем только первые 4 значения (дата, тип, цена, товар)
                            # Преобразуем цену в число
                            try:
                                price = float(row[2])  # Преобразуем цену в число
                                # Форматируем цену для отображения в формате к/кк
                                formatted_price = self._convert_number_format(price)
                                self.history_tree.insert("", tk.END, values=(row[0], row[1], formatted_price, row[3]))
                                self.history.append((row[0], row[1], price, row[3]))
                            except (ValueError, IndexError):
                                # Пропускаем некорректные строки
                                continue
                
                # Автоматическая очистка дублей удалена
                self.update_stats()
            except Exception:
                logger.exception("Ошибка при загрузке истории сделок")

    def save_deals(self):
        try:
            with open(DEAL_FILE, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Сохраняем данные из self.history (оригинальные цены)
                for record in self.history:
                    if len(record) >= 4:
                        # Убедимся, что все значения - строки
                        row = [str(value) for value in record]
                        writer.writerow(row)
            logger.debug(f"Сохранено {len(self.history)} записей в историю сделок")
        except Exception:
            logger.exception("Ошибка при сохранении истории сделок")

    # ---------------- АВТООБНОВЛЕНИЕ СТРАНИЦЫ ----------------
    def toggle_page_refresh(self):
        """Переключить автообновление страницы по нажатию клавиши \\ (backslash) или F9."""
        try:
            self.page_refresh_enabled = not self.page_refresh_enabled
            if self.page_refresh_enabled:
                logger.info("🔄 Автообновление страницы: ВКЛ")
                self.auto_enter_status_var.set("Автообновление: Вкл")
                
                # Проверяем, что keyboard доступен
                if not HAS_KEYBOARD:
                    logger.warning("⚠️ Библиотека keyboard недоступна, автообновление может работать нестабильно")
                
                # Проверяем, что выбрано окно
                if not self.window_var.get():
                    logger.warning("⚠️ Не выбрано окно для автообновления")
                
                # Сбрасываем флаг клика при включении
                self.search_field_clicked = False
                
                # Показываем уведомление в оверлее
                if hasattr(self, 'overlay_window'):
                    self.overlay_window.update_auto_enter_status(True)
                
                # Запускаем поток автообновления
                if not self.page_refresh_thread or not self.page_refresh_thread.is_alive():
                    self.page_refresh_thread = threading.Thread(target=self._page_refresh_loop, daemon=True, name="PageRefreshThread")
                    self.page_refresh_thread.start()
                    logger.info("✅ Поток автообновления запущен")
                else:
                    logger.info("✅ Поток автообновления уже работает")
                    
                # Логируем успешное включение (без всплывающего окна)
                logger.info("✅ Автообновление страницы ВКЛЮЧЕНО! Нажмите \\ или F9 для выключения")
                    
            else:
                logger.info("🔄 Автообновление страницы: ВЫКЛ")
                self.auto_enter_status_var.set("Автообновление: Выкл")
                
                # Сбрасываем флаг клика при выключении
                self.search_field_clicked = False
                
                # Показываем уведомление в оверлее
                if hasattr(self, 'overlay_window'):
                    self.overlay_window.update_auto_enter_status(False)
                    
                # Логируем успешное выключение (без всплывающего окна)
                logger.info("❌ Автообновление страницы ВЫКЛЮЧЕНО! Нажмите \\ или F9 для включения")
                    
        except Exception as e:
            logger.error(f"Ошибка переключения автообновления: {e}")
            messagebox.showerror("Ошибка", f"Ошибка переключения автообновления:\n{str(e)}")

    # Функция toggle_auto_buy удалена
        
    def _page_refresh_loop(self):
        """Цикл обновления страницы с человеческой скоростью и случайностью, пока не выключат."""
        if not HAS_KEYBOARD:
            logger.warning("Библиотека keyboard недоступна, автообновление отключено")
            self.page_refresh_enabled = False
            return
            
        # Счетчик для периодических пауз
        action_count = 0
        
        while self.running and self.page_refresh_enabled:
            try:
                # Активно ли выбранное окно и не активен ли наш GUI
                active_win = None
                try:
                    active_win = gw.getActiveWindow()
                except Exception:
                    pass

                # Безопасная проверка фокуса приложения
                try:
                    app_has_focus = self.root.focus_get() is not None
                except Exception:
                    # Если проверка фокуса не работает, считаем что приложение не в фокусе
                    app_has_focus = False
                target_ok = True

                if self.window_var.get():
                    # Обновляем только если в фокусе окно с выбранным заголовком
                    target_ok = active_win and self.window_var.get() in (active_win.title or "")

                if not app_has_focus and target_ok:
                    # Увеличиваем счетчик действий
                    action_count += 1
                    
                    # Периодические длинные паузы (каждые 10-30 действий)
                    if action_count % random.randint(10, 30) == 0:
                        long_pause = random.uniform(3.0, 10.0)  # 3-10 секунд паузы
                        logger.debug(f"Длинная пауза: {long_pause:.1f}с (действие #{action_count})")
                        time.sleep(long_pause)
                        continue
                    
                    # Случайные короткие паузы (каждые 3-8 действий)
                    if action_count % random.randint(3, 8) == 0:
                        short_pause = random.uniform(1.0, 3.0)  # 1-3 секунды
                        logger.debug(f"Короткая пауза: {short_pause:.1f}с (действие #{action_count})")
                        time.sleep(short_pause)
                    
                    # Обновление страницы с небольшой случайной задержкой
                    time.sleep(random.uniform(0.1, 0.3))
                    self._refresh_page()
                    
            except Exception:
                logger.exception("Ошибка обновления страницы")
                time.sleep(0.5)
                
            # Имитируем человеческий темп согласно настройкам
            delay = random.uniform(self.auto_enter_min_delay, self.auto_enter_max_delay)
            time.sleep(delay)

    def _refresh_page(self):
        """Обновляет страницу в выбранном окне через поиск + Enter."""
        try:
            if HAS_PYAUTOGUI:
                # Получаем активное окно
                active_win = gw.getActiveWindow()
                if active_win:
                    # Получаем координаты окна
                    window_rect = active_win._rect
                    
                    # Координаты поля поиска (используем настраиваемые относительные координаты)
                    search_x = window_rect.left + int(window_rect.width * self.search_field_x)
                    search_y = window_rect.top + int(window_rect.height * self.search_field_y)
                    
                    # Кликаем в поле поиска только один раз при первом запуске
                    if not self.search_field_clicked:
                        pyautogui.click(search_x, search_y)
                        time.sleep(0.2)  # Задержка для активации поля
                        self.search_field_clicked = True
                        logger.debug(f"Активация поля поиска: клик в ({search_x}, {search_y})")
                    
                    # Симулируем нажатие Enter без реального нажатия клавиши
                    # Это позволяет избежать конфликтов с системными горячими клавишами
                    self._simulate_enter_press()
                    logger.debug("Симуляция нажатия Enter для обновления")
                    
            else:
                # Если pyautogui недоступен, используем альтернативный способ
                if not self.search_field_clicked:
                    keyboard.send("tab")  # Переходим к полю поиска
                    time.sleep(0.1)
                    self.search_field_clicked = True
                    logger.debug("Активация поля поиска: Tab")
                
                # Симулируем Enter
                self._simulate_enter_press()
                logger.debug("Симуляция нажатия Enter")
                    
        except Exception as e:
            logger.exception(f"Ошибка при обновлении страницы: {e}")
            # Fallback - обычное обновление
            try:
                keyboard.send("f5")
                logger.debug("Fallback: F5")
            except:
                pass
    
    def _simulate_enter_press(self):
        """Симулирует нажатие Enter без реального нажатия клавиши."""
        try:
            # Попытка 1: Используем Windows API для отправки события напрямую в активное окно
            if self._send_enter_to_active_window():
                logger.debug("Enter отправлен через Windows API")
                return
            
            # Попытка 2: Используем pyautogui для более точного контроля
            if HAS_PYAUTOGUI:
                # Получаем активное окно
                active_win = gw.getActiveWindow()
                if active_win:
                    # Отправляем Enter только в это окно
                    pyautogui.press('enter')
                    time.sleep(0.05)
                    logger.debug("Enter отправлен через pyautogui")
                    return
            
            # Fallback: обычный keyboard.send
            keyboard.send("enter")
            time.sleep(0.05)
            logger.debug("Enter отправлен через keyboard")
            
        except Exception as e:
            logger.debug(f"Ошибка симуляции Enter: {e}")
            # Последний fallback
            try:
                keyboard.send("enter")
            except:
                pass
    
    def _send_enter_to_active_window(self):
        """Отправляет Enter напрямую в активное окно через Windows API."""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Получаем handle активного окна
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd == 0:
                return False
            
            # Отправляем сообщение WM_KEYDOWN для Enter (VK_RETURN = 0x0D)
            VK_RETURN = 0x0D
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            
            # Нажатие клавиши
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
            time.sleep(0.01)
            # Отпускание клавиши
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)
            
            return True
            
        except Exception as e:
            logger.debug(f"Ошибка Windows API: {e}")
            return False

    def get_mouse_position(self):
        """Определяет текущую позицию мыши и показывает информацию об окне под курсором."""
        try:
            if HAS_PYAUTOGUI:
                # Получаем текущую позицию мыши
                mouse_x, mouse_y = pyautogui.position()
                
                # Получаем информацию об окне под курсором
                try:
                    import ctypes
                    from ctypes import wintypes
                    
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
                    
                    message = f"""🖱️ Позиция мыши: ({mouse_x}, {mouse_y})

🪟 Окно под курсором: "{window_title}"
📐 Координаты окна: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})
📏 Размер окна: {rect.right - rect.left} x {rect.bottom - rect.top}

🎯 Относительные координаты в окне:
X: {rel_x:.3f} (0.0-1.0)
Y: {rel_y:.3f} (0.0-1.0)

💡 Для автообновления используйте эти относительные координаты!"""
                    
                except Exception as e:
                    message = f"🖱️ Позиция мыши: ({mouse_x}, {mouse_y})\n\n❌ Ошибка получения информации об окне: {e}"
                
                # Показываем уведомление в оверлее, если он открыт
                if hasattr(self, 'overlay_window') and self.overlay_window.visible:
                    self.overlay_window.show_notification(f"Мышь: ({mouse_x}, {mouse_y})", "#00ff00", 3000)
                
                # Показываем диалог с подробной информацией
                import tkinter.messagebox as mb
                mb.showinfo("Позиция мыши", message)
                
                logger.info(f"Позиция мыши: ({mouse_x}, {mouse_y})")
                
            else:
                import tkinter.messagebox as mb
                mb.showerror("Ошибка", "pyautogui недоступен для определения позиции мыши")
                
        except Exception as e:
            logger.exception(f"Ошибка при определении позиции мыши: {e}")
            import tkinter.messagebox as mb
            mb.showerror("Ошибка", f"Ошибка при определении позиции мыши: {e}")

    def export_items_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Название", "Покупка", "Продажа", "Ремонт", "Налог", "Средняя", "Прибыль"])
                    for child in self.tree.get_children():
                        writer.writerow(self.tree.item(child)["values"])
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
            except Exception:
                logger.exception("Ошибка при экспорте CSV")
                messagebox.showerror("Ошибка", "Не удалось экспортировать данные")

    def _convert_number_format(self, number):
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
            logger.warning(f"Ошибка конвертации числа '{number}' в формат к/кк: {e}")
            return str(number)

    def _parse_transaction_date(self, date_str):
        """Парсинг даты транзакции из строки формата 'DD/MM HH:MM'"""
        try:
            if not date_str or not date_str.strip():
                return None
                
            # Очищаем строку от лишних символов
            date_str = date_str.strip()
            
            # Ищем паттерн даты: DD/MM HH:MM
            date_match = re.match(r'(\d{2})/(\d{2})\s+(\d{2}):(\d{2})', date_str)
            if date_match:
                day, month, hour, minute = map(int, date_match.groups())
                
                # Получаем текущий год
                current_year = datetime.now().year
                
                # Создаем объект даты
                transaction_date = datetime(current_year, month, day, hour, minute)
                
                # Если дата в будущем, значит это прошлый год
                if transaction_date > datetime.now():
                    transaction_date = datetime(current_year - 1, month, day, hour, minute)
                
                return transaction_date.strftime("%Y-%m-%d %H:%M:%S")
            
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка парсинга даты '{date_str}': {e}")
            return None

    def on_close(self):
        self.running = False
        # Останавливаем мониторинг горячих клавиш
        self.hotkeys_monitor_enabled = False
        # Гасим автоспам Enter
        self.auto_enter_enabled = False
        # Останавливаем автоимпорт
        self.auto_import_running = False
        
        # Даем потокам шанс завершиться
        try:
            if self.auto_enter_thread and self.auto_enter_thread.is_alive():
                self.auto_enter_thread.join(timeout=0.5)
        except Exception:
            pass
            
        try:
            if self.auto_import_thread and self.auto_import_thread.is_alive():
                self.auto_import_thread.join(timeout=0.5)
        except Exception:
            pass
            
        if hasattr(self, 'overlay_window'):
            self.overlay_window.destroy()
        
        # Очищаем горячие клавиши
        if HAS_KEYBOARD:
            try:
                keyboard.unhook_all()
                logger.info("Горячие клавиши очищены при закрытии")
            except Exception as e:
                logger.warning(f"Ошибка при очистке горячих клавиш: {e}")
        
        # Сохраняем все данные перед закрытием
        self.save_settings()
        self.save_deals()
        self.save_items()
        self.root.destroy()
    
    def get_safety_recommendations(self):
        """Возвращает рекомендации по безопасному использованию"""
        return {
            "ocr_safety": [
                "✅ OCR работает только с видимым на экране",
                "✅ Не читает память игры напрямую",
                "✅ Относительно безопасен для античита",
                "⚠️ Не используйте 24/7 - делайте перерывы",
                "⚠️ Имитируйте поведение человека"
            ],
            "auto_enter_safety": [
                "✅ Имитирует нажатия клавиш как человек",
                "✅ Случайные задержки и паузы",
                "✅ Останавливается при сворачивании окна",
                "⚠️ Не используйте слишком долго подряд",
                "⚠️ Делайте перерывы каждые 30-60 минут"
            ],
            "general_safety": [
                "🚫 НЕ читайте память игры напрямую",
                "🚫 НЕ модифицируйте файлы игры",
                "🚫 НЕ используйте DLL injection",
                "✅ Используйте только OCR и автоматизацию",
                "✅ Делайте перерывы в работе",
                "✅ Имитируйте человеческое поведение"
            ]
        }

    # ================= МОБИЛЬНЫЙ ИНТЕРФЕЙС =================
    def start_mobile_interface(self):
        """Запускает мобильный веб-интерфейс"""
        try:
            if not self.mobile_interface_enabled:
                logger.info("📱 Мобильный интерфейс отключен в настройках")
                return
                
            logger.info("📱 Запуск мобильного интерфейса...")
            
            # Проверяем, что Flask доступен
            try:
                import flask
                logger.info(f"✅ Flask версия: {flask.__version__}")
            except ImportError as e:
                logger.error(f"❌ Flask не установлен: {e}")
                messagebox.showerror("Ошибка", "Flask не установлен!\n\nУстановите Flask командой:\npip install flask")
                return
            
            self.mobile_interface = MobileInterface(self)
            
            # Получаем настройки из конфига
            mobile_host = self.settings.get('mobile_host', '0.0.0.0')
            mobile_port = self.settings.get('mobile_port', 5000)
            
            logger.info(f"📱 Настройки мобильного интерфейса: {mobile_host}:{mobile_port}")
            
            # Проверяем доступность порта
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex((mobile_host, mobile_port))
                if result == 0:
                    logger.warning(f"⚠️ Порт {mobile_port} уже занят, попробуем другой порт")
                    # Пробуем найти свободный порт
                    for port in range(mobile_port + 1, mobile_port + 10):
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        result = sock.connect_ex((mobile_host, port))
                        if result != 0:
                            mobile_port = port
                            logger.info(f"✅ Найден свободный порт: {port}")
                            break
                        sock.close()
                    else:
                        logger.error("❌ Не удалось найти свободный порт")
                        messagebox.showerror("Ошибка", f"Не удалось найти свободный порт в диапазоне {mobile_port}-{mobile_port + 9}")
                        return
                sock.close()
            except Exception as e:
                logger.warning(f"⚠️ Не удалось проверить порт: {e}")
            
            # Запускаем в отдельном потоке
            self.mobile_interface_thread = threading.Thread(
                target=lambda: self.mobile_interface.run(host=mobile_host, port=mobile_port, debug=False),
                daemon=True,
                name="MobileInterface"
            )
            self.mobile_interface_thread.start()
            
            # Даем время на запуск
            time.sleep(1)
            
            # Проверяем, что поток запустился
            if self.mobile_interface_thread.is_alive():
                logger.info(f"🌐 Мобильный интерфейс запущен на {mobile_host}:{mobile_port}")
                
                # Получаем IP адрес для отображения
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    
                    url = f"http://{local_ip}:{mobile_port}"
                    logger.info(f"📱 URL для мобильного доступа: {url}")
                    
                    # Показываем уведомление с URL
                    messagebox.showinfo("Мобильный интерфейс", 
                        f"Мобильный интерфейс запущен!\n\n"
                        f"URL для доступа:\n{url}\n\n"
                        f"Откройте этот адрес в браузере на телефоне")
                        
                except Exception as e:
                    logger.warning(f"Не удалось получить IP адрес: {e}")
                    messagebox.showinfo("Мобильный интерфейс", 
                        f"Мобильный интерфейс запущен на порту {mobile_port}!\n\n"
                        f"Используйте IP адрес вашего компьютера для доступа")
            else:
                logger.error("❌ Не удалось запустить мобильный интерфейс")
                messagebox.showerror("Ошибка", "Не удалось запустить мобильный интерфейс")
            
        except Exception as e:
            logger.error(f"Ошибка запуска мобильного интерфейса: {e}")
            messagebox.showerror("Ошибка", f"Ошибка запуска мобильного интерфейса:\n{str(e)}")
    
    def add_mobile_deal(self, deal):
        """Добавляет сделку из мобильного интерфейса в основное приложение"""
        try:
            print(f"📱 Начинаем добавление сделки: {deal}")
            
            # Валидация данных
            if not deal or 'name' not in deal or 'price' not in deal or 'type' not in deal:
                print(f"❌ Неполные данные сделки: {deal}")
                return False
            
            # Создаем запись в истории в том же формате, что и обычные сделки
            # Формат: (дата, тип, цена, название, ID)
            history_record = (
                deal.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                deal['type'],
                float(deal['price']),
                deal['name'],
                deal.get('id', int(time.time() * 1000))  # Добавляем ID для возможности удаления
            )
            
            print(f"📱 Создана запись истории: {history_record}")
            
            # Добавляем в историю
            self.history.append(history_record)
            print(f"📱 Запись добавлена в историю. Всего записей: {len(self.history)}")
            
            # Сохраняем историю
            self.save_deals()
            print(f"📱 История сохранена")
            
            # Обновляем GUI в главном потоке
            self.root.after(0, self.update_total_profit)
            self.root.after(0, self._update_history_display)
            print(f"📱 GUI обновлен")
            
            logger.info(f"📱 Добавлена сделка из мобильного интерфейса: {deal['name']} - ${deal['price']}")
            print(f"✅ Сделка успешно добавлена: {deal['name']} - ${deal['price']} ({deal['type']})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления мобильной сделки: {e}")
            print(f"❌ Ошибка добавления сделки: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _update_history_display(self):
        """Обновляет отображение истории сделок в GUI"""
        try:
            if hasattr(self, 'history_tree'):
                # Очищаем текущее содержимое
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
                
                # Добавляем все записи из истории
                for record in self.history:
                    if len(record) >= 4:
                        # Форматируем цену для отображения
                        try:
                            price = float(record[2]) if isinstance(record[2], (int, float)) else float(record[2])
                            formatted_price = self._convert_number_format(price)
                            self.history_tree.insert("", tk.END, values=(record[0], record[1], formatted_price, record[3]))
                        except (ValueError, IndexError) as e:
                            # Если не удалось отформатировать, используем как есть
                            logger.warning(f"Ошибка форматирования записи {record}: {e}")
                            self.history_tree.insert("", tk.END, values=record[:4])
                
                logger.debug(f"Обновлено отображение истории: {len(self.history)} записей")
                
        except Exception as e:
            logger.error(f"Ошибка обновления отображения истории: {e}")
    
    def remove_mobile_deal(self, deal_id):
        """Удаляет сделку из основного приложения по ID"""
        try:
            print(f"🔍 Поиск сделки с ID: {deal_id}")
            print(f"📊 Всего записей в истории: {len(self.history)}")
            
            # Ищем сделку в истории по ID
            removed = False
            removed_records = []
            
            # Проходим по истории в обратном порядке для безопасного удаления
            for i in range(len(self.history) - 1, -1, -1):
                record = self.history[i]
                print(f"🔍 Проверяем запись {i}: {record}")
                
                if len(record) >= 4:
                    # Проверяем ID в 5-м поле (если есть)
                    if len(record) > 4 and str(record[4]) == str(deal_id):
                        removed_record = self.history.pop(i)
                        removed_records.append(removed_record)
                        removed = True
                        print(f"✅ Удалена запись с ID {deal_id}: {removed_record}")
                        break
            
            if removed:
                # Сохраняем изменения
                self.save_deals()
                print(f"📱 История сохранена после удаления")
                
                # Обновляем GUI
                self.root.after(0, self.update_total_profit)
                self.root.after(0, self._update_history_display)
                print(f"📱 GUI обновлен после удаления")
                
                logger.info(f"📱 Удалена сделка из основного приложения: ID {deal_id}")
                print(f"✅ Сделка удалена: ID {deal_id}")
                return True
            else:
                logger.warning(f"📱 Сделка с ID {deal_id} не найдена в основном приложении")
                print(f"⚠️ Сделка с ID {deal_id} не найдена")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка удаления мобильной сделки: {e}")
            print(f"❌ Ошибка удаления сделки: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_all_deals_for_mobile(self):
        """Возвращает все сделки в формате для мобильного интерфейса"""
        try:
            deals = []
            for record in self.history:
                if len(record) >= 4:
                    deal = {
                        'id': record[4] if len(record) > 4 else int(time.time() * 1000),
                        'name': record[3],
                        'price': float(record[2]),
                        'quantity': 1,
                        'type': record[1],
                        'date': record[0],
                        'source': 'main'
                    }
                    deals.append(deal)
            return deals
        except Exception as e:
            logger.error(f"Ошибка получения сделок для мобильного интерфейса: {e}")
            return []
    
    def clean_phantom_deals(self):
        """Очищает фантомные сделки и дубликаты"""
        try:
            print("🧹 Начинаем очистку фантомных сделок...")
            original_count = len(self.history)
            
            # Удаляем дубликаты по комбинации дата+тип+цена+название
            seen_deals = set()
            cleaned_history = []
            
            for record in self.history:
                if len(record) >= 4:
                    # Создаем ключ для проверки дубликатов
                    deal_key = (record[0], record[1], str(record[2]), record[3])
                    
                    if deal_key not in seen_deals:
                        seen_deals.add(deal_key)
                        cleaned_history.append(record)
                    else:
                        print(f"🗑️ Удален дубликат: {record}")
            
            # Обновляем историю
            self.history = cleaned_history
            
            # Сохраняем изменения
            self.save_deals()
            
            # Обновляем GUI
            self.root.after(0, self.update_total_profit)
            self.root.after(0, self._update_history_display)
            
            removed_count = original_count - len(self.history)
            print(f"✅ Очистка завершена: удалено {removed_count} фантомных/дублирующихся записей")
            logger.info(f"Очищено {removed_count} фантомных/дублирующихся записей")
            
            if removed_count > 0:
                messagebox.showinfo("Очистка завершена", f"Удалено {removed_count} фантомных/дублирующихся записей")
            else:
                messagebox.showinfo("Очистка завершена", "Фантомные записи не найдены")
                
        except Exception as e:
            logger.error(f"Ошибка очистки фантомных сделок: {e}")
            messagebox.showerror("Ошибка", f"Не удалось очистить фантомные сделки:\n{str(e)}")
    
    def sync_with_mobile_interface(self):
        """Синхронизирует данные с мобильным интерфейсом"""
        try:
            if not self.mobile_interface_enabled or not self.mobile_interface:
                messagebox.showinfo("Информация", "Мобильный интерфейс не запущен")
                return
                
            # Отправляем все сделки в мобильный интерфейс
            mobile_deals = []
            for record in self.history:
                if len(record) >= 4:
                    # Создаем объект сделки для мобильного интерфейса
                    deal = {
                        'id': record[4] if len(record) > 4 else int(time.time() * 1000),
                        'name': record[3],
                        'price': float(record[2]),
                        'quantity': 1,
                        'type': record[1],
                        'date': record[0],
                        'source': 'main_app'
                    }
                    mobile_deals.append(deal)
            
            # Сохраняем в мобильный файл
            self.mobile_interface.save_deals(mobile_deals)
            
            logger.info(f"📱 Синхронизировано {len(mobile_deals)} сделок с мобильным интерфейсом")
            print(f"📱 Синхронизировано {len(mobile_deals)} сделок")
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации с мобильным интерфейсом: {e}")
            print(f"❌ Ошибка синхронизации: {e}")
    
    def get_all_deals_for_mobile(self):
        """Возвращает все сделки в формате для мобильного интерфейса"""
        try:
            deals = []
            for record in self.history:
                if len(record) >= 4:
                    deal = {
                        'id': record[4] if len(record) > 4 else int(time.time() * 1000),
                        'name': record[3],
                        'price': float(record[2]),
                        'quantity': 1,
                        'type': record[1],
                        'date': record[0],
                        'source': 'main_app'
                    }
                    deals.append(deal)
            return deals
        except Exception as e:
            logger.error(f"Ошибка получения сделок для мобильного интерфейса: {e}")
            return []
    
    def get_items_for_mobile(self):
        """Возвращает список товаров для мобильного интерфейса"""
        try:
            items = []
            for child in self.tree.get_children():
                values = self.tree.item(child)["values"]
                if len(values) >= 7:
                    try:
                        item = {
                            'name': values[0],  # Название
                            'buy_price': self._safe_float(values[1]),  # Покупка
                            'sell_price': self._safe_float(values[2]),  # Продажа
                            'repair': self._safe_float(values[3]),  # Ремонт
                            'tax': self._safe_float(values[4]),  # Налог
                            'avg_price': self._safe_float(values[5]),  # Средняя цена
                            'profit': self._safe_float(values[6]),  # Прибыль
                            'comment': values[7] if len(values) > 7 and values[7] else ''  # Комментарий
                        }
                        items.append(item)
                    except Exception as item_error:
                        logger.warning(f"Ошибка обработки товара {values[0]}: {item_error}")
                        continue
            return items
        except Exception as e:
            logger.error(f"Ошибка получения товаров для мобильного интерфейса: {e}")
            return []
    
    def _safe_float(self, value):
        """Безопасное преобразование в float"""
        try:
            if not value or value == '':
                return 0.0
            # Убираем пробелы и заменяем запятые на точки
            clean_value = str(value).strip().replace(',', '.')
            return float(clean_value)
        except (ValueError, TypeError):
            return 0.0
    
    def get_all_deals_for_mobile(self):
        """Возвращает все сделки для мобильного интерфейса"""
        try:
            deals = []
            for deal in self.history:
                if len(deal) >= 4:
                    dt, typ, price, name = deal[:4]
                    deals.append({
                        'date': dt,
                        'type': 'Продажа' if typ == 'sell' else 'Покупка',
                        'price': self._safe_float(price),
                        'name': name
                    })
            return deals
        except Exception as e:
            logger.error(f"Ошибка получения сделок для мобильного интерфейса: {e}")
            return []
    
    def delete_deal_from_mobile(self, deal_id):
        """Удаляет сделку из мобильного интерфейса"""
        try:
            # Удаляем сделку из истории
            deleted_deal = self.history.pop(deal_id)
            
            # Сохраняем историю
            self.save_deals()
            
            # Обновляем статистику
            self.update_stats()
            
            # Обновляем отображение истории
            self._update_history_display()
            
            logger.info(f"Сделка удалена из мобильного интерфейса: {deal_id} - {deleted_deal}")
            
        except Exception as e:
            logger.error(f"Ошибка удаления сделки из мобильного интерфейса: {e}")
            raise
    
    def update_deal_in_mobile(self, deal_id, deal_data):
        """Обновляет сделку в мобильном интерфейсе"""
        try:
            # Конвертируем тип сделки
            deal_type = 'sell' if deal_data.get('type') == 'Продажа' else 'buy'
            
            # Обновляем сделку в истории
            self.history[deal_id] = [
                deal_data.get('date', ''),
                deal_type,
                str(deal_data.get('price', 0)),
                deal_data.get('name', '')
            ]
            
            # Сохраняем историю
            self.save_deals()
            
            # Обновляем статистику
            self.update_stats()
            
            # Обновляем отображение истории
            self._update_history_display()
            
            logger.info(f"Сделка обновлена в мобильном интерфейсе: {deal_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления сделки в мобильном интерфейсе: {e}")
            raise
    
    def add_deal_from_mobile(self, deal):
        """Добавляет сделку из мобильного интерфейса"""
        try:
            # Конвертируем тип сделки
            deal_type = 'sell' if deal['type'] == 'Продажа' else 'buy'
            
            # Добавляем в историю
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            deal_record = [timestamp, deal_type, str(deal['price']), deal['name']]
            self.history.append(deal_record)
            
            # Сохраняем историю
            self.save_deals()
            
            # Обновляем статистику
            self.update_stats()
            
            # Обновляем отображение истории
            self._update_history_display()
            
            logger.info(f"Сделка добавлена из мобильного интерфейса: {deal}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления сделки из мобильного интерфейса: {e}")
            raise
    
    def toggle_mobile_interface(self):
        """Переключает мобильный интерфейс"""
        try:
            if self.mobile_interface_enabled:
                # Останавливаем
                if self.mobile_interface:
                    # Flask сервер остановится автоматически при завершении потока
                    self.mobile_interface = None
                self.mobile_interface_enabled = False
                logger.info("📱 Мобильный интерфейс остановлен")
                messagebox.showinfo("Информация", "Мобильный интерфейс отключен")
            else:
                # Запускаем
                self.mobile_interface_enabled = True
                self.start_mobile_interface()
                logger.info("📱 Мобильный интерфейс запущен")
                messagebox.showinfo("Информация", "Мобильный интерфейс включен")
                
        except Exception as e:
            logger.error(f"Ошибка переключения мобильного интерфейса: {e}")
    
    def get_mobile_interface_url(self):
        """Возвращает URL мобильного интерфейса"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            port = self.settings.get('mobile_port', 5000)
            url = f"http://{local_ip}:{port}"
            logger.info(f"📱 URL мобильного интерфейса: {url}")
            return url
        except Exception as e:
            logger.warning(f"Не удалось получить IP адрес: {e}")
            port = self.settings.get('mobile_port', 5000)
            return f"http://localhost:{port}"
    
    def setup_mobile_access(self):
        """Настройка внешнего доступа к мобильному интерфейсу"""
        try:
            import subprocess
            import os
            
            # Запускаем скрипт настройки
            script_path = os.path.join(os.path.dirname(__file__), "setup_external_access.py")
            if os.path.exists(script_path):
                subprocess.Popen([sys.executable, script_path], shell=True)
            else:
                # Если скрипт не найден, показываем инструкции
                self.show_mobile_setup_instructions()
                
        except Exception as e:
            logger.error(f"Ошибка запуска настройки мобильного доступа: {e}")
            self.show_mobile_setup_instructions()
    
    def show_mobile_setup_instructions(self):
        """Показывает инструкции по настройке мобильного доступа"""
        try:
            import socket
            from tkinter import messagebox
            
            # Получаем IP адреса
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
            
            port = self.settings.get('mobile_port', 5000)
            
            instructions = f"""🌐 Настройка внешнего доступа к мобильному интерфейсу

📱 Ваши адреса:
• Локально: http://localhost:{port}
• В сети: http://{local_ip}:{port}

🔧 Для внешнего доступа:
1. Настройте проброс портов в роутере
2. Откройте порт {port} в брандмауэре Windows
3. Используйте внешний IP адрес

⚙️ Настройки в программе:
• Откройте Настройки → Мобильный
• Хост: 0.0.0.0 (для внешнего доступа)
• Порт: {port}

⚠️ Будьте осторожны с безопасностью!"""
            
            messagebox.showinfo("Настройка мобильного доступа", instructions)
            
        except Exception as e:
            logger.error(f"Ошибка показа инструкций: {e}")
    
    def test_mobile_interface(self):
        """Тестирует мобильный интерфейс"""
        try:
            logger.info("🧪 Тестирование мобильного интерфейса...")
            
            # Проверяем, что Flask доступен
            try:
                import flask
                logger.info(f"✅ Flask версия: {flask.__version__}")
            except ImportError as e:
                logger.error(f"❌ Flask не установлен: {e}")
                messagebox.showerror("Ошибка", "Flask не установлен!\n\nУстановите Flask командой:\npip install flask")
                return
            
            # Проверяем, что мобильный интерфейс включен
            if not self.mobile_interface_enabled:
                logger.warning("⚠️ Мобильный интерфейс отключен")
                messagebox.showwarning("Предупреждение", "Мобильный интерфейс отключен!\n\nВключите его в настройках или нажмите кнопку 'Мобильный интерфейс'")
                return
            
            # Проверяем, что поток запущен
            if not hasattr(self, 'mobile_interface_thread') or not self.mobile_interface_thread.is_alive():
                logger.warning("⚠️ Мобильный интерфейс не запущен")
                messagebox.showwarning("Предупреждение", "Мобильный интерфейс не запущен!\n\nПопробуйте перезапустить его")
                return
            
            # Получаем URL
            url = self.get_mobile_interface_url()
            
            # Тестируем подключение
            try:
                import urllib.request
                import urllib.error
                
                # Пробуем подключиться к мобильному интерфейсу
                response = urllib.request.urlopen(url, timeout=5)
                if response.getcode() == 200:
                    logger.info(f"✅ Мобильный интерфейс работает: {url}")
                    messagebox.showinfo("Тест успешен", 
                        f"✅ Мобильный интерфейс работает!\n\n"
                        f"URL: {url}\n\n"
                        f"Откройте этот адрес в браузере на телефоне")
                else:
                    logger.warning(f"⚠️ Мобильный интерфейс отвечает с кодом: {response.getcode()}")
                    messagebox.showwarning("Предупреждение", 
                        f"Мобильный интерфейс отвечает с кодом {response.getcode()}\n\n"
                        f"URL: {url}")
                        
            except urllib.error.URLError as e:
                logger.error(f"❌ Не удалось подключиться к мобильному интерфейсу: {e}")
                messagebox.showerror("Ошибка", 
                    f"Не удалось подключиться к мобильному интерфейсу!\n\n"
                    f"URL: {url}\n\n"
                    f"Ошибка: {e}\n\n"
                    f"Проверьте:\n"
                    f"• Запущен ли мобильный интерфейс\n"
                    f"• Правильно ли настроен порт\n"
                    f"• Не блокирует ли брандмауэр подключение")
            except Exception as e:
                logger.error(f"❌ Ошибка тестирования: {e}")
                messagebox.showerror("Ошибка", f"Ошибка тестирования мобильного интерфейса:\n{str(e)}")
                
        except Exception as e:
            logger.error(f"Ошибка тестирования мобильного интерфейса: {e}")
            messagebox.showerror("Ошибка", f"Ошибка тестирования мобильного интерфейса:\n{str(e)}")

    def show_qr_code(self):
        """Показывает QR-код для мобильного интерфейса"""
        try:
            if not self.mobile_interface_enabled:
                messagebox.showwarning("Предупреждение", "Мобильный интерфейс не запущен!")
                return
                
            # Получаем URL мобильного интерфейса
            url = self.get_mobile_interface_url()
            
            # Создаем окно QR-кода
            self.create_qr_window(url)
            
        except Exception as e:
            logger.error(f"Ошибка показа QR-кода: {e}")
            messagebox.showerror("Ошибка", f"Не удалось показать QR-код: {e}")
    
    def create_qr_window(self, url):
        """Создает окно с QR-кодом"""
        try:
            # Создаем новое окно
            qr_window = tk.Toplevel(self.root)
            qr_window.title("QR-код для мобильного интерфейса")
            qr_window.geometry("400x500")
            qr_window.configure(bg="#1e1e1e")
            qr_window.resizable(False, False)
            
            # Заголовок
            title_label = tk.Label(
                qr_window, 
                text="📱 QR-код для мобильного интерфейса",
                font=("Arial", 16, "bold"),
                bg="#1e1e1e",
                fg="#ffffff"
            )
            title_label.pack(pady=20)
            
            # URL
            url_label = tk.Label(
                qr_window,
                text=f"URL: {url}",
                font=("Arial", 10),
                bg="#1e1e1e",
                fg="#00ff00",
                wraplength=350
            )
            url_label.pack(pady=10)
            
            # Фрейм для QR-кода
            qr_frame = tk.Frame(qr_window, bg="#1e1e1e")
            qr_frame.pack(pady=20)
            
            # Создаем QR-код
            self.generate_qr_in_window(qr_frame, url)
            
            # Кнопки
            button_frame = tk.Frame(qr_window, bg="#1e1e1e")
            button_frame.pack(pady=20)
            
            # Кнопка открытия в браузере
            open_btn = tk.Button(
                button_frame,
                text="🌐 Открыть в браузере",
                command=lambda: webbrowser.open(url),
                bg="#00aa00",
                fg="#ffffff",
                font=("Arial", 12),
                padx=20,
                pady=10
            )
            open_btn.pack(side=tk.LEFT, padx=10)
            
            # Кнопка копирования URL
            copy_btn = tk.Button(
                button_frame,
                text="📋 Копировать URL",
                command=lambda: self.copy_url_to_clipboard(url, qr_window),
                bg="#0066aa",
                fg="#ffffff",
                font=("Arial", 12),
                padx=20,
                pady=10
            )
            copy_btn.pack(side=tk.LEFT, padx=10)
            
            # Инструкции
            instructions = tk.Label(
                qr_window,
                text="📋 Инструкции:\n1. Отсканируйте QR-код камерой телефона\n2. Или введите URL вручную\n3. Убедитесь, что телефон в той же Wi-Fi сети",
                font=("Arial", 10),
                bg="#1e1e1e",
                fg="#cccccc",
                justify=tk.LEFT
            )
            instructions.pack(pady=20)
            
        except Exception as e:
            logger.error(f"Ошибка создания окна QR-кода: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать окно QR-кода: {e}")
    
    def generate_qr_in_window(self, parent_frame, url):
        """Генерирует QR-код в указанном фрейме"""
        try:
            if not HAS_QRCODE:
                print("❌ Библиотека qrcode не установлена")
                self._show_qr_fallback(parent_frame, url)
                return
                
            print(f"🔧 Создание QR-кода для URL: {url}")
            
            # Создаем QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Создаем изображение
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменяем размер для отображения
            img = img.resize((120, 120), Image.Resampling.LANCZOS)
            
            # Сохраняем во временный файл
            temp_file = "temp_qr_main.png"
            img.save(temp_file)
            
            # Загружаем из файла
            qr_image = ImageTk.PhotoImage(file=temp_file)
            
            # Отображаем QR-код
            qr_label = tk.Label(parent_frame, image=qr_image, bg="#1e1e1e")
            qr_label.image = qr_image  # Сохраняем ссылку
            qr_label.pack()
            
            # Удаляем временный файл
            try:
                os.remove(temp_file)
            except:
                pass
            
            print(f"✅ QR-код успешно создан и отображен")
            
        except Exception as e:
            print(f"❌ Ошибка создания QR-кода: {e}")
            import traceback
            traceback.print_exc()
            self._show_qr_fallback(parent_frame, url)
    
    def _show_qr_fallback(self, parent_frame, url):
        """Показывает текстовое сообщение вместо QR-кода"""
        text_label = tk.Label(
            parent_frame, 
            text=f"📱 Мобильный интерфейс\n\nURL для ввода вручную:\n{url}\n\n📋 Инструкции:\n1. Откройте браузер на телефоне\n2. Введите URL выше\n3. Убедитесь, что телефон в той же Wi-Fi сети",
            bg="#1e1e1e",
            fg="#00ff00",
            font=("Arial", 11, "bold"),
            justify=tk.CENTER,
            wraplength=350
        )
        text_label.pack()
    
    def copy_url_to_clipboard(self, url, window):
        """Копирует URL в буфер обмена"""
        try:
            window.clipboard_clear()
            window.clipboard_append(url)
            messagebox.showinfo("Успех", f"URL скопирован в буфер обмена:\n{url}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать URL: {e}")

    # Функции автоимпорта и очистки дублей полностью удалены
    
    # Метод start_telegram_bot удален
    
    # Метод start_bot_console удален
    
    # Метод update_bot_status_indicator удален
    
    # Метод show_bot_notification удален
    
    # Метод show_bot_info удален
    
    # Метод show_bot_setup_guide удален
    
    def check_tesseract(self):
        """Проверка наличия Tesseract OCR"""
        try:
            if HAS_TESSERACT:
                # Пробуем выполнить простую команду
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR найден и готов к работе")
                return True
            else:
                logger.warning("Tesseract OCR не установлен")
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки Tesseract: {e}")
            return False
    
    # Метод get_stats_for_bot удален
    
    # Метод get_items_for_bot удален
    
    # Метод get_items_from_file_for_bot удален
    
    # Метод calculate_deal_profit_for_bot удален
    
    def sync_with_mobile_interface(self):
        """Синхронизация с мобильным интерфейсом"""
        try:
            logger.info("🔄 Синхронизация с мобильным интерфейсом...")
            
            if not self.mobile_interface_enabled:
                messagebox.showwarning("Предупреждение", "Мобильный интерфейс не запущен!")
                return
                
            # Обновляем данные в мобильном интерфейсе
            if hasattr(self, 'mobile_interface') and self.mobile_interface:
                # Обновляем товары
                self.mobile_interface.update_items_data()
                # Обновляем статистику
                self.mobile_interface.update_stats_data()
                
                logger.info("✅ Синхронизация завершена")
                messagebox.showinfo("Синхронизация", "✅ Данные синхронизированы с мобильным интерфейсом!")
            else:
                logger.warning("⚠️ Мобильный интерфейс не инициализирован")
                messagebox.showwarning("Предупреждение", "Мобильный интерфейс не инициализирован!")
                
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
            messagebox.showerror("Ошибка", f"Ошибка синхронизации:\n{str(e)}")
    
    def clean_phantom_deals(self):
        """Очистка фантомных сделок"""
        try:
            logger.info("🧹 Очистка фантомных сделок...")
            
            # Подсчитываем количество записей до очистки
            initial_count = len(self.history)
            
            # Фильтруем фантомные сделки (пустые или с некорректными данными)
            cleaned_history = []
            for record in self.history:
                if len(record) >= 4 and record[0] and record[1] and record[2] and record[3]:
                    # Проверяем, что все поля заполнены
                    if str(record[0]).strip() and str(record[1]).strip() and str(record[2]).strip() and str(record[3]).strip():
                        cleaned_history.append(record)
            
            # Обновляем историю
            self.history = cleaned_history
            removed_count = initial_count - len(self.history)
            
            # Сохраняем изменения
            self.save_deals()
            
            # Обновляем отображение
            self.update_history_display()
            self.update_total_profit()
            
            logger.info(f"✅ Очистка завершена. Удалено {removed_count} фантомных записей")
            messagebox.showinfo("Очистка завершена", 
                f"✅ Очистка фантомных сделок завершена!\n\n"
                f"Удалено записей: {removed_count}\n"
                f"Осталось записей: {len(self.history)}")
                
        except Exception as e:
            logger.error(f"Ошибка очистки фантомных сделок: {e}")
            messagebox.showerror("Ошибка", f"Ошибка очистки фантомных сделок:\n{str(e)}")


def _start_winapi_hotkeys_for_app(app):
    """Глобальные хоткеи через WinAPI для F8 и \\ (фолбэк, если keyboard не ловит вне фокуса)."""
    try:
        import ctypes
        import ctypes.wintypes as wt
        user32 = ctypes.windll.user32
        MOD_NOREPEAT = 0x4000
        HOTKEY_ID_F8 = 1
        HOTKEY_ID_BS = 2

        # Регистрируем F8
        if not user32.RegisterHotKey(None, HOTKEY_ID_F8, MOD_NOREPEAT, 0x77):  # VK_F8
            return False

        # Регистрируем backslash (или F9 при неудаче)
        if not user32.RegisterHotKey(None, HOTKEY_ID_BS, MOD_NOREPEAT, 0xDC):  # VK_OEM_5
            user32.RegisterHotKey(None, HOTKEY_ID_BS, MOD_NOREPEAT, 0x78)      # VK_F9

        # Сохраняем для последующей отписки
        app._winapi_user32 = user32
        app._winapi_hotkey_ids = (HOTKEY_ID_F8, HOTKEY_ID_BS)

        def loop():
            msg = wt.MSG()
            while getattr(app, 'running', True):
                res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res == 0 or res == -1:
                    break
                if msg.message == 0x0312:  # WM_HOTKEY
                    if msg.wParam == HOTKEY_ID_F8:
                        app.root.after(0, app._safe_toggle_overlay)
                    elif msg.wParam == HOTKEY_ID_BS:
                        app.root.after(0, app._safe_toggle_page_refresh)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        t = threading.Thread(target=loop, daemon=True, name="WinHotkeysThread")
        t.start()
        return True
    except Exception:
        logger.exception("WinAPI хоткеи не удалось запустить (фолбэк)")
        return False


def _stop_winapi_hotkeys_for_app(app):
    try:
        if hasattr(app, '_winapi_user32') and hasattr(app, '_winapi_hotkey_ids'):
            user32 = app._winapi_user32
            f8_id, bs_id = app._winapi_hotkey_ids
            try:
                user32.UnregisterHotKey(None, f8_id)
            except Exception:
                pass
            try:
                user32.UnregisterHotKey(None, bs_id)
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    root = tk.Tk()
    app = TraderApp(root)
    # Пытаемся запустить глобальные WinAPI хоткеи как дополнительный фолбэк
    _start_winapi_hotkeys_for_app(app)

    # Оборачиваем on_close, чтобы корректно снять регистрацию хоткеев
    try:
        _orig_on_close = app.on_close
        def _wrapped_on_close():
            try:
                _stop_winapi_hotkeys_for_app(app)
            finally:
                _orig_on_close()
        app.on_close = _wrapped_on_close
        root.protocol("WM_DELETE_WINDOW", app.on_close)
    except Exception:
        pass

    root.mainloop()