import socket
import threading
import json
import os
import base64
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.properties import StringProperty, BooleanProperty
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp

PORT = 16385
BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def ip_to_code(ip: str) -> str:
    parts = list(map(int, ip.split('.')))
    num = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
    if num == 0:
        return "0"
    s = ""
    while num > 0:
        s = BASE36[num % 36] + s
        num //= 36
    return s

def code_to_ip(code: str) -> str:
    num = 0
    for char in code.upper():
        if char not in BASE36:
            raise ValueError(f"Invalid character: {char}")
        num = num * 36 + BASE36.index(char)
    return f"{(num >> 24) & 0xFF}.{(num >> 16) & 0xFF}.{(num >> 8) & 0xFF}.{num & 0xFF}"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        with self.canvas.before:
            Color(0.027, 0.725, 0.376, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(8)])
        self.bind(size=self.update_rect, pos=self.update_rect)
    
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class MessageBubble(BoxLayout):
    text_content = StringProperty("")
    is_self = BooleanProperty(True)
    sender = StringProperty("")
    time_str = StringProperty("")
    is_group = BooleanProperty(False)
    msg_type = StringProperty("text")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = [dp(10), dp(5), dp(10), dp(5)]
        self.spacing = dp(2)
        
        file_data = kwargs.get('file_data', None)
        file_category = kwargs.get('file_category', 'text')
        
        header = Label(
            size_hint_y=None,
            height=dp(20),
            font_size=dp(11),
            markup=True
        )
        if self.is_group and not self.is_self:
            header.text = f"[color=576b95]{self.sender}[/color] [color=999999]{self.time_str}[/color]"
        else:
            header.text = f"[color=999999]{self.time_str}[/color]"
        self.add_widget(header)
        
        if self.msg_type == 'image':
            content_box = BoxLayout(size_hint_y=None, height=dp(150))
            with content_box.canvas.before:
                Color(1, 1, 1, 1)
                content_box.rect = RoundedRectangle(size=content_box.size, pos=content_box.pos, radius=[dp(8)])
            content_box.bind(size=lambda i, v: setattr(content_box.rect, 'size', v), 
                           pos=lambda i, v: setattr(content_box.rect, 'pos', v))
            if file_data:
                try:
                    import io
                    from kivy.core.image import Image as CoreImage
                    img_data = io.BytesIO(file_data)
                    img = CoreImage(img_data, ext='png')
                    img_widget = Image(texture=img.texture, size_hint=(None, None), size=(dp(200), dp(120)))
                    content_box.add_widget(img_widget)
                except:
                    content_box.add_widget(Label(text="[图片]", color=(0,0,0,1)))
            else:
                content_box.add_widget(Label(text="[图片]", color=(0,0,0,1)))
            self.add_widget(content_box)
            
        elif self.msg_type == 'file':
            content_box = BoxLayout(size_hint_y=None, height=dp(60), padding=[dp(10), dp(5), dp(10), dp(5)])
            with content_box.canvas.before:
                Color(1, 1, 1, 1)
                content_box.rect = RoundedRectangle(size=content_box.size, pos=content_box.pos, radius=[dp(8)])
            content_box.bind(size=lambda i, v: setattr(content_box.rect, 'size', v), 
                           pos=lambda i, v: setattr(content_box.rect, 'pos', v))
            
            icon_map = {
                'image': '🖼️', 'pdf': '📕', 'office_doc': '📘', 'office_xls': '📊',
                'office_ppt': '📙', 'archive': '📦', 'html': '🌐',
                'script_py': '🐍', 'config': '⚙️', 'code': '📝', 'binary_no_preview': '🔒'
            }
            icon = icon_map.get(file_category, '📄')
            
            content_box.add_widget(Label(text=icon, font_size=dp(24), size_hint_x=None, width=dp(40)))
            
            info_box = BoxLayout(orientation='vertical')
            info_box.add_widget(Label(text=self.text_content, font_size=dp(14), halign='left', color=(0,0,0,1)))
            size_str = ""
            if file_data:
                size = len(file_data)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024*1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/1024/1024:.1f} MB"
            info_box.add_widget(Label(text=size_str, font_size=dp(10), color=(0.6,0.6,0.6,1)))
            content_box.add_widget(info_box)
            
            btn_box = BoxLayout(size_hint_x=None, width=dp(120), spacing=dp(5))
            btn_box.add_widget(Button(text="预览", size_hint_x=None, width=dp(55), font_size=dp(12)))
            btn_box.add_widget(Button(text="保存", size_hint_x=None, width=dp(55), font_size=dp(12)))
            content_box.add_widget(btn_box)
            
            self.add_widget(content_box)
        else:
            bubble = Label(
                text=self.text_content,
                size_hint_y=None,
                font_size=dp(14),
                markup=True,
                halign='left',
                valign='middle'
            )
            bubble.bind(texture_size=lambda i, v: setattr(bubble, 'height', v[1] + dp(16)))
            if self.is_self:
                with bubble.canvas.before:
                    Color(0.584, 0.925, 0.412, 1)
                    bubble.rect = RoundedRectangle(size=bubble.size, pos=bubble.pos, radius=[dp(8)])
            else:
                with bubble.canvas.before:
                    Color(1, 1, 1, 1)
                    bubble.rect = RoundedRectangle(size=bubble.size, pos=bubble.pos, radius=[dp(8)])
            bubble.bind(size=lambda i, v: setattr(bubble.rect, 'size', v), 
                       pos=lambda i, v: setattr(bubble.rect, 'pos', v))
            self.add_widget(bubble)
        
        self.bind(minimum_height=lambda i, v: setattr(self, 'height', v))

