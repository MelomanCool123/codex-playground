import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import logging

logger = logging.getLogger(__name__)

class MobileInterface:
    def __init__(self, main_app):
        self.main_app = main_app
        self.app = Flask(__name__)
        self.deals = []
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/')
        def mobile_index():
            return self.get_mobile_html()

        @self.app.route('/api/deals', methods=['GET', 'POST'])
        def handle_deals():
            if request.method == 'GET':
                return self.get_deals()
            elif request.method == 'POST':
                return self.add_deal()
        
        @self.app.route('/api/deals/<int:deal_id>', methods=['DELETE'])
        def delete_deal(deal_id):
            """Удаляет сделку"""
            try:
                self.main_app.delete_deal_from_mobile(deal_id)
                return jsonify({'success': True, 'message': 'Сделка удалена'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/deals/<int:deal_id>', methods=['PUT'])
        def update_deal(deal_id):
            """Обновляет сделку"""
            try:
                data = request.get_json()
                self.main_app.update_deal_in_mobile(deal_id, data)
                return jsonify({'success': True, 'message': 'Сделка обновлена'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            return self.get_stats()

        @self.app.route('/api/items', methods=['GET'])
        def get_items():
            """API для получения списка товаров из основной программы"""
            try:
                items = self.main_app.get_items_for_mobile()
                return jsonify({'success': True, 'items': items})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/search', methods=['GET'])
        def search_deals():
            """API для поиска сделок"""
            try:
                query = request.args.get('q', '').lower()
                date_from = request.args.get('from', '')
                date_to = request.args.get('to', '')
                deal_type = request.args.get('type', '')
                
                deals = self.main_app.get_all_deals_for_mobile()
                filtered_deals = []
                
                for deal in deals:
                    # Поиск по названию
                    if query and query not in deal.get('name', '').lower():
                        continue
                    
                    # Фильтр по типу
                    if deal_type and deal.get('type') != deal_type:
                        continue
                    
                    # Фильтр по дате
                    if date_from or date_to:
                        deal_date = datetime.strptime(deal.get('date', ''), '%Y-%m-%d %H:%M:%S')
                        if date_from and deal_date < datetime.strptime(date_from, '%Y-%m-%d'):
                            continue
                        if date_to and deal_date > datetime.strptime(date_to, '%Y-%m-%d'):
                            continue
                    
                    filtered_deals.append(deal)
                
                return jsonify({'success': True, 'deals': filtered_deals})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/analytics', methods=['GET'])
        def get_analytics():
            """API для аналитики"""
            try:
                deals = self.main_app.get_all_deals_for_mobile()
                
                # Статистика по дням
                daily_stats = {}
                for deal in deals:
                    date = deal.get('date', '')[:10]  # YYYY-MM-DD
                    if date not in daily_stats:
                        daily_stats[date] = {'income': 0, 'expense': 0, 'count': 0}
                    
                    if deal.get('type') == 'Продажа':
                        daily_stats[date]['income'] += deal.get('price', 0)
                    else:
                        daily_stats[date]['expense'] += deal.get('price', 0)
                    daily_stats[date]['count'] += 1
                
                # Топ товаров
                item_stats = {}
                for deal in deals:
                    name = deal.get('name', '')
                    if name not in item_stats:
                        item_stats[name] = {'count': 0, 'total': 0}
                    item_stats[name]['count'] += 1
                    item_stats[name]['total'] += deal.get('price', 0)
                
                top_items = sorted(item_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
                
                return jsonify({
                    'success': True,
                    'daily_stats': daily_stats,
                    'top_items': top_items,
                    'total_deals': len(deals)
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
    def get_deals(self):
        """Возвращает список сделок"""
        try:
            deals = self.main_app.get_all_deals_for_mobile()
            return jsonify({'success': True, 'deals': deals})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def delete_deal(self, deal_id):
        """Удаляет сделку"""
        try:
            # Удаляем сделку из основной программы
            self.main_app.delete_deal_from_mobile(deal_id)
            return jsonify({'success': True, 'message': 'Сделка удалена'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def update_deal(self, deal_id, deal_data):
        """Обновляет сделку"""
        try:
            # Обновляем сделку в основной программе
            self.main_app.update_deal_in_mobile(deal_id, deal_data)
            return jsonify({'success': True, 'message': 'Сделка обновлена'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    def add_deal(self):
        """Добавляет новую сделку"""
        try:
            data = request.get_json()
            deal_id = int(time.time() * 1000)
            
            deal = {
                'id': deal_id,
                'name': data.get('name', ''),
                'price': float(data.get('price', 0)),
                'type': data.get('type', 'Продажа'),
                'quantity': int(data.get('quantity', 1)),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'mobile'
            }
            
            # Добавляем сделку в основное приложение
            self.main_app.add_deal_from_mobile(deal)
            
            return jsonify({'success': True, 'deal': deal})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        
    def get_stats(self):
        """Возвращает статистику"""
        try:
            deals = self.main_app.get_all_deals_for_mobile()
            stats = self.calculate_correct_stats(deals)
            
            return jsonify({
                'success': True,
                'total_deals': len(deals),
                'total_profit': stats['profit'],
                'total_income': stats['income'],
                'total_expense': stats['expenses'],
                'net_profit': stats['net'],
                'avg_profit': stats['avg_profit']
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    def calculate_correct_stats(self, deals):
        """Вычисляет статистику по правильной логике из основной программы"""
        try:
            count = len(deals)
            profit = 0.0
            income = 0.0
            expenses = 0.0

            for deal in deals:
                price = deal.get('price', 0)
                deal_type = deal.get('type', '')
                name = deal.get('name', '')
                
                if deal_type == 'Продажа':
                    income += price
                    # Найти товар и вычислить прибыль
                    items = self.main_app.get_items_for_mobile()
                    for item in items:
                        if item['name'] == name:
                            try:
                                buy = item.get('buy_price', 0)
                                repair = item.get('repair', 0)
                                tax_pct = item.get('tax', 0)
                                tax_amt = price * tax_pct / 100
                                profit += price - buy - repair - tax_amt
                            except (ValueError, TypeError):
                                pass
                            break
                elif deal_type == 'Покупка':
                    expenses += price

            net = income - expenses
            avg_profit = profit / count if count > 0 else 0
            
            return {
                'profit': profit,
                'income': income,
                'expenses': expenses,
                'net': net,
                'avg_profit': avg_profit
            }
        except Exception as e:
            logger.error(f"Ошибка расчета статистики: {e}")
            return {
                'profit': 0.0,
                'income': 0.0,
                'expenses': 0.0,
                'net': 0.0,
                'avg_profit': 0.0
            }

    def calculate_total_profit(self):
        """Вычисляет общую прибыль (устаревший метод, оставлен для совместимости)"""
        try:
            deals = self.main_app.get_all_deals_for_mobile()
            stats = self.calculate_correct_stats(deals)
            return stats['profit']
        except:
            return 0

    def save_deals(self):
        """Сохраняет сделки"""
        try:
            self.main_app.save_deals()
        except Exception as e:
            logger.error(f"Ошибка сохранения сделок: {e}")

    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Запускает мобильный интерфейс"""
        try:
            logger.info("🌐 Мобильный интерфейс запущен")
            print(f"🌐 Запуск мобильного интерфейса на {host}:{port}")
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except Exception as e:
            logger.error(f"Ошибка запуска мобильного интерфейса: {e}")
    
    def get_mobile_html(self):
        """Генерирует супер-красивый HTML для мобильного интерфейса"""
        try:
            deals = self.main_app.get_all_deals_for_mobile()
            total_profit = self.calculate_total_profit()

            html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GTA5 RP Calculator - Mobile Pro</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg-primary: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            --bg-secondary: rgba(0, 0, 0, 0.8);
            --text-primary: #ffffff;
            --text-secondary: #cccccc;
            --accent-color: #00ff00;
            --accent-hover: #00cc00;
            --border-color: rgba(255, 255, 255, 0.2);
            --card-bg: rgba(255, 255, 255, 0.1);
            --shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }}
        
        [data-theme="light"] {{
            --bg-primary: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 50%, #ddeeff 100%);
            --bg-secondary: rgba(255, 255, 255, 0.9);
            --text-primary: #333333;
            --text-secondary: #666666;
            --accent-color: #0066cc;
            --accent-hover: #004499;
            --border-color: rgba(0, 0, 0, 0.2);
            --card-bg: rgba(255, 255, 255, 0.8);
            --shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            transition: all 0.3s ease;
        }}

        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .app-wrapper {{
            max-width: 800px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }}
        
        .header {{
            text-align: center;
            padding: 20px 0;
            background: rgba(0, 255, 0, 0.1);
            border-radius: 15px;
            margin-bottom: 20px;
            border: 2px solid rgba(0, 255, 0, 0.3);
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.2);
        }}

        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(45deg, var(--accent-color), var(--accent-hover));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
            margin-bottom: 10px;
        }}
        
        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--card-bg);
            border: 2px solid var(--border-color);
            border-radius: 50px;
            padding: 10px 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}
        
        .theme-toggle:hover {{
            transform: scale(1.1);
            border-color: var(--accent-color);
        }}
        
        .template-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .template-btn {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 8px 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9em;
            color: var(--text-primary);
        }}
        
        .template-btn:hover {{
            background: var(--accent-color);
            color: #000;
            transform: translateY(-2px);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 255, 0, 0.3);
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #00ff00;
            margin-bottom: 5px;
        }}

        .stat-label {{
            font-size: 0.9em;
            color: #cccccc;
        }}

        .tabs {{
            display: flex;
            margin-bottom: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 5px;
        }}

        .tab {{
            flex: 1;
            padding: 15px;
            text-align: center;
            background: transparent;
            border: none;
            color: #ffffff;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1.1em;
        }}

        .tab.active {{
            background: linear-gradient(45deg, #00ff00, #00cc00);
            color: #000000;
            font-weight: bold;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .form-container {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .form-group {{
            margin-bottom: 20px;
            position: relative;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 8px;
            color: #00ff00;
            font-weight: bold;
            font-size: 1.1em;
        }}

        .form-group input, .form-group select {{
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.3);
            color: #ffffff;
            font-size: 1.1em;
            transition: all 0.3s ease;
        }}

        .form-group input:focus, .form-group select:focus {{
            outline: none;
            border-color: #00ff00;
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
        }}

        .suggestions {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.9);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }}

        .item-suggestion {{
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .item-suggestion:hover {{
            background: rgba(0, 255, 0, 0.2);
        }}

        .item-suggestion:last-child {{
            border-bottom: none;
        }}

        .suggestion-name {{
            font-weight: bold;
            color: #00ff00;
            margin-bottom: 5px;
        }}

        .suggestion-comment {{
            font-size: 0.9em;
            color: #cccccc;
            margin-bottom: 5px;
        }}

        .suggestion-price {{
            font-size: 0.9em;
            color: #00ff00;
        }}

        .btn {{
            background: linear-gradient(45deg, #00ff00, #00cc00);
            color: #000000;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            margin-top: 10px;
        }}

        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 255, 0, 0.4);
        }}

        .btn-secondary {{
            background: linear-gradient(45deg, #666666, #444444);
            color: #ffffff;
        }}

        .deals-list {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .deal-item {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid var(--accent-color);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            touch-action: pan-y;
        }}

        .deal-item:hover {{
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0, 255, 0, 0.2);
        }}
        
        .deal-item.swipe-left {{
            transform: translateX(-100px);
        }}
        
        .deal-item.swipe-right {{
            transform: translateX(100px);
        }}
        
        .swipe-actions {{
            position: absolute;
            top: 0;
            right: -100px;
            height: 100%;
            width: 100px;
            background: linear-gradient(90deg, #ff4444, #cc0000);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: right 0.3s ease;
            border-radius: 0 10px 10px 0;
        }}
        
        .deal-item.swipe-left .swipe-actions {{
            right: 0;
        }}
        
        .swipe-delete {{
            color: white;
            font-size: 1.5em;
            cursor: pointer;
        }}

        .deal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .deal-actions {{
            display: flex;
            gap: 5px;
        }}
        
        .edit-btn, .delete-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 5px;
            padding: 5px 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 14px;
        }}
        
        .edit-btn:hover {{
            background: rgba(0, 255, 0, 0.2);
            border-color: #00ff00;
            transform: scale(1.1);
        }}
        
        .delete-btn:hover {{
            background: rgba(255, 0, 0, 0.2);
            border-color: #ff0000;
            transform: scale(1.1);
        }}
        
        #editForm {{
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.9);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(0, 255, 0, 0.3);
            border-radius: 15px;
            padding: 30px;
            z-index: 1000;
            max-width: 400px;
            width: 90%;
        }}

        .deal-name {{
            font-weight: bold;
            color: #00ff00;
            font-size: 1.1em;
        }}

        .deal-price {{
            font-size: 1.2em;
            font-weight: bold;
        }}

        .deal-price.income {{
            color: #00ff00;
        }}

        .deal-price.expense {{
            color: #ff4444;
        }}

        .deal-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            font-size: 0.9em;
            color: #cccccc;
        }}

        .search-filters {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}

        .filter-group {{
            display: flex;
            flex-direction: column;
        }}

        .filter-group label {{
            font-size: 0.9em;
            color: #00ff00;
            margin-bottom: 5px;
        }}

        .filter-group input, .filter-group select {{
            padding: 10px;
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.3);
            color: #ffffff;
        }}

        .analytics-chart {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
        }}

        .chart-placeholder {{
            height: 200px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #cccccc;
            font-size: 1.2em;
        }}

        .message {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            color: #ffffff;
            font-weight: bold;
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        }}

        .message.success {{
            background: linear-gradient(45deg, #00ff00, #00cc00);
            color: #000000;
        }}

        .message.error {{
            background: linear-gradient(45deg, #ff4444, #cc0000);
        }}

        .message.show {{
            transform: translateX(0);
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 5px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .search-filters {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
        <div class="theme-toggle" onclick="toggleTheme()">
            <span id="theme-icon">🌙</span>
        </div>
        
    <div class="container">
            <div class="app-wrapper">
        <div class="header">
                    <h1>🚗 GTA5 RP Calculator Pro</h1>
                    <p>Мобильный интерфейс для управления сделками</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" id="totalDeals">{len(deals)}</div>
                        <div class="stat-label">Всего сделок</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalProfit">${total_profit:,.0f}</div>
                        <div class="stat-label">Прибыль</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalIncome">$0</div>
                        <div class="stat-label">Доходы</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalExpense">$0</div>
                        <div class="stat-label">Расходы</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="netProfit">$0</div>
                        <div class="stat-label">Чистая прибыль</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="avgProfit">$0</div>
                        <div class="stat-label">Средняя прибыль</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('deals')">📊 Сделки</button>
            <button class="tab" onclick="showTab('analytics')">📈 Аналитика</button>
            <button class="tab" onclick="showTab('search')">🔍 Поиск</button>
        </div>

                <div id="deals-tab" class="tab-content active">
                    <div class="template-buttons">
                        <button class="template-btn" onclick="useTemplate('drugs')">💊 Наркотики</button>
                        <button class="template-btn" onclick="useTemplate('weapons')">🔫 Оружие</button>
                        <button class="template-btn" onclick="useTemplate('vehicles')">🚗 Транспорт</button>
                        <button class="template-btn" onclick="useTemplate('materials')">🔧 Материалы</button>
                        <button class="template-btn" onclick="useTemplate('food')">🍔 Еда</button>
                </div>
                
                    <div class="form-container">
                        <h3 style="color: var(--accent-color); margin-bottom: 20px;">➕ Добавить сделку</h3>
                        <form id="dealForm">
                <div class="form-group">
                                <label>Название товара:</label>
                                <input type="text" id="name" name="name" placeholder="Введите название товара" required>
                                <div class="suggestions" id="suggestions"></div>
                </div>
                <div class="form-group">
                        <label>Цена:</label>
                        <input type="number" id="price" name="price" placeholder="Введите цену" step="0.01" required>
                </div>
                <div class="form-group">
                        <label>Тип сделки:</label>
                    <select id="type" name="type">
                            <option value="Продажа">Продажа</option>
                            <option value="Покупка">Покупка</option>
                    </select>
                </div>
                    <div class="form-group">
                        <label>Количество:</label>
                        <input type="number" id="quantity" name="quantity" value="1" min="1" required>
                    </div>
                    <button type="submit" class="btn">💾 Добавить сделку</button>
            </form>
        </div>
        
            <div class="deals-list">
                <h3 style="color: #00ff00; margin-bottom: 20px;">📋 Последние сделки</h3>
                <div id="dealsList">
                    <div style="text-align: center; color: #cccccc; padding: 20px;">
                        Загрузка сделок...
                </div>
                </div>
            </div>
        </div>
        
        <div id="analytics-tab" class="tab-content">
            <div class="analytics-chart">
                <h3 style="color: #00ff00; margin-bottom: 20px;">📈 График прибыли</h3>
                <div class="chart-placeholder">
                    📊 График будет здесь
                </div>
            </div>
            <div class="analytics-chart">
                <h3 style="color: #00ff00; margin-bottom: 20px;">🏆 Топ товаров</h3>
                <div id="topItems">
                    <div style="text-align: center; color: #cccccc; padding: 20px;">
                        Загрузка аналитики...
                </div>
                </div>
            </div>
        </div>
        
        <div id="search-tab" class="tab-content">
            <div class="form-container">
                <h3 style="color: #00ff00; margin-bottom: 20px;">🔍 Поиск и фильтры</h3>
            <div class="search-filters">
                    <div class="filter-group">
                        <label>Поиск по названию:</label>
                        <input type="text" id="searchQuery" placeholder="Введите название товара">
                    </div>
                    <div class="filter-group">
                        <label>Тип сделки:</label>
                        <select id="searchType">
                    <option value="">Все типы</option>
                            <option value="Продажа">Продажа</option>
                            <option value="Покупка">Покупка</option>
                </select>
            </div>
                    <div class="filter-group">
                        <label>От даты:</label>
                        <input type="date" id="searchFrom">
                    </div>
                    <div class="filter-group">
                        <label>До даты:</label>
                        <input type="date" id="searchTo">
                    </div>
                </div>
                <button class="btn" onclick="searchDeals()">🔍 Найти</button>
                <button class="btn btn-secondary" onclick="clearSearch()">🗑️ Очистить</button>
            </div>
            <div class="deals-list">
                <h3 style="color: #00ff00; margin-bottom: 20px;">🔍 Результаты поиска</h3>
                <div id="searchResults">
                    <div style="text-align: center; color: #cccccc; padding: 20px;">
                        Введите критерии поиска
                    </div>
                </div>
            </div>
        </div>
    </div>

                <!-- Форма редактирования сделки -->
                <div id="editForm"></div>

                <div id="message" class="message"></div>
            </div>
        </div>

    <script>
        let items = [];
        let allDeals = [];

        document.addEventListener('DOMContentLoaded', function() {{
                    loadTheme();
                    loadDeals();
                    loadItems();
                    loadStats();
                    loadAnalytics();
        }});

        function showTab(tabName) {{
            // Скрыть все вкладки
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Показать выбранную вкладку
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
        }}

        document.getElementById('dealForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            addDeal();
        }});

        document.getElementById('name').addEventListener('input', function(e) {{
            showSuggestions(e.target.value);
        }});

        function loadDeals() {{
            fetch('/api/deals')
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    allDeals = data.deals;
                    displayDeals(data.deals);
                }}
            }})
            .catch(error => console.log('Ошибка загрузки сделок:', error));
        }}

        function loadItems() {{
            fetch('/api/items')
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    items = data.items;
                }}
            }})
            .catch(error => console.log('Ошибка загрузки товаров:', error));
        }}

        function loadStats() {{
            fetch('/api/stats')
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    document.getElementById('totalDeals').textContent = data.total_deals;
                    document.getElementById('totalProfit').textContent = '$' + Math.round(data.total_profit).toLocaleString();
                    document.getElementById('totalIncome').textContent = '$' + Math.round(data.total_income).toLocaleString();
                    document.getElementById('totalExpense').textContent = '$' + Math.round(data.total_expense).toLocaleString();
                    document.getElementById('netProfit').textContent = '$' + Math.round(data.net_profit).toLocaleString();
                    document.getElementById('avgProfit').textContent = '$' + Math.round(data.avg_profit).toLocaleString();
                }}
            }})
            .catch(error => console.log('Ошибка загрузки статистики:', error));
        }}

        function loadAnalytics() {{
            fetch('/api/analytics')
                .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    displayTopItems(data.top_items);
                }}
            }})
            .catch(error => console.log('Ошибка загрузки аналитики:', error));
        }}

        function showSuggestions(query) {{
            const suggestions = document.getElementById('suggestions');
            if (query.length < 2) {{
                suggestions.style.display = 'none';
                return;
            }}

            const filtered = items.filter(item =>
                item.name.toLowerCase().includes(query.toLowerCase())
            ).slice(0, 5);

            if (filtered.length > 0) {{
                suggestions.innerHTML = filtered.map(item => `
                    <div class="item-suggestion" onclick="selectItem('${{item.name}}', ${{item.avg_price || item.sell_price || 0}})">
                        <div class="suggestion-name">${{item.name}}</div>
                        ${{item.comment ? `<div class="suggestion-comment">${{item.comment}}</div>` : ''}}
                        <div class="suggestion-price">Цена: ${{item.avg_price || item.sell_price || 0}}</div>
                    </div>
                `).join('');
                suggestions.style.display = 'block';
            }} else {{
                suggestions.style.display = 'none';
            }}
        }}

        function selectItem(name, price) {{
            document.getElementById('name').value = name;
            document.getElementById('price').value = price;
            document.getElementById('suggestions').style.display = 'none';
        }}

        function addDeal() {{
            const formData = {{
                name: document.getElementById('name').value,
                price: parseFloat(document.getElementById('price').value),
                type: document.getElementById('type').value,
                quantity: parseInt(document.getElementById('quantity').value)
            }};

            fetch('/api/deals', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(formData)
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    showMessage('Сделка успешно добавлена!', 'success');
                    document.getElementById('dealForm').reset();
                    loadDeals();
                    loadStats();
                }} else {{
                    showMessage('Ошибка: ' + data.error, 'error');
                }}
            }})
            .catch(error => {{
                showMessage('Ошибка: ' + error, 'error');
            }});
        }}

        function displayDeals(deals) {{
            const dealsList = document.getElementById('dealsList');
            if (deals.length === 0) {{
                dealsList.innerHTML = '<div style="text-align: center; color: #cccccc; padding: 20px;">Нет сделок</div>';
                return;
            }}

            dealsList.innerHTML = deals.slice(0, 10).map((deal, index) => `
                <div class="deal-item" id="deal-${{index}}" onmousedown="startSwipe(event, ${{index}})" onmousemove="swipeMove(event, ${{index}})" onmouseup="endSwipe(event, ${{index}})" ontouchstart="startSwipe(event, ${{index}})" ontouchmove="swipeMove(event, ${{index}})" ontouchend="endSwipe(event, ${{index}})">
                    <div class="deal-header">
                        <div class="deal-name">${{deal.name}}</div>
                        <div class="deal-price ${{deal.type === 'Продажа' ? 'income' : 'expense'}}">
                            ${{deal.type === 'Продажа' ? '+' : '-'}}$${{deal.price.toLocaleString()}}
                        </div>
                        <div class="deal-actions">
                            <button class="edit-btn" onclick="editDeal(${{index}})">✏️</button>
                            <button class="delete-btn" onclick="deleteDeal(${{index}})">🗑️</button>
                        </div>
                    </div>
                    <div class="deal-details">
                        <div>Тип: ${{deal.type}}</div>
                        <div>Количество: ${{deal.quantity}}</div>
                        <div>Дата: ${{deal.date}}</div>
                    </div>
                    <div class="swipe-actions">
                        <div class="swipe-delete" onclick="deleteDeal(${{index}})">🗑️</div>
                    </div>
                </div>
            `).join('');
        }}

        function displayTopItems(topItems) {{
            const topItemsDiv = document.getElementById('topItems');
            if (topItems.length === 0) {{
                topItemsDiv.innerHTML = '<div style="text-align: center; color: #cccccc; padding: 20px;">Нет данных</div>';
                return;
            }}

            topItemsDiv.innerHTML = topItems.map((item, index) => `
                <div class="deal-item">
                    <div class="deal-header">
                        <div class="deal-name">#${{index + 1}} ${{item[0]}}</div>
                        <div class="deal-price income">$${{item[1].total.toLocaleString()}}</div>
                    </div>
                    <div class="deal-details">
                        <div>Количество сделок: ${{item[1].count}}</div>
                        <div>Средняя цена: ${{(item[1].total / item[1].count).toLocaleString()}}</div>
                    </div>
                </div>
            `).join('');
        }}

        function searchDeals() {{
            const query = document.getElementById('searchQuery').value;
            const type = document.getElementById('searchType').value;
            const from = document.getElementById('searchFrom').value;
            const to = document.getElementById('searchTo').value;

            const params = new URLSearchParams();
            if (query) params.append('q', query);
            if (type) params.append('type', type);
            if (from) params.append('from', from);
            if (to) params.append('to', to);

            fetch('/api/search?' + params.toString())
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    displaySearchResults(data.deals);
                }} else {{
                    showMessage('Ошибка поиска: ' + data.error, 'error');
                }}
            }})
            .catch(error => {{
                showMessage('Ошибка поиска: ' + error, 'error');
            }});
        }}

        function displaySearchResults(deals) {{
            const resultsDiv = document.getElementById('searchResults');
            if (deals.length === 0) {{
                resultsDiv.innerHTML = '<div style="text-align: center; color: #cccccc; padding: 20px;">Ничего не найдено</div>';
                return;
            }}

            resultsDiv.innerHTML = deals.map(deal => `
                <div class="deal-item">
                    <div class="deal-header">
                        <div class="deal-name">${{deal.name}}</div>
                        <div class="deal-price ${{deal.type === 'Продажа' ? 'income' : 'expense'}}">
                            ${{deal.type === 'Продажа' ? '+' : '-'}}$${{deal.price.toLocaleString()}}
                        </div>
                    </div>
                    <div class="deal-details">
                        <div>Тип: ${{deal.type}}</div>
                        <div>Количество: ${{deal.quantity}}</div>
                        <div>Дата: ${{deal.date}}</div>
                    </div>
                </div>
            `).join('');
        }}

        function clearSearch() {{
            document.getElementById('searchQuery').value = '';
            document.getElementById('searchType').value = '';
            document.getElementById('searchFrom').value = '';
            document.getElementById('searchTo').value = '';
            document.getElementById('searchResults').innerHTML = '<div style="text-align: center; color: #cccccc; padding: 20px;">Введите критерии поиска</div>';
        }}

        function showMessage(text, type) {{
            const message = document.getElementById('message');
            message.textContent = text;
            message.className = `message ${{type}} show`;
            
            setTimeout(() => {{
                message.classList.remove('show');
            }}, 3000);
        }}
        
        function deleteDeal(dealIndex) {{
            if (confirm('Вы уверены, что хотите удалить эту сделку?')) {{
                fetch(`/api/deals/${{dealIndex}}`, {{
                    method: 'DELETE',
                    headers: {{
                        'Content-Type': 'application/json',
                    }}
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        showMessage('Сделка удалена успешно!', 'success');
                        loadDeals();
                        loadStats();
                    }} else {{
                        showMessage('Ошибка: ' + data.error, 'error');
                    }}
                }})
                .catch(error => {{
                    showMessage('Ошибка: ' + error, 'error');
                }});
            }}
        }}
        
        function editDeal(dealIndex) {{
            const deal = allDeals[dealIndex];
            if (deal) {{
                // Показываем форму редактирования
                document.getElementById('editForm').style.display = 'block';
                document.getElementById('editForm').innerHTML = `
                    <h3 style="color: #00ff00; margin-bottom: 20px;">✏️ Редактировать сделку</h3>
                    <div class="form-group">
                        <label>Название товара:</label>
                        <input type="text" id="editName" name="name" value="${{deal.name}}" required>
                    </div>
                    <div class="form-group">
                        <label>Цена:</label>
                        <input type="number" id="editPrice" name="price" value="${{deal.price}}" step="0.01" required>
                    </div>
                    <div class="form-group">
                        <label>Тип сделки:</label>
                        <select id="editType" name="type">
                            <option value="Продажа" ${{deal.type === 'Продажа' ? 'selected' : ''}}>Продажа</option>
                            <option value="Покупка" ${{deal.type === 'Покупка' ? 'selected' : ''}}>Покупка</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Количество:</label>
                        <input type="number" id="editQuantity" name="quantity" value="${{deal.quantity || 1}}" min="1" required>
                    </div>
                    <button type="button" class="btn" onclick="updateDeal(${{dealIndex}})">💾 Обновить сделку</button>
                    <button type="button" class="btn btn-secondary" onclick="cancelEdit()">❌ Отмена</button>
                `;
            }}
        }}
        
        function updateDeal(dealIndex) {{
            const formData = {{
                name: document.getElementById('editName').value,
                price: parseFloat(document.getElementById('editPrice').value),
                type: document.getElementById('editType').value,
                quantity: parseInt(document.getElementById('editQuantity').value),
                date: allDeals[dealIndex].date  // Сохраняем оригинальную дату
            }};
            
            fetch(`/api/deals/${{dealIndex}}`, {{
                method: 'PUT',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(formData)
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    showMessage('Сделка обновлена успешно!', 'success');
                    document.getElementById('editForm').style.display = 'none';
                    loadDeals();
                    loadStats();
                }} else {{
                    showMessage('Ошибка: ' + data.error, 'error');
                }}
            }})
            .catch(error => {{
                showMessage('Ошибка: ' + error, 'error');
            }});
        }}
        
        function cancelEdit() {{
            document.getElementById('editForm').style.display = 'none';
        }}
        
        // Управление темами
        function toggleTheme() {{
            const body = document.body;
            const themeIcon = document.getElementById('theme-icon');
            
            if (body.getAttribute('data-theme') === 'light') {{
                body.removeAttribute('data-theme');
                themeIcon.textContent = '🌙';
                localStorage.setItem('theme', 'dark');
            }} else {{
                body.setAttribute('data-theme', 'light');
                themeIcon.textContent = '☀️';
                localStorage.setItem('theme', 'light');
            }}
        }}
        
        // Загрузка сохраненной темы
        function loadTheme() {{
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light') {{
                document.body.setAttribute('data-theme', 'light');
                document.getElementById('theme-icon').textContent = '☀️';
            }}
        }}
        
        // Шаблоны для быстрого добавления
        const templates = {{
            drugs: [
                {{name: 'Кокаин', price: 5000, type: 'Продажа'}},
                {{name: 'Метамфетамин', price: 3000, type: 'Продажа'}},
                {{name: 'Марихуана', price: 1000, type: 'Продажа'}},
                {{name: 'Героин', price: 8000, type: 'Продажа'}}
            ],
            weapons: [
                {{name: 'Пистолет', price: 2000, type: 'Продажа'}},
                {{name: 'Автомат', price: 15000, type: 'Продажа'}},
                {{name: 'Снайперская винтовка', price: 25000, type: 'Продажа'}},
                {{name: 'Гранаты', price: 500, type: 'Продажа'}}
            ],
            vehicles: [
                {{name: 'Спортивный автомобиль', price: 50000, type: 'Продажа'}},
                {{name: 'Мотоцикл', price: 15000, type: 'Продажа'}},
                {{name: 'Грузовик', price: 30000, type: 'Продажа'}},
                {{name: 'Вертолет', price: 100000, type: 'Продажа'}}
            ],
            materials: [
                {{name: 'Металлолом', price: 200, type: 'Продажа'}},
                {{name: 'Электроника', price: 1000, type: 'Продажа'}},
                {{name: 'Ткань', price: 300, type: 'Продажа'}},
                {{name: 'Пластик', price: 150, type: 'Продажа'}}
            ],
            food: [
                {{name: 'Бургер', price: 50, type: 'Продажа'}},
                {{name: 'Пицца', price: 80, type: 'Продажа'}},
                {{name: 'Напиток', price: 20, type: 'Продажа'}},
                {{name: 'Сладости', price: 30, type: 'Продажа'}}
            ]
        }};
        
        function useTemplate(templateType) {{
            const template = templates[templateType];
            if (template && template.length > 0) {{
                const randomItem = template[Math.floor(Math.random() * template.length)];
                document.getElementById('name').value = randomItem.name;
                document.getElementById('price').value = randomItem.price;
                document.getElementById('type').value = randomItem.type;
                showMessage(`Шаблон "${{templateType}}" применен!`, 'success');
            }}
        }}
        
        // Swipe функции
        let swipeStartX = 0;
        let swipeCurrentX = 0;
        let isSwipeActive = false;
        
        function startSwipe(event, index) {{
            isSwipeActive = true;
            swipeStartX = event.type === 'touchstart' ? event.touches[0].clientX : event.clientX;
            const dealItem = document.getElementById(`deal-${{index}}`);
            dealItem.style.transition = 'none';
        }}
        
        function swipeMove(event, index) {{
            if (!isSwipeActive) return;
            
            event.preventDefault();
            swipeCurrentX = event.type === 'touchmove' ? event.touches[0].clientX : event.clientX;
            const deltaX = swipeCurrentX - swipeStartX;
            const dealItem = document.getElementById(`deal-${{index}}`);
            
            if (deltaX < -50) {{
                dealItem.style.transform = `translateX(${{Math.max(deltaX, -100)}}px)`;
                dealItem.classList.add('swipe-left');
            }} else {{
                dealItem.style.transform = 'translateX(0)';
                dealItem.classList.remove('swipe-left');
            }}
        }}
        
        function endSwipe(event, index) {{
            if (!isSwipeActive) return;
            
            isSwipeActive = false;
            const dealItem = document.getElementById(`deal-${{index}}`);
            const deltaX = swipeCurrentX - swipeStartX;
            
            dealItem.style.transition = 'all 0.3s ease';
            
            if (deltaX < -100) {{
                dealItem.style.transform = 'translateX(-100px)';
                dealItem.classList.add('swipe-left');
            }} else {{
                dealItem.style.transform = 'translateX(0)';
                dealItem.classList.remove('swipe-left');
            }}
        }}
    </script>
</body>
</html>
            """
            return html

        except Exception as e:
            return f"<html><body><h1>Ошибка: {str(e)}</h1></body></html>"