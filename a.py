# gta5_rp_calculator_enhanced.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv, os, json, threading, time, logging, traceback, sys
from queue import Queue
from datetime import datetime

# OCR / скриншоты
import pytesseract
from PIL import ImageGrab

# Окна
import pygetwindow as gw

# Опционально: глобальные хоткеи
try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False

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

# Путь к tesseract (при необходимости раскомментируй и настрой)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ================= УЛУЧШЕННЫЙ ОВЕРЛЕЙ =================
class OverlayWindow:
    def __init__(self, app, alpha=0.8, geometry="350x650+100+100"):
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
        
        # Кнопка обновления
        self.refresh_btn = tk.Button(self.title_bar, text="↻", bg="#555555", fg="#fff",
                                   command=self.update_list_from_app, width=3, font=("Arial", 9))
        self.refresh_btn.pack(side=tk.RIGHT, padx=2)
        
        # Кнопка закрытия
        self.close_btn = tk.Button(self.title_bar, text="×", bg="#333333", fg="#fff", 
                                 bd=0, command=self.hide, font=("Arial", 12, "bold"), width=3)
        self.close_btn.pack(side=tk.RIGHT, padx=2)

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

        # === ПОИСК ТОВАРОВ ===
        self.search_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.search_frame.pack(fill=tk.X, padx=8, pady=5)
        
        tk.Label(self.search_frame, text="Поиск:", bg="#1e1e1e", fg="#fff").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, width=20, bg="#333333", fg="#fff")
        self.search_entry.pack(side=tk.LEFT, padx=5)
        # Исправлено: trace_variable -> trace_add
        self.search_var.trace_add("write", lambda *args: self.filter_items())
        
        # Кнопка очистки поиска
        self.clear_search_btn = tk.Button(self.search_frame, text="×", bg="#555555", fg="#fff",
                                        command=self.clear_search, width=3)
        self.clear_search_btn.pack(side=tk.LEFT, padx=2)

        # === ФОРМА ДОБАВЛЕНИЯ ===
        self.add_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.add_frame.pack(fill=tk.X, padx=8, pady=5)
        
        tk.Label(self.add_frame, text="Название:", bg="#1e1e1e", fg="#fff").grid(row=0, column=0, sticky="w")
        
        # Автодополнение названий
        self.name_combo = ttk.Combobox(self.add_frame, width=18)
        self.name_combo.grid(row=0, column=1, padx=2)
        self.name_combo.bind("<Return>", lambda e: self.price_entry.focus())
        
        tk.Label(self.add_frame, text="Цена:", bg="#1e1e1e", fg="#fff").grid(row=0, column=2, sticky="w")
        self.price_entry = tk.Entry(self.add_frame, width=10, bg="#333333", fg="#fff")
        self.price_entry.grid(row=0, column=3, padx=2)
        self.price_entry.bind("<Return>", lambda e: self.add_item_from_overlay())

        # === TREEVIEW ===
        self.tree_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        
        self.tree = ttk.Treeview(self.tree_frame, columns=("Название", "Средняя цена"), 
                               show="headings", style="Overlay.Treeview", height=12)
        
        # Настройка колонок
        self.tree.heading("Название", text="Название", command=lambda: self.sort_treeview("Название", False))
        self.tree.heading("Средняя цена", text="Цена", command=lambda: self.sort_treeview("Средняя цена", False))
        self.tree.column("Название", width=180, anchor=tk.W)
        self.tree.column("Средняя цена", width=80, anchor=tk.CENTER)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
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

        # === СТАТУС БАР ===
        self.status_bar = tk.Label(self.root, text="Готов к работе", bg="#333333", fg="#00ff00", 
                                  anchor=tk.W, font=("Arial", 9))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # === ОБРАБОТЧИКИ СОБЫТИЙ ===
        self.tree.bind("<Double-1>", self.edit_item_from_overlay)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#333333", fg="#fff")
        self.context_menu.add_command(label="Редактировать", command=self.edit_selected)
        self.context_menu.add_command(label="Удалить", command=self.delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Копировать название", command=self.copy_name)
        self.context_menu.add_command(label="Копировать цену", command=self.copy_price)

        # Обработчик изменения размера
        self.root.bind("<Configure>", self.on_resize)

    # === ОСНОВНЫЕ МЕТОДЫ ===
    def add_item_from_overlay(self):
        name = self.name_combo.get().strip()
        price = self.price_entry.get().strip()
        
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
        self.price_entry.delete(0, tk.END)
        
        # Фокусируемся на поле названия
        self.name_combo.focus()
        
        # Обновляем список и автодополнение
        self.update_list_from_app()
        self.update_autocomplete()
        
        self.show_notification(f"Товар '{name}' добавлен!", "#00ff00")

    def edit_item_from_overlay(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item['values']
            if values:
                self.name_combo.set(values[0])
                self.price_entry.delete(0, tk.END)
                self.price_entry.insert(0, values[1] if len(values) > 1 else "")
                self.price_entry.focus()

    def update_list_from_app(self):
        """Обновляет список из данных основного приложения"""
        items = []
        for child in self.app.tree.get_children():
            vals = self.app.tree.item(child)["values"]
            if len(vals) >= 6:
                items.append((vals[0], vals[5]))
        self.update_list(items)

    def update_list(self, items):
        try:
            self.tree.delete(*self.tree.get_children())
            for name, avg in items:
                self.tree.insert("", tk.END, values=(name, avg))
                
            # Обновляем статус бар
            count = len(items)
            self.status_bar.config(text=f"Товаров: {count} | Готов")
            
        except Exception:
            logger.exception("Ошибка при обновлении списка оверлея")

    def update_autocomplete(self):
        """Обновляет список автодополнения"""
        names = [self.app.tree.item(c)["values"][0] for c in self.app.tree.get_children()]
        self.name_combo['values'] = names

    # === ФИЛЬТРАЦИЯ И ПОИСК ===
    def filter_items(self):
        search_text = self.search_var.get().lower()
        if not search_text:
            self.update_list_from_app()
            return
            
        filtered_items = []
        for child in self.app.tree.get_children():
            vals = self.app.tree.item(child)["values"]
            if len(vals) >= 6 and search_text in vals[0].lower():
                filtered_items.append((vals[0], vals[5]))
                
        self.update_list(filtered_items)
        self.status_bar.config(text=f"Найдено: {len(filtered_items)} товаров")

    def clear_search(self):
        self.search_var.set("")
        self.update_list_from_app()

    # === КОНТЕКСТНОЕ МЕНЮ ===
    def show_context_menu(self, event):
        selection = self.tree.identify_row(event.y)
        if selection:
            self.tree.selection_set(selection)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def edit_selected(self):
        self.edit_item_from_overlay(None)

    def delete_selected(self):
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

    def copy_name(self):
        selection = self.tree.selection()
        if selection:
            name = self.tree.item(selection[0])["values"][0]
            self.root.clipboard_clear()
            self.root.clipboard_append(name)
            self.show_notification("Название скопировано!", "#00ff00")

    def copy_price(self):
        selection = self.tree.selection()
        if selection and len(self.tree.item(selection[0])["values"]) > 1:
            price = self.tree.item(selection[0])["values"][1]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(price))
            self.show_notification("Цена скопирована!", "#00ff00")

    # === ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ===
    def toggle_alpha(self):
        self.alpha = 0.3 if self.alpha == 0.8 else 0.8
        self.set_alpha(self.alpha)
        status = "Прозрачный" if self.alpha == 0.3 else "Непрозрачный"
        self.show_notification(f"Режим: {status}", "#00ff00")

    def show_notification(self, message, color="#00ff00"):
        """Показывает уведомление в статус баре"""
        self.status_bar.config(text=message, fg=color)
        self.root.after(3000, lambda: self.status_bar.config(text="Готов", fg="#00ff00"))

    def sort_treeview(self, col, reverse):
        """Сортировка Treeview"""
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

    def on_resize(self, event):
        """Обработчик изменения размера окна"""
        if event.widget == self.root:
            self.status_bar.config(text=f"Размер: {event.width}x{event.height}")

    # === БАЗОВЫЕ МЕТОДЫ ===
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def hide(self):
        if self.visible:
            try:
                self.root.withdraw()
            except Exception:
                pass
            self.visible = False

    def show(self):
        if not self.visible:
            try:
                self.root.deiconify()
                self.root.lift()
            except Exception:
                pass
            self.visible = True
            self.update_list_from_app()
            self.update_autocomplete()
            self.name_combo.focus()

    def set_alpha(self, alpha):
        self.alpha = alpha
        try:
            self.root.attributes("-alpha", alpha)
        except Exception:
            pass

    def get_geometry(self):
        try:
            return self.root.geometry()
        except Exception:
            return ""

    def destroy(self):
        try:
            self.root.destroy()
        except:
            pass


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
        self.overlay_refresh = 1.0
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
            "show_stats": "Показать статистику"
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
        
        # Окно статистики
        self.stats_window = None

        # Загружаем настройки/данные
        self.load_settings()
        self.setup_gui()
        self.load_items()
        self.load_deals()
        self.update_total_profit()

        # Проверяем Tesseract
        self.check_tesseract()

        # Оверлей - создаем после setup_gui
        self.overlay_window = OverlayWindow(self, alpha=self.overlay_alpha, geometry=self.overlay_geometry)
        if not self.overlays_enabled:
            self.overlay_window.hide()

        # Запускаем OCR-поток если включён
        if self.ocr_enabled:
            self.ocr_thread = threading.Thread(target=self.ocr_loop, daemon=True, name="OCRThread")
            self.ocr_thread.start()
            self.root.after(100, self.update_overlay_safe)

        # Горячая клавиша F8 (если есть библиотека keyboard)
        if HAS_KEYBOARD:
            try:
                keyboard.add_hotkey("F8", self.toggle_overlay)
            except Exception:
                logger.exception("Не удалось зарегать горячую клавишу F8 через библиотеку keyboard")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Применяем UI конфиг (подписи кнопок, видимость панелей)
        self.apply_ui_config()
        
        # Обновляем комбобокс после создания оверлея
        self.update_combobox_values()
        
        # Обновляем список окон
        self.update_window_list()

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

        # Таблица товаров
        self.tree_frame = tk.Frame(items_frame, bg="#1e1e1e")
        self.tree_frame.grid(row=3, column=0, columnspan=8, sticky="nsew", padx=5, pady=5)

        self.tree = ttk.Treeview(self.tree_frame, columns=("Название", "Покупка", "Продажа", "Ремонт", "Налог", "Средняя", "Прибыль"), show="headings")
        self.tree.heading("Название", text="Название")
        self.tree.heading("Покупка", text="Покупка")
        self.tree.heading("Продажа", text="Продажа")
        self.tree.heading("Ремонт", text="Ремонт")
        self.tree.heading("Налог", text="Налог")
        self.tree.heading("Средняя", text="Средняя")
        self.tree.heading("Прибыль", text="Прибыль")
        self.tree.column("Название", width=150)
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
        self.reg_buttons["add_deal"] = self.add_deal_btn

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
        self.history_tree.grid(row=1, column=0, columnspan=5, sticky="nsew", padx=5, pady=5)
        scrollbar2.grid(row=1, column=5, sticky="ns")

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
            if len(values) >= 7:
                try:
                    total += float(values[6])
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

        values = (name, buy, sell, repair, tax, avg, f"{profit:.2f}")
        if found:
            self.tree.item(found, values=values)
        else:
            self.tree.insert("", tk.END, values=values)

        self.save_items()
        self.update_total_profit()
        self.update_combobox_values()
        self.clear_form()

    def clear_form(self):
        self.name_var.set("")
        self.buy_var.set("")
        self.sell_var.set("")
        self.repair_var.set("0")
        self.tax_var.set("0")
        self.avg_price_var.set("")
        self.name_cb.focus()

    def fill_form_from_tree(self, event):
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0])["values"]
            if values:
                self.name_var.set(values[0])
                self.buy_var.set(values[1])
                self.sell_var.set(values[2])
                self.repair_var.set(values[3])
                self.tax_var.set(values[4])
                self.avg_price_var.set(values[5])

    def fill_form_from_selection(self, event):
        name = self.name_var.get()
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            if values and values[0] == name:
                self.buy_var.set(values[1])
                self.sell_var.set(values[2])
                self.repair_var.set(values[3])
                self.tax_var.set(values[4])
                self.avg_price_var.set(values[5])
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
        self.history_tree.insert("", tk.END, values=(now, deal_type, price_f, name))
        self.history.append((now, deal_type, price_f, name))
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
                    # Найти товар и вычислить прибыль
                    for child in self.tree.get_children():
                        vals = self.tree.item(child)["values"]
                        if vals and vals[0] == name:
                            try:
                                buy = float(vals[1])
                                repair = float(vals[3])
                                tax_pct = float(vals[4])
                                tax_amt = price * tax_pct / 100
                                profit += price - buy - repair - tax_amt
                            except (ValueError, IndexError):
                                pass
                            break
                elif typ == "buy":
                    expenses += price

        net = income - expenses
        avg_profit = profit / count if count > 0 else 0
        avg_income = income / count if count > 0 else 0

        self.stats_vars["count"].set(str(count))
        self.stats_vars["profit"].set(f"{profit:.2f}")
        self.stats_vars["income"].set(f"{income:.2f}")
        self.stats_vars["expenses"].set(f"{expenses:.2f}")
        self.stats_vars["net"].set(f"{net:.2f}")
        self.stats_vars["avg_profit"].set(f"{avg_profit:.2f}")
        self.stats_vars["avg_income"].set(f"{avg_income:.2f}")

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
                avg = vals[5] if len(vals) > 5 else "0"
                if all(word in texts for word in name.split()):
                    items.append((vals[0], avg))
                    
        except Exception:
            logger.debug("OCR ошибка (подробности в логах)", exc_info=True)
            
        return items

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
        if self.running and self.overlays_enabled and not self.ocr_queue.empty():
            new_items = self.ocr_queue.get()
            try:
                if hasattr(self, 'overlay_window'):
                    self.overlay_window.update_list(new_items)
            except Exception:
                logger.exception("Ошибка обновления оверлея")
        if self.running and self.ocr_enabled:
            self.root.after(100, self.update_overlay_safe)

    def update_window_list(self):
        try:
            titles = [w.title for w in gw.getAllWindows() if w.title]
            self.window_cb['values'] = titles
        except Exception:
            logger.exception("Ошибка получения списка окон")

    def check_tesseract(self):
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            self.ocr_enabled = False
            messagebox.showwarning("Tesseract не найден", 
                                  "Не удалось найти Tesseract OCR. Функция автоматического поиска товаров будет отключена.")

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Настройки")
        settings_win.geometry("400x300")
        settings_win.configure(bg="#1e1e1e")

        tk.Label(settings_win, text="Прозрачность оверлея (0-1):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        alpha_var = tk.StringVar(value=str(self.overlay_alpha))
        alpha_entry = tk.Entry(settings_win, textvariable=alpha_var)
        alpha_entry.pack(pady=5)

        tk.Label(settings_win, text="Интервал обновления (сек):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        interval_var = tk.StringVar(value=str(self.overlay_refresh))
        interval_entry = tk.Entry(settings_win, textvariable=interval_var)
        interval_entry.pack(pady=5)

        tk.Label(settings_win, text="Область скриншота (left,top,right,bottom):", bg="#1e1e1e", fg="#fff").pack(pady=5)
        bbox_var = tk.StringVar(value=str(self.bbox) if self.bbox else "")
        bbox_entry = tk.Entry(settings_win, textvariable=bbox_var, width=40)
        bbox_entry.pack(pady=5)

        def save():
            try:
                self.overlay_alpha = float(alpha_var.get())
                self.overlay_refresh = float(interval_var.get())
                bbox_text = bbox_var.get().strip()
                self.bbox = tuple(map(int, bbox_text.strip("() ").split(","))) if bbox_text else None
                # применяем прозрачность в оверлее
                try:
                    self.overlay_window.set_alpha(self.overlay_alpha)
                except Exception:
                    pass
                self.save_settings()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
                logger.exception("Ошибка в настройках")

        tk.Button(settings_win, text="Сохранить", command=save, bg="#333333", fg="#fff").pack(pady=10)

    def load_settings(self):
        try:
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
        except Exception:
            logger.exception("Ошибка при загрузке настроек")

    def save_settings(self):
        try:
            data = {
                "overlay_alpha": self.overlay_alpha,
                "overlay_refresh": self.overlay_refresh,
                "bbox": self.bbox,
                "ocr_enabled": self.ocr_enabled,
                "overlays_enabled": self.overlays_enabled,
                "overlay_geometry": self.overlay_window.get_geometry() if hasattr(self, 'overlay_window') else self.overlay_geometry,
                "ui_config": self.ui_config
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
                        if len(row) >= 7:
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
        except Exception:
            logger.exception("Ошибка при сохранении товаров")

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
                                self.history_tree.insert("", tk.END, values=(row[0], row[1], price, row[3]))
                                self.history.append((row[0], row[1], price, row[3]))
                            except (ValueError, IndexError):
                                # Пропускаем некорректные строки
                                continue
                self.update_stats()
            except Exception:
                logger.exception("Ошибка при загрузке истории сделок")

    def save_deals(self):
        try:
            with open(DEAL_FILE, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for child in self.history_tree.get_children():
                    values = self.history_tree.item(child)["values"]
                    # Убедимся, что все значения - строки
                    row = [str(value) for value in values]
                    writer.writerow(row)
        except Exception:
            logger.exception("Ошибка при сохранении истории сделок")

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

    def on_close(self):
        self.running = False
        if hasattr(self, 'overlay_window'):
            self.overlay_window.destroy()
        self.save_settings()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TraderApp(root)
    root.mainloop()