class ChatView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        self.scroll = ScrollView(size_hint=(1, 1))
        self.message_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5), padding=[dp(10), dp(10), dp(10), dp(10)])
        self.message_container.bind(minimum_height=self.message_container.setter('height'))
        self.scroll.add_widget(self.message_container)
        self.add_widget(self.scroll)
        
        input_box = BoxLayout(size_hint_y=None, height=dp(100), padding=[dp(10), dp(5), dp(10), dp(5)], spacing=dp(10))
        with input_box.canvas.before:
            Color(0.969, 0.969, 0.969, 1)
            input_box.rect = Rectangle(size=input_box.size, pos=input_box.pos)
        input_box.bind(size=lambda i, v: setattr(input_box.rect, 'size', v), 
                      pos=lambda i, v: setattr(input_box.rect, 'pos', v))
        
        tool_box = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
        
        file_btn = Button(text="📎 文件", size_hint_x=None, width=dp(80), font_size=dp(12))
        file_btn.bind(on_press=self.select_file)
        tool_box.add_widget(file_btn)
        
        img_btn = Button(text="🖼️ 图片", size_hint_x=None, width=dp(80), font_size=dp(12))
        img_btn.bind(on_press=self.select_image)
        tool_box.add_widget(img_btn)
        
        tool_box.add_widget(Label())
        input_box.add_widget(tool_box)
        
        text_box = BoxLayout(spacing=dp(10))
        
        self.msg_input = TextInput(
            hint_text="输入消息...",
            multiline=True,
            size_hint_x=0.8,
            font_size=dp(14)
        )
        text_box.add_widget(self.msg_input)
        
        send_btn = RoundedButton(text="发送", size_hint_x=None, width=dp(70))
        send_btn.bind(on_press=self.on_send)
        text_box.add_widget(send_btn)
        
        input_box.add_widget(text_box)
        self.add_widget(input_box)
        
        self.send_callback = None
        self.send_file_callback = None
    
    def select_file(self, instance):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView()
        content.add_widget(filechooser)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(50))
        cancel_btn = Button(text="取消")
        select_btn = Button(text="选择")
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(select_btn)
        content.add_widget(btn_box)
        
        popup = Popup(title="选择文件", content=content, size_hint=(0.9, 0.9))
        cancel_btn.bind(on_press=popup.dismiss)
        select_btn.bind(on_press=lambda x: self._on_file_selected(filechooser.path, popup))
        popup.open()
    
    def _on_file_selected(self, path, popup):
        popup.dismiss()
        if path and os.path.isfile(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                filename = os.path.basename(path)
                if self.send_file_callback:
                    self.send_file_callback(filename, data, 'file')
            except Exception as e:
                print(f"读取文件失败: {e}")
    
    def select_image(self, instance):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(filters=['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp'])
        content.add_widget(filechooser)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(50))
        cancel_btn = Button(text="取消")
        select_btn = Button(text="选择")
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(select_btn)
        content.add_widget(btn_box)
        
        popup = Popup(title="选择图片", content=content, size_hint=(0.9, 0.9))
        cancel_btn.bind(on_press=popup.dismiss)
        select_btn.bind(on_press=lambda x: self._on_image_selected(filechooser.path, popup))
        popup.open()
    
    def _on_image_selected(self, path, popup):
        popup.dismiss()
        if path and os.path.isfile(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                filename = os.path.basename(path)
                if self.send_file_callback:
                    self.send_file_callback(filename, data, 'image')
            except Exception as e:
                print(f"读取图片失败: {e}")
    
    def on_send(self, instance):
        text = self.msg_input.text.strip()
        if text and self.send_callback:
            self.send_callback(text, "text", None)
            self.msg_input.text = ""
    
    def add_message(self, text, is_self=True, sender="", time="", is_group=False, msg_type="text", file_data=None):
        bubble = MessageBubble(
            text_content=text,
            is_self=is_self,
            sender=sender,
            time_str=time,
            is_group=is_group,
            msg_type=msg_type,
            file_data=file_data
        )
        self.message_container.add_widget(bubble)
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)
    
    def scroll_to_bottom(self):
        self.scroll.scroll_y = 0
    
    def clear_messages(self):
        self.message_container.clear_widgets()

