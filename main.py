import socket
import threading
import json
import os
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock

PORT = 16385

class ConnectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.name_input = TextInput(hint_text='输入用户名', size_hint_y=None, height=40)
        self.ip_input = TextInput(hint_text='输入服务器IP', size_hint_y=None, height=40)
        connect_btn = Button(text='连接', size_hint_y=None, height=40)
        
        layout.add_widget(self.name_input)
        layout.add_widget(self.ip_input)
        layout.add_widget(connect_btn)
        
        connect_btn.bind(on_press=self.connect)
        self.add_widget(layout)
    
    def connect(self, instance):
        app = App.get_running_app()
        app.connect_to_server(self.name_input.text, self.ip_input.text)

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        
        self.chat_history = ScrollView()
        self.messages = BoxLayout(orientation='vertical', size_hint_y=None)
        self.messages.bind(minimum_height=self.messages.setter('height'))
        self.chat_history.add_widget(self.messages)
        
        input_layout = BoxLayout(size_hint_y=None, height=40)
        self.message_input = TextInput(hint_text='输入消息', size_hint_x=0.8)
        send_btn = Button(text='发送', size_hint_x=0.2)
        
        input_layout.add_widget(self.message_input)
        input_layout.add_widget(send_btn)
        
        layout.add_widget(self.chat_history)
        layout.add_widget(input_layout)
        
        send_btn.bind(on_press=self.send_message)
        self.add_widget(layout)
    
    def add_message(self, text, is_self=False):
        label = Label(text=text, size_hint_y=None, height=30)
        label.color = (0, 0, 1, 1) if is_self else (0, 0, 0, 1)
        self.messages.add_widget(label)
    
    def send_message(self, instance):
        app = App.get_running_app()
        app.send_message(self.message_input.text)
        self.message_input.text = ''

class ClientApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.connect_screen = ConnectScreen(name='connect')
        self.chat_screen = ChatScreen(name='chat')
        self.sm.add_widget(self.connect_screen)
        self.sm.add_widget(self.chat_screen)
        return self.sm
    
    def connect_to_server(self, name, ip):
        self.username = name
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, PORT))
            self.send_data({"type": "login", "username": name})
            self.chat_screen.add_message(f'已连接到 {ip}', False)
            self.sm.current = 'chat'
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            self.chat_screen.add_message(f'连接失败: {str(e)}', False)
    
    def send_data(self, data):
        if self.socket:
            try:
                msg = json.dumps(data) + '\n'
                self.socket.sendall(msg.encode('utf-8'))
            except:
                pass
    
    def send_message(self, text):
        if text.strip():
            self.send_data({"type": "message", "content": text})
            self.chat_screen.add_message(f'我: {text}', True)
    
    def receive_loop(self):
        buffer = ''
        while True:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = json.loads(line)
                    self.handle_message(msg)
            except:
                break
    
    def handle_message(self, msg):
        if msg.get('type') == 'message':
            user = msg.get('username', '未知')
            content = msg.get('content', '')
            Clock.schedule_once(lambda dt: self.chat_screen.add_message(f'{user}: {content}', False))

if __name__ == '__main__':
    ClientApp().run()