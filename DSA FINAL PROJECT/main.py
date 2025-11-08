# main.py
import json
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.list import (
    TwoLineAvatarIconListItem,
    IconLeftWidget,
    IconRightWidget,
    MDList,
)
from kivymd.uix.button import (
    MDFillRoundFlatButton,
    MDRectangleFlatButton,
    MDFloatingActionButton,
)
from kivymd.uix.dialog import MDDialog
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

from kivy.properties import StringProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.clock import Clock
from collections import deque
import sqlite3
from datetime import date, datetime

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_name="restaurant.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT DEFAULT 'Main'
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                items TEXT,
                total_price REAL,
                status TEXT DEFAULT 'pending',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def get_menu(self):
        self.cursor.execute("SELECT id, name, price, category FROM menu ORDER BY category, name")
        return [{'id': r[0], 'name': r[1], 'price': r[2], 'category': r[3]} for r in self.cursor.fetchall()]

    def add_menu_item(self, name, price, category="Main"):
        self.cursor.execute("INSERT INTO menu (name, price, category) VALUES (?, ?, ?)", (name, price, category))
        self.conn.commit()

    def delete_menu_item(self, item_id):
        self.cursor.execute("DELETE FROM menu WHERE id = ?", (item_id,))
        self.conn.commit()

    def create_order(self, customer_name, items, total_price):
        # Use current timestamp instead of relying on SQLite's CURRENT_TIMESTAMP
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO orders (customer_name, items, total_price, timestamp) VALUES (?, ?, ?, ?)",
            (customer_name, json.dumps(items), total_price, current_time)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_pending_orders(self):
        self.cursor.execute(
            "SELECT id, customer_name, items, total_price, timestamp FROM orders WHERE status='pending' ORDER BY timestamp"
        )
        rows = self.cursor.fetchall()
        orders = []
        for r in rows:
            try:
                # Try to parse as JSON first, fall back to eval for backward compatibility
                try:
                    items_data = json.loads(r[2])
                except:
                    items_data = eval(r[2])
                orders.append({
                    'id': r[0], 
                    'customer_name': r[1], 
                    'items': items_data, 
                    'total_price': r[3], 
                    'timestamp': r[4]
                })
            except:
                continue  # Skip corrupted orders
        return orders

    def update_order_status(self, order_id, status):
        # Use current timestamp when updating order status
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            UPDATE orders 
            SET status = ?, timestamp = ?
            WHERE id = ?
        """, (status, current_time, order_id))
        self.conn.commit()

    def get_today_stats(self):
        today = date.today().isoformat()
        self.cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(total_price),0)
            FROM orders
            WHERE status='completed' AND DATE(timestamp)=?
        ''', (today,))
        count, revenue = self.cursor.fetchone()
        avg = revenue / count if count and count > 0 else 0.0
        return {'orders': count or 0, 'revenue': revenue, 'avg': avg}
    
    def get_transactions(self):
        self.cursor.execute(
            "SELECT id, customer_name, items, total_price, timestamp FROM orders WHERE status='completed' ORDER BY timestamp DESC"
        )
        rows = self.cursor.fetchall()
        transactions = []
        for r in rows:
            try:
                # Try to parse as JSON first, fall back to eval for backward compatibility
                try:
                    items_data = json.loads(r[2])
                except:
                    items_data = eval(r[2])
                transactions.append({
                    'id': r[0], 
                    'customer_name': r[1], 
                    'items': items_data, 
                    'total_price': r[3], 
                    'timestamp': r[4]
                })
            except:
                continue  # Skip corrupted transactions
        return transactions


# ==================== ORDER QUEUE ====================
class OrderQueue:
    def __init__(self, database):
        self.db = database
        self.queue = deque()
        self.load_orders()

    def load_orders(self):
        """Load pending orders from database"""
        self.queue = deque(self.db.get_pending_orders())

    def enqueue(self, order_data):
        # Add current timestamp to order data
        current_time = datetime.now()
        order_data['timestamp'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        order_id = self.db.create_order(
            customer_name=order_data.get('customer_name', 'Guest'),
            items=order_data['items'],
            total_price=order_data['total_price']
        )
        # Add the order to queue with proper timestamp
        order_data['id'] = order_id
        self.queue.append(order_data)
        return order_id

    def dequeue(self):
        if not self.queue:
            return None
        order = self.queue.popleft()
        self.db.update_order_status(order['id'], 'completed')
        return order

    def get_all(self):
        return list(self.queue)

    def size(self):
        return len(self.queue)

    def refresh(self):
        """Force reload from DB"""
        self.load_orders()


# ==================== KV STRING ====================
kv_string = '''
<OrdersScreen>:
    name: "orders"
    BoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Order Queue"
            elevation: 10
            right_action_items: [["refresh", lambda x: root.refresh_orders()]]

        ScrollView:
            MDList:
                id: order_list

<TransactionHistoryScreen>:
    name: "history"
    BoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Transaction History"
            elevation: 10
            right_action_items: [["refresh", lambda x: root.refresh_transactions()]]

        ScrollView:
            MDList:
                id: transaction_list

<MenuScreen>:
    name: "menu"
    BoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Menu Management"
            elevation: 10
            right_action_items: [["plus", lambda x: root.show_add_dialog()]]

        ScrollView:
            MDList:
                id: menu_list

        MDFloatingActionButton:
            icon: "plus"
            pos_hint: {"right": 0.9, "bottom": 0.1}
            on_release: root.show_add_dialog()

<StatsScreen>:
    name: "stats"
    BoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Statistics"
            elevation: 10

        ScrollView:
            GridLayout:
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                padding: "20dp"
                spacing: "20dp"

                MDCard:
                    orientation: "vertical"
                    padding: "20dp"
                    size_hint_y: None
                    height: "120dp"
                    md_bg_color: "#2d5b7c"
                    MDLabel:
                        text: f"Today's Orders: {root.total_orders}"
                        halign: "center"
                        font_style: "H5"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1

                MDCard:
                    orientation: "vertical"
                    padding: "20dp"
                    size_hint_y: None
                    height: "120dp"
                    md_bg_color: "#2d7c5b"
                    MDLabel:
                        text: f"Revenue: ₱{root.daily_revenue}"
                        halign: "center"
                        font_style: "H5"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1

                MDCard:
                    orientation: "vertical"
                    padding: "20dp"
                    size_hint_y: None
                    height: "120dp"
                    md_bg_color: "#7c5b2d"
                    MDLabel:
                        text: f"Avg Order: ₱{root.average_order}"
                        halign: "center"
                        font_style: "H5"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1

                MDRectangleFlatButton:
                    text: "Refresh Stats"
                    size_hint_y: None
                    height: "50dp"
                    pos_hint: {"center_x": 0.5}
                    on_release: root.refresh_stats()

MDScreen:
    MDBottomNavigation:
        id: bottom_nav
        panel_color: "#333333"
        on_switch_tabs: app.on_tab_switch(*args)

        MDBottomNavigationItem:
            name: "orders_tab"
            text: "Orders"
            icon: "cart-outline"
            OrdersScreen:
                id: orders_screen

        MDBottomNavigationItem:
            name: "history_tab"
            text: "History"
            icon: "history"
            TransactionHistoryScreen:
                id: transaction_history_screen

        MDBottomNavigationItem:
            name: "menu_tab"
            text: "Menu"
            icon: "food"
            MenuScreen:
                id: menu_screen

        MDBottomNavigationItem:
            name: "stats_tab"
            text: "Stats"
            icon: "chart-line"
            StatsScreen:
                id: stats_screen
'''


# ==================== SCREENS ====================

class OrdersScreen(MDScreen):
    def on_enter(self):
        """Refresh when screen becomes visible"""
        self.refresh_orders()

    def refresh_orders(self):
        app = MDApp.get_running_app()
        self.ids.order_list.clear_widgets()
        orders = app.order_queue.get_all()

        if not orders:
            self.ids.order_list.add_widget(
                MDLabel(
                    text="No pending orders", 
                    halign="center", 
                    theme_text_color="Hint",
                    size_hint_y=None,
                    height="50dp"
                )
            )
            return

        for order in orders:
            items_str = ", ".join([f"{i['name']} x{i['qty']}" for i in order['items']])
            
            # Format timestamp
            timestamp = order.get('timestamp', '')
            formatted_time = self.format_timestamp(timestamp)

            item = TwoLineAvatarIconListItem(
                text=f"{order['customer_name']} - ₱{order['total_price']:,.2f}",
                secondary_text=f"Received: {formatted_time} • {items_str}"
            )
            item.add_widget(IconLeftWidget(icon="clock-outline"))
            btn = IconRightWidget(
                icon="check-bold", 
                theme_text_color="Custom", 
                text_color=(0, 0.8, 0, 1)
            )
            btn.bind(on_release=lambda x, o=order: self.complete_order(o))
            item.add_widget(btn)
            self.ids.order_list.add_widget(item)

    def format_timestamp(self, timestamp):
        """Format timestamp for display"""
        if not timestamp:
            return "Time not available"
        
        try:
            # Handle different timestamp formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return dt.strftime("%m/%d/%Y %I:%M:%S %p")
                except:
                    continue
            return timestamp
        except:
            return timestamp

    def complete_order(self, order):
        app = MDApp.get_running_app()
        completed_order = app.order_queue.dequeue()
        if completed_order:
            self.refresh_orders()
            # Refresh other screens
            app.refresh_history()
            app.refresh_stats()


class MenuScreen(MDScreen):
    def on_enter(self):
        """Refresh when screen becomes visible"""
        self.refresh_menu()

    def refresh_menu(self):
        app = MDApp.get_running_app()
        self.ids.menu_list.clear_widgets()
        menu = app.db.get_menu()
        
        if not menu:
            self.ids.menu_list.add_widget(
                MDLabel(
                    text="No menu items. Add some!", 
                    halign="center", 
                    theme_text_color="Hint",
                    size_hint_y=None,
                    height="50dp"
                )
            )
            return

        for m in menu:
            li = TwoLineAvatarIconListItem(
                text=m['name'],
                secondary_text=f"₱{m['price']:,.2f} • {m['category']}"
            )
            li.add_widget(IconLeftWidget(icon="silverware"))
            del_btn = IconRightWidget(
                icon="delete", 
                theme_text_color="Custom", 
                text_color=(1, 0.2, 0.2, 1)
            )
            del_btn.bind(on_release=lambda x, mid=m['id']: self.delete_item(mid))
            li.add_widget(del_btn)
            self.ids.menu_list.add_widget(li)

    def delete_item(self, item_id):
        app = MDApp.get_running_app()
        app.db.delete_menu_item(item_id)
        self.refresh_menu()

    def show_add_dialog(self):
        app = MDApp.get_running_app()
        if not hasattr(app, 'menu_dialog') or not app.menu_dialog:
            self.name_input = MDTextField(
                hint_text="Item Name",
                size_hint_y=None,
                height="40dp"
            )
            self.price_input = MDTextField(
                hint_text="Price", 
                input_filter="float",
                size_hint_y=None,
                height="40dp"
            )
            self.cat_input = MDTextField(
                hint_text="Category", 
                text="Main",
                size_hint_y=None,
                height="40dp"
            )

            content = MDBoxLayout(
                orientation="vertical",
                spacing="12dp",
                size_hint_y=None,
                height="200dp",
            )
            content.add_widget(self.name_input)
            content.add_widget(self.price_input)
            content.add_widget(self.cat_input)

            app.menu_dialog = MDDialog(
                title="Add Menu Item",
                type="custom",
                content_cls=content,
                buttons=[ 
                    MDRectangleFlatButton(
                        text="Cancel", 
                        on_release=lambda x: app.menu_dialog.dismiss()
                    ),
                    MDFillRoundFlatButton(
                        text="Add", 
                        on_release=lambda x: self.add_item()
                    ),
                ],
            )
        
        # Clear previous inputs
        self.name_input.text = ""
        self.price_input.text = ""
        self.cat_input.text = "Main"
        app.menu_dialog.open()

    def add_item(self):
        app = MDApp.get_running_app()
        name = self.name_input.text.strip()
        price_text = self.price_input.text.strip()
        cat = self.cat_input.text.strip() or "Main"

        if not name:
            return
            
        if not price_text:
            return

        try:
            price = float(price_text)
            if price <= 0:
                return
                
            app.db.add_menu_item(name, price, cat)
            self.refresh_menu()
            app.menu_dialog.dismiss()
        except ValueError:
            # Invalid price
            pass


class StatsScreen(MDScreen):
    total_orders = StringProperty("0")
    daily_revenue = StringProperty("0.00")
    average_order = StringProperty("0.00")

    def on_enter(self):
        """Refresh when screen becomes visible"""
        self.refresh_stats()

    def refresh_stats(self):
        app = MDApp.get_running_app()
        stats = app.db.get_today_stats()
        self.total_orders = str(stats['orders'])
        self.daily_revenue = f"{stats['revenue']:,.2f}"
        self.average_order = f"{stats['avg']:,.2f}"


class TransactionHistoryScreen(MDScreen):
    def on_enter(self):
        """Refresh when screen becomes visible"""
        self.refresh_transactions()
        
    def refresh_transactions(self):
        app = MDApp.get_running_app()
        self.ids.transaction_list.clear_widgets()

        transactions = app.db.get_transactions()

        if not transactions:
            self.ids.transaction_list.add_widget(
                MDLabel(
                    text="No transactions yet",
                    halign="center",
                    theme_text_color="Hint",
                    size_hint_y=None,
                    height="50dp"
                )
            )
            return

        for t in transactions:
            items_str = ", ".join([f"{i['name']} x{i['qty']}" for i in t['items']])
            
            # Format timestamp
            timestamp = t.get('timestamp', '')
            formatted_time = self.format_timestamp(timestamp)

            item = TwoLineAvatarIconListItem(
                text=f"{t['customer_name']} – ₱{t['total_price']:,.2f}",
                secondary_text=f"Completed: {formatted_time} • {items_str}"
            )
            item.add_widget(IconLeftWidget(icon="receipt"))
            self.ids.transaction_list.add_widget(item)

    def format_timestamp(self, timestamp):
        """Format timestamp for display"""
        if not timestamp:
            return "Time not available"
        
        try: 
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return dt.strftime("%m/%d/%Y %I:%M:%S %p")
                except:
                    continue
            return timestamp
        except:
            return timestamp


# ==================== MAIN APP ====================
class AdminApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.order_queue = OrderQueue(self.db)
        self.menu_dialog = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.accent_palette = "Amber"
        return Builder.load_string(kv_string)
    
    def refresh_history(self):
        """Refresh the Transaction History tab."""
        history_screen = self.root.ids.transaction_history_screen
        if history_screen:
            history_screen.refresh_transactions()
    
    def refresh_stats(self):
        """Refresh the Stats tab."""
        stats_screen = self.root.ids.stats_screen
        if stats_screen:
            stats_screen.refresh_stats()

    def on_tab_switch(self, *args):
        """Handle tab switching"""
        # Use Clock to avoid Kivy binding issues
        Clock.schedule_once(self.refresh_current_tab, 0.1)

    def refresh_current_tab(self, dt=None):
        """Refresh the currently active tab"""
        bottom_nav = self.root.ids.bottom_nav
        current_tab = bottom_nav.current
        
        if current_tab == "orders_tab":
            orders_screen = self.root.ids.orders_screen
            if orders_screen:
                orders_screen.refresh_orders()
                
        elif current_tab == "menu_tab":
            menu_screen = self.root.ids.menu_screen
            if menu_screen:
                menu_screen.refresh_menu()
                
        elif current_tab == "stats_tab":
            stats_screen = self.root.ids.stats_screen
            if stats_screen:
                stats_screen.refresh_stats()
                
        elif current_tab == "history_tab":
            history_screen = self.root.ids.transaction_history_screen
            if history_screen:
                history_screen.refresh_transactions()

    def on_start(self):
        # Initialize sample data
        self.initialize_sample_data()
        
        # Initial refresh of all screens
        Clock.schedule_once(self.refresh_all_screens, 0.2)

    def initialize_sample_data(self):
        """Add sample data if database is empty"""
        # Sample menu
        if not self.db.get_menu():
            samples = [
                ("Beef Caldereta", 180.0, "Main"),
                ("Chicken Adobo", 150.0, "Main"),
                ("Iced Tea", 45.0, "Drinks"),
                ("Rice", 25.0, "Sides"),
            ]
            for n, p, c in samples:
                self.db.add_menu_item(n, p, c)

        # Sample pending order if queue is empty
        if self.order_queue.size() == 0:
            self.items = [ {
                'customer_name': 'Maria Santos',
                'items': [
                    {'name': 'Chicken Adobo', 'qty': 1}, 
                    {'name': 'Rice', 'qty': 2}, 
                    {'name': 'Iced Tea', 'qty': 1}
                ],
                'total_price': 245.0
            },
             {
                'customer_name': 'Rhovic Gabijan',
                'items': [
                    {'name': 'Nilagang Tinola', 'qty': 3}, 
                    {'name': 'Siomai rice', 'qty': 2}, 
                    {'name': 'Iced Tea', 'qty': 4}
                ],
                'total_price': 500
            },
             {
                'customer_name': 'Eulin Ryan Bertrand',
                'items': [
                    {'name': 'Sinigang na Spaghetti', 'qty': 1}, 
                    {'name': 'Rice', 'qty': 2}, 
                    {'name': 'Iced Tea', 'qty': 1}
                ],
                'total_price': 245.0
            } ]
            for items in self.items:
                self.order_queue.enqueue(items)

        # Add one completed transaction if none exist
        transactions = self.db.get_transactions()
        if not transactions:
            completed_id = self.db.create_order(
                customer_name="Juan Dela Cruz",
                items=[{'name': 'Beef Caldereta', 'qty': 1}, {'name': 'Rice', 'qty': 2}],
                total_price=230.0
            )
            self.db.update_order_status(completed_id, 'completed')

    def refresh_all_screens(self, dt=None):
        """Refresh all screens initially"""
        self.refresh_current_tab()


if __name__ == "__main__":
    AdminApp().run()