class ContactItem(BoxLayout):
    def __init__(self, name, is_group=False, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [dp(10), dp(5), dp(10), dp(5)]
        
        self.contact_name = name
        self.is_group = is_group
        self.callback = callback
        
        avatar = Label(
            text="群" if is_group else name[0].upper() if name else "?",
            size_hint_x=None,
            width=dp(40),
            font_size=dp(18)
        )
        with avatar.canvas.before:
            Color(0.027, 0.725, 0.376, 1)
            avatar.rect = RoundedRectangle(size=avatar.size, pos=avatar.pos, radius=[dp(20)])
        avatar.bind(size=lambda i, v: setattr(avatar.rect, 'size', v), 
                    pos=lambda i, v: setattr(avatar.rect, 'pos', v))
        self.add_widget(avatar)
        
        name_label = Label(text=f"群: {name}" if is_group else name, halign='left', color=(1,1,1,1))
        self.add_widget(name_label)
        
        self.bind(on_touch_down=self.on_item_touch)
    
    def on_item_touch(self, instance, touch):
        if self.collide_point(*touch.pos) and self.callback:
            self.callback(self.contact_name, self.is_group)
            return True
        return False

class ConnectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(orientation='vertical', padding=[dp(30), dp(50), dp(30), dp(50)], spacing=dp(15))
        with layout.canvas.before:
            Color(0.18, 0.18, 0.18, 1)
            layout.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=lambda i, v: setattr(layout.rect, 'size', v), 
                    pos=lambda i, v: setattr(layout.rect, 'pos', v))
        
        layout.add_widget(Label(text="简易微信", font_size=dp(28), bold=True, color=(1,1,1,1)))
        layout.add_widget(Label(text="连接交换机", font_size=dp(18), color=(0.7,0.7,0.7,1)))
        
        layout.add_widget(Label(text="交换Code:", color=(0.7,0.7,0.7,1), size_hint_y=None, height=dp(30)))
        self.code_input = TextInput(hint_text="输入交换Code", multiline=False, font_size=dp(16))
        self.code_input.background_color = (0.24, 0.24, 0.24, 1)
        self.code_input.foreground_color = (1, 1, 1, 1)
        layout.add_widget(self.code_input)
        
        layout.add_widget(Label(text="用户名:", color=(0.7,0.7,0.7,1), size_hint_y=None, height=dp(30)))
        self.name_input = TextInput(hint_text="输入用户名 (2-20字符)", multiline=False, font_size=dp(16))
        self.name_input.background_color = (0.24, 0.24, 0.24, 1)
        self.name_input.foreground_color = (1, 1, 1, 1)
        layout.add_widget(self.name_input)
        
        layout.add_widget(Label(size_hint_y=None, height=dp(20)))
        
        self.connect_btn = RoundedButton(text="连接", size_hint_y=None, height=dp(50), font_size=dp(18))
        layout.add_widget(self.connect_btn)
        
        self.add_widget(layout)

