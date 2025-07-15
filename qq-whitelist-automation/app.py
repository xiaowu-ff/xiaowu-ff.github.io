import os
import time
import json
import threading
import logging
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import pyautogui
import pyperclip
import psutil
import pygetwindow as gw

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化Flask应用和SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app)

# 全局变量
clients = {}  # 存储客户端连接信息
status = {"processing": False, "message": "等待操作"}

# 查找QQ窗口并激活
def find_and_activate_qq_window():
    try:
        qq_windows = gw.getWindowsWithTitle('牛哥v枣庄售后群')
        if not qq_windows:
            logger.warning("未找到QQ聊天窗口")
            return False
        
        qq_window = qq_windows[0]
        qq_window.activate()
        time.sleep(0.5)  # 等待窗口激活
        return True
    except Exception as e:
        logger.error(f"查找QQ窗口失败: {e}")
        return False

# 发送消息到QQ聊天窗口
def send_message_to_qq(message):
    if not find_and_activate_qq_window():
        return False
    
    try:
        # 复制消息到剪贴板
        pyperclip.copy(message)
        
        # 粘贴并发送
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)
        pyautogui.press('enter')
        logger.info(f"消息已发送: {message}")
        return True
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        return False

# 识别添加成功的回复
def recognize_success_message():
    # 这里使用图像识别或OCR技术识别"添加成功"的回复
    # 简化版本：等待2秒后假设成功
    time.sleep(2)
    logger.info("假设添加成功")
    return True

# 处理IP地址并发送到QQ
def process_ip(ip_address, client_id):
    global status
    status = {"processing": True, "message": f"正在处理IP: {ip_address}"}
    socketio.emit('status_update', status, room=client_id)
    
    try:
        # 构造完整消息
        full_message = f"43.249.192.150添加白名单 {ip_address}"
        
        # 发送消息到QQ
        if send_message_to_qq(full_message):
            # 等待并识别回复
            success = recognize_success_message()
            if success:
                status = {"processing": False, "message": f"IP {ip_address} 添加成功", "success": True}
            else:
                status = {"processing": False, "message": f"IP {ip_address} 添加失败", "success": False}
        else:
            status = {"processing": False, "message": f"发送消息失败", "success": False}
            
    except Exception as e:
        logger.error(f"处理IP时出错: {e}")
        status = {"processing": False, "message": f"处理IP时出错: {str(e)}", "success": False}
    
    # 发送最终状态
    socketio.emit('status_update', status, room=client_id)

# 网页路由
@app.route('/')
def index():
    return render_template('index.html')

# 添加IP的API
@app.route('/add_ip', methods=['POST'])
def add_ip():
    data = request.json
    ip_address = data.get('ip_address')
    
    if not ip_address:
        return jsonify({"error": "IP地址不能为空"}), 400
    
    # 验证IP格式
    # 简化版本：只检查是否包含点
    if '.' not in ip_address:
        return jsonify({"error": "无效的IP地址格式"}), 400
    
    # 启动处理线程
    client_id = request.sid if hasattr(request, 'sid') else None
    thread = threading.Thread(target=process_ip, args=(ip_address, client_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "正在处理IP地址", "status": "processing"})

# SocketIO事件处理
@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    clients[client_id] = True
    logger.info(f"客户端连接: {client_id}")
    emit('status_update', status)

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    if client_id in clients:
        del clients[client_id]
    logger.info(f"客户端断开连接: {client_id}")

if __name__ == '__main__':
    logger.info("启动IP白名单自动化系统")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)    