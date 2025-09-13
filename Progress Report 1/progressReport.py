from kivy.lang import Builder
from kivy.modules.recorder import on_recorder_key
from kivymd.app import MDApp
from kivy.properties import StringProperty
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton

Window.size = (400, 650)

class Queue:
    def __init__(self):
        self.queue = []

    def enqueue(self, dataval):
        if dataval not in self.queue:
            self.queue.append(dataval)
            return True
        else:
            return False

    def dequeue(self):
        if len(self.queue) <= 0:
            return "Queue is empty"
        else:
            return self.queue.pop(0)

    def is_empty(self):
        return len(self.queue) == 0


class OrderItem(MDBoxLayout):
    order_text = StringProperty()
    order_details = StringProperty()
    on_status_change = None
    on_remove = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = "72dp"
        self.spacing = "10dp"
        self.padding = ("10dp", "10dp")

        self.label = MDLabel(
            text=self.order_text,
            halign='left',
            shorten=True,
        )
        self.bind(order_text=lambda instance, value: setattr(self.label, "text", value))

        self.ongoing_btn = MDIconButton(
            icon="progress-clock",
            on_release=self.mark_ongoing,
        )

        self.ready_btn = MDIconButton(
            icon="check-bold",
            on_release=self.mark_ready,
        )

        self.delete_btn = MDIconButton(
            icon="delete",
            on_release=self.remove_order,
        )

        self.add_widget(self.label)
        self.add_widget(self.ongoing_btn)
        self.add_widget(self.ready_btn)
        self.add_widget(self.delete_btn)

    def mark_ongoing(self, instance):
        self.label.text = f"{self.label.text.split(' [')[0]} [Ongoing]"
        if self.on_status_change:
            self.on_status_change(self)

    def mark_ready(self, instance):
        self.label.text = f"{self.label.text.split(' [')[0]} [Ready to Serve]"
        if self.on_status_change:
            self.on_status_change(self)

    def remove_order(self, instance):
        if self.on_remove:
            self.on_remove(self)

class StaffDashboardApp(MDApp):
    def build(self):
        self.title = "Staff Dashboard"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Dark"
        return Builder.load_file("dashboard.kv")

    def on_start(self):
        self.orders_list = self.root.ids.orders_list
        self.populate_orders()

    def populate_orders(self):
        self.orders = Queue()
        orders_list = self.root.ids.orders_list

        sample_orders = [
            {"title": "Order #101 - Burger & Fries", "details": "Burger with cheese."},
            {"title": "Order #102 - Vegan Salad", "details": "Mixed greens."},
            {"title": "Order #103 - Coffee & Donut", "details": "Glazed donut."},
        ]
        for order in sample_orders:
            item = OrderItem(
                order_text=f"{order['title']} [Pending]",
                order_details=order['details']
            )
            self.orders.enqueue(order)
            item.on_status_change = self.on_order_status_change
            item.on_remove = self.on_order_remove
            orders_list.add_widget(item)

    def on_order_status_change(self, order_item):
        removed_order = self.orders.dequeue()
        print(f"Processed order: {removed_order}")

    def on_order_remove(self, order_item):
        removed_order = order_item.order_text.split(' [')[0]
        self.orders.queue = [order for order in self.orders.queue if order != removed_order]
        print(f"Removed order: {removed_order}")
        self.orders_list.remove_widget(order_item)


if __name__ == '__main__':
    StaffDashboardApp().run()