class MainScreen(Screen):
    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        
        main_layout = BoxLayout(orientation='horizontal')
        
        left_panel = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(280))
        with left_panel.canvas.before:
            Color(0.18, 0.18, 0.18, 1)
            left_panel.rect = Rectangle(size=left_panel.size, pos=left_panel.pos)
        left_panel.bind(size=lambda i, v: setattr(left_panel.rect, 'size', v), 
                        pos=lambda i, v: setattr(left_panel.rect, 'pos', v))
        
        header = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(15), dp(10), dp(15), dp(10)])
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            header.rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda i, v: setattr(header.rect, 'size', v), 
                   pos=lambda i, v: setattr(header.rect, 'pos', v))
        
        self.avatar = Label(text="?", size_hint_x=None, width=dp(45), font_size=dp(18))
        with self.avatar.canvas.before:
            Color(0.027, 0.725, 0.376, 1)
            self.avatar.rect = RoundedRectangle(size=self.avatar.size, pos=self.avatar.pos, radius=[dp(22)])
        self.avatar.bind(size=lambda i, v: setattr(self.avatar.rect, 'size', v), 
                        pos=lambda i, v: setattr(self.avatar.rect, 'pos', v))
        header.add_widget(self.avatar)
        
        self.name_label = Label(text="未连接", font_size=dp(16), bold=True, color=(1,1,1,1))
        header.add_widget(self.name_label)
        
        menu_btn = Button(text="⋮", size_hint_x=None, width=dp(30), font_size=dp(18), background_normal='', background_color=(0,0,0,0), color=(1,1,1,1))
        menu_btn.bind(on_press=self.show_menu)
        header.add_widget(menu_btn)
        
        left_panel.add_widget(header)
        
        self.tabs = TabbedPanel()
        self.tabs.background_color = (0.18, 0.18, 0.18, 1)
        
        friend_tab = TabbedPanelItem(text="好友")
        friend_scroll = ScrollView()
        self.friend_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        self.friend_list.bind(minimum_height=self.friend_list.setter('height'))
        friend_scroll.add_widget(self.friend_list)
        friend_tab.add_widget(friend_scroll)
        self.tabs.add_widget(friend_tab)
        
        group_tab = TabbedPanelItem(text="群聊")
        group_scroll = ScrollView()
        self.group_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        self.group_list.bind(minimum_height=self.group_list.setter('height'))
        group_scroll.add_widget(self.group_list)
        group_tab.add_widget(group_scroll)
        self.tabs.add_widget(group_tab)
        
        left_panel.add_widget(self.tabs)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(60), padding=[dp(10), dp(10), dp(10), dp(10)], spacing=dp(10))
        create_group_btn = RoundedButton(text="创建群")
        create_group_btn.bind(on_press=self.create_group)
        btn_box.add_widget(create_group_btn)
        
        join_group_btn = Button(text="加入群", background_normal='', background_color=(0.34, 0.42, 0.58, 1))
        join_group_btn.bind(on_press=self.join_group)
        btn_box.add_widget(join_group_btn)
        
        left_panel.add_widget(btn_box)
        main_layout.add_widget(left_panel)
        
        right_panel = BoxLayout(orientation='vertical')
        
        self.chat_header = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(20), dp(10), dp(20), dp(10)])
        with self.chat_header.canvas.before:
            Color(0.929, 0.929, 0.929, 1)
            self.chat_header.rect = Rectangle(size=self.chat_header.size, pos=self.chat_header.pos)
        self.chat_header.bind(size=lambda i, v: setattr(self.chat_header.rect, 'size', v), 
                             pos=lambda i, v: setattr(self.chat_header.rect, 'pos', v))
        
        self.chat_title = Label(text="请选择联系人开始聊天", font_size=dp(16), bold=True, halign='left', color=(0,0,0,1))
        self.chat_header.add_widget(self.chat_title)
        right_panel.add_widget(self.chat_header)
        
        self.chat_widget = ChatView()
        right_panel.add_widget(self.chat_widget)
        
        main_layout.add_widget(right_panel)
        self.add_widget(main_layout)
    
    def show_menu(self, instance):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        rename_btn = Button(text="改名", size_hint_y=None, height=dp(40))
        rename_btn.bind(on_press=self.do_rename)
        content.add_widget(rename_btn)
        
        refresh_btn = Button(text="刷新", size_hint_y=None, height=dp(40))
        refresh_btn.bind(on_press=self.do_refresh)
        content.add_widget(refresh_btn)
        
        disconnect_btn = Button(text="断开连接", size_hint_y=None, height=dp(40))
        disconnect_btn.bind(on_press=self.do_disconnect)
        content.add_widget(disconnect_btn)
        
        popup = Popup(title="菜单", content=content, size_hint=(None, None), size=(dp(200), dp(200)))
        rename_btn.bind(on_press=popup.dismiss)
        refresh_btn.bind(on_press=popup.dismiss)
        disconnect_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def do_rename(self, instance):
        if self.app:
            self.app.rename()
    
    def do_refresh(self, instance):
        if self.app:
            self.app.refresh_contacts()
    
    def do_disconnect(self, instance):
        if self.app:
            self.app.disconnect()
    
    def rename(self):
        pass
    
    def refresh_contacts(self):
        pass
    
    def disconnect(self):
        pass
    
    def create_group(self, instance):
        if self.app:
            self.app.create_group()
    
    def join_group(self, instance):
        if self.app:
            self.app.join_group()

class ClientApp(App):
    def build(self):
        Window.clearcolor = (0.929, 0.929, 0.929, 1)
        
        self.sm = ScreenManager()
        self.connect_screen = ConnectScreen(name='connect')
        self.main_screen = MainScreen(app_ref=self, name='main')
        
        self.connect_screen.connect_btn.bind(on_press=self.do_connect)
        
        self.sm.add_widget(self.connect_screen)
        self.sm.add_widget(self.main_screen)
        
        self.socket = None
        self.connected = False
        self.local_ip = get_local_ip()
        self.user_name = None
        self.online_users = []
        self.my_groups = []
        self.all_groups = []
        self.current_chat = None
        self.current_is_group = False
        self.chat_history = {}
        
        self.main_screen.chat_widget.send_callback = self.send_message
        self.main_screen.chat_widget.send_file_callback = self.send_file
        
        return self.sm
    
    def do_connect(self, instance):
        code = self.connect_screen.code_input.text.strip().upper()
        name = self.connect_screen.name_input.text.strip()
        
        if not code:
            self.show_popup("提示", "请输入交换Code")
            return
        if not name or len(name) < 2 or len(name) > 20:
            self.show_popup("提示", "用户名长度需2-20字符")
            return
        
        try:
            server_ip = code_to_ip(code)
        except:
            self.show_popup("错误", "无效的交换Code")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((server_ip, PORT))
            self.socket.settimeout(None)
            
            self.send_request({"type": "connect", "code": code, "ip": self.local_ip, "name": name})
            response = self.receive_response()
            
            if response and response.get("success"):
                self.connected = True
                self.user_name = name
                self.online_users = response.get("online_users", [])
                self.all_groups = response.get("groups", [])
                
                self.main_screen.name_label.text = name
                self.main_screen.avatar.text = name[0].upper()
                self.sm.current = 'main'
                self.update_contacts()
                
                threading.Thread(target=self.receive_loop, daemon=True).start()
            else:
                self.show_popup("连接失败", response.get("message", "未知错误") if response else "无响应")
                self.socket.close()
                self.socket = None
                
        except socket.timeout:
            self.show_popup("错误", "连接超时")
            if self.socket:
                self.socket.close()
                self.socket = None
        except Exception as e:
            self.show_popup("错误", f"连接失败: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=dp(20))
        content.add_widget(Label(text=message))
        btn = Button(text="确定", size_hint_y=None, height=dp(40))
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(None, None), size=(dp(300), dp(150)))
        btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def send_request(self, data):
        try:
            msg = json.dumps(data, ensure_ascii=False) + "\n"
            self.socket.send(msg.encode('utf-8'))
        except Exception as e:
            print(f"发送错误: {e}")
    
    def receive_response(self):
        try:
            data = b""
            while True:
                chunk = self.socket.recv(8192)
                if not chunk:
                    return None
                data += chunk
                if b"\n" in data:
                    break
            return json.loads(data.decode('utf-8').strip())
        except:
            return None
    
    def receive_loop(self):
        while self.connected and self.socket:
            try:
                data = b""
                while True:
                    chunk = self.socket.recv(65536)
                    if not chunk:
                        Clock.schedule_once(lambda dt: self.disconnect(), 0)
                        return
                    data += chunk
                    if b"\n" in data:
                        break
                
                message = json.loads(data.decode('utf-8').strip())
                msg_type = message.get("type")
                
                if msg_type == "private_message":
                    sender = message.get("sender")
                    content = message.get("content")
                    content_type = message.get("content_type", "text")
                    timestamp = message.get("timestamp", "")
                    time_str = timestamp.split(" ")[1] if " " in timestamp else timestamp
                    filename = message.get("filename", "file")
                    
                    file_data = None
                    if content_type in ('file', 'image') and content:
                        try:
                            file_data = base64.b64decode(content)
                        except:
                            pass
                    
                    display_content = content if content_type == 'text' else filename
                    Clock.schedule_once(lambda dt, s=sender, c=display_content, t=time_str, ct=content_type, fd=file_data: 
                        self.handle_private_message(s, c, t, ct, fd), 0)
                
                elif msg_type == "group_message":
                    group_name = message.get("group_name")
                    sender = message.get("sender")
                    content = message.get("content")
                    content_type = message.get("content_type", "text")
                    timestamp = message.get("timestamp", "")
                    time_str = timestamp.split(" ")[1] if " " in timestamp else timestamp
                    filename = message.get("filename", "file")
                    
                    file_data = None
                    if content_type in ('file', 'image') and content:
                        try:
                            file_data = base64.b64decode(content)
                        except:
                            pass
                    
                    display_content = content if content_type == 'text' else filename
                    Clock.schedule_once(lambda dt, gn=group_name, s=sender, c=display_content, t=time_str, ct=content_type, fd=file_data: 
                        self.handle_group_message(gn, s, c, t, ct, fd), 0)
                
                elif msg_type == "user_list_update":
                    self.online_users = message.get("users", [])
                    Clock.schedule_once(lambda dt: self.update_contacts(), 0)
                
                elif msg_type == "group_created":
                    group_name = message.get("group_name")
                    if group_name not in self.my_groups:
                        self.my_groups.append(group_name)
                    Clock.schedule_once(lambda dt: self.update_contacts(), 0)
                
                elif msg_type == "groups_list":
                    self.my_groups = message.get("groups", [])
                    self.all_groups = message.get("all_groups", [])
                    Clock.schedule_once(lambda dt: self.update_contacts(), 0)
                
            except Exception as e:
                if self.connected:
                    print(f"接收错误: {e}")
                break
    
    def handle_private_message(self, sender, content, time, content_type, file_data):
        key = f"friend_{sender}"
        if key not in self.chat_history:
            self.chat_history[key] = []
        self.chat_history[key].append({
            "text": content, "is_self": False, "sender": sender, 
            "time": time, "msg_type": content_type, "file_data": file_data
        })
        
        if self.current_chat == sender and not self.current_is_group:
            self.main_screen.chat_widget.add_message(content, False, sender, time, False, content_type, file_data)
    
    def handle_group_message(self, group_name, sender, content, time, content_type, file_data):
        key = f"group_{group_name}"
        if key not in self.chat_history:
            self.chat_history[key] = []
        self.chat_history[key].append({
            "text": content, "is_self": False, "sender": sender,
            "time": time, "is_group": True, "msg_type": content_type, "file_data": file_data
        })
        
        if self.current_chat == group_name and self.current_is_group:
            self.main_screen.chat_widget.add_message(content, False, sender, time, True, content_type, file_data)
    
    def send_message(self, text, content_type, file_data):
        if not self.connected or not self.current_chat:
            return
        
        if self.current_is_group:
            self.send_request({"type": "group_message", "group_name": self.current_chat, "content": text, "content_type": content_type})
            key = f"group_{self.current_chat}"
        else:
            self.send_request({"type": "private_message", "target_name": self.current_chat, "content": text, "content_type": content_type})
            key = f"friend_{self.current_chat}"
        
        if key not in self.chat_history:
            self.chat_history[key] = []
        time_str = datetime.now().strftime("%H:%M:%S")
        self.chat_history[key].append({
            "text": text, "is_self": True, "sender": self.user_name,
            "time": time_str, "is_group": self.current_is_group, "msg_type": content_type, "file_data": file_data
        })
        self.main_screen.chat_widget.add_message(text, True, self.user_name, time_str, self.current_is_group, content_type, file_data)
    
    def send_file(self, filename, file_data, file_type):
        if not self.connected or not self.current_chat:
            return
        
        encoded = base64.b64encode(file_data).decode('utf-8')
        
        if self.current_is_group:
            self.send_request({"type": "group_message", "group_name": self.current_chat, "content": encoded, "content_type": file_type, "filename": filename})
            key = f"group_{self.current_chat}"
        else:
            self.send_request({"type": "private_message", "target_name": self.current_chat, "content": encoded, "content_type": file_type, "filename": filename})
            key = f"friend_{self.current_chat}"
        
        if key not in self.chat_history:
            self.chat_history[key] = []
        time_str = datetime.now().strftime("%H:%M:%S")
        self.chat_history[key].append({
            "text": filename, "is_self": True, "sender": self.user_name,
            "time": time_str, "is_group": self.current_is_group, "msg_type": file_type, "file_data": file_data
        })
        self.main_screen.chat_widget.add_message(filename, True, self.user_name, time_str, self.current_is_group, file_type, file_data)
    
    def update_contacts(self):
        self.main_screen.friend_list.clear_widgets()
        for user in self.online_users:
            if user != self.user_name:
                item = ContactItem(user, False, self.on_contact_clicked)
                self.main_screen.friend_list.add_widget(item)
        
        self.main_screen.group_list.clear_widgets()
        for group in self.my_groups:
            item = ContactItem(group, True, self.on_contact_clicked)
            self.main_screen.group_list.add_widget(item)
    
    def on_contact_clicked(self, name, is_group):
        self.current_chat = name
        self.current_is_group = is_group
        self.main_screen.chat_title.text = f"群聊: {name}" if is_group else f"与 {name} 聊天"
        
        self.main_screen.chat_widget.clear_messages()
        key = f"{'group' if is_group else 'friend'}_{name}"
        for msg in self.chat_history.get(key, []):
            self.main_screen.chat_widget.add_message(
                msg["text"], msg["is_self"], msg["sender"], msg["time"],
                is_group, msg.get("msg_type", "text"), msg.get("file_data")
            )
    
    def rename(self):
        if not self.connected:
            return
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text="新名称:"))
        name_input = TextInput(text=self.user_name or "", multiline=False)
        content.add_widget(name_input)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(40))
        cancel_btn = Button(text="取消")
        ok_btn = Button(text="确定")
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(ok_btn)
        content.add_widget(btn_box)
        
        popup = Popup(title="改名", content=content, size_hint=(None, None), size=(dp(300), dp(150)))
        cancel_btn.bind(on_press=popup.dismiss)
        ok_btn.bind(on_press=lambda x: self._do_rename(name_input.text, popup))
        popup.open()
    
    def _do_rename(self, new_name, popup):
        popup.dismiss()
        if new_name.strip():
            self.send_request({"type": "rename", "new_name": new_name.strip()})
    
    def refresh_contacts(self):
        if self.connected:
            self.send_request({"type": "get_groups"})
    
    def create_group(self):
        if not self.connected:
            return
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text="群名称:"))
        name_input = TextInput(multiline=False)
        content.add_widget(name_input)
        
        content.add_widget(Label(text="选择成员:"))
        member_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(150))
        member_checks = []
        for user in self.online_users:
            if user != self.user_name:
                btn = Button(text=user, size_hint_y=None, height=dp(35))
                btn.background_color = (0.5, 0.5, 0.5, 1)
                btn.selected = False
                def toggle(btn=btn):
                    btn.selected = not btn.selected
                    btn.background_color = (0.027, 0.725, 0.376, 1) if btn.selected else (0.5, 0.5, 0.5, 1)
                btn.bind(on_press=lambda x, b=btn: toggle(b))
                member_checks.append(btn)
                member_box.add_widget(btn)
        content.add_widget(member_box)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(40))
        cancel_btn = Button(text="取消")
        ok_btn = Button(text="创建")
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(ok_btn)
        content.add_widget(btn_box)
        
        popup = Popup(title="创建群", content=content, size_hint=(None, None), size=(dp(300), dp(350)))
        cancel_btn.bind(on_press=popup.dismiss)
        ok_btn.bind(on_press=lambda x: self._do_create_group(name_input.text, member_checks, popup))
        popup.open()
    
    def _do_create_group(self, name, member_checks, popup):
        popup.dismiss()
        if not name.strip():
            return
        members = [btn.text for btn in member_checks if btn.selected]
        self.send_request({"type": "create_group", "group_name": name.strip(), "members": members})
    
    def join_group(self):
        if not self.connected:
            return
        self.send_request({"type": "get_groups"})
        Clock.schedule_once(lambda dt: self._show_join_dialog(), 0.5)
    
    def _show_join_dialog(self):
        available = [g for g in self.all_groups if g not in self.my_groups]
        if not available:
            self.show_popup("提示", "没有可加入的群")
            return
        
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text="选择群:"))
        
        group_box = BoxLayout(orientation='vertical')
        for group in available:
            btn = Button(text=group, size_hint_y=None, height=dp(40))
            btn.bind(on_press=lambda x, g=group: self._do_join_group(g, popup))
            group_box.add_widget(btn)
        content.add_widget(group_box)
        
        cancel_btn = Button(text="取消", size_hint_y=None, height=dp(40))
        content.add_widget(cancel_btn)
        
        popup = Popup(title="加入群", content=content, size_hint=(None, None), size=(dp(300), dp(300)))
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def _do_join_group(self, group_name, popup):
        popup.dismiss()
        self.send_request({"type": "join_group", "group_name": group_name})
    
    def disconnect(self):
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.user_name = None
        self.online_users = []
        self.my_groups = []
        self.sm.current = 'connect'
        self.main_screen.name_label.text = "未连接"
        self.main_screen.avatar.text = "?"

if __name__ == "__main__":
    ClientApp().run()
