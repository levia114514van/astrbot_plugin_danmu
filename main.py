from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from flask import Flask
from flask_socketio import SocketIO
import threading
import requests

@register("弹幕", "114514", "111111", "1.0.0")
class Danmu(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # ===================== 配置 =====================
        self.WS_PORT = 8080        # 内网端口（NAT模式下和端口映射的内网端口一致）
        self.MAX_DANMU = 15        # 最多保留的弹幕历史数量
        # =================================================
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.danmu_history = []
        self.ws_thread = None
        self.public_ip = None

    def get_public_ip(self):
        """自动获取服务器公网IP"""
        try:
            # 使用多个可靠的IP查询服务，提高成功率
            services = [
                'https://api.ipify.org',
                'https://ident.me',
                'https://ifconfig.me/ip'
            ]
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        return response.text.strip()
                except:
                    continue
            return "获取失败"
        except Exception as e:
            logger.error(f"获取公网IP失败: {e}")
            return "获取失败"

    async def initialize(self):
        """插件初始化时自动启动WebSocket服务并打印连接地址"""
        # 定义WebSocket连接处理
        @self.socketio.on('connect')
        def handle_connect():
            logger.info("OBS客户端已连接WebSocket")
            self.socketio.emit('init_danmu', self.danmu_history)
        
        # 自动获取公网IP
        self.public_ip = self.get_public_ip()
        
        # 后台线程启动WebSocket服务
        self.ws_thread = threading.Thread(
            target=self.socketio.run,
            args=("0.0.0.0", self.WS_PORT),
            kwargs={"debug": False},
            daemon=True
        )
        self.ws_thread.start()
        
        # 打印完整的连接信息
        logger.info("="*50)
        logger.info("✅ WebSocket弹幕服务已启动！")
        logger.info(f"🌐 服务器公网IP: {self.public_ip}")
        logger.info(f"🔌 内网端口: {self.WS_PORT}")
        logger.info("="*50)
        logger.info("📢 重要提示：")
        logger.info("   如果你是江苏宿迁NAT服务器：")
        logger.info("   1. 请在雨云控制台添加端口映射，内网端口填5000")
        logger.info("   2. 然后使用雨云分配的 公网IP:外网端口 作为连接地址")
        logger.info("   其他地区服务器直接使用下面的地址：")
        logger.info(f"   WebSocket连接地址: ws://{self.public_ip}:{self.WS_PORT}")
        logger.info("="*50)

    @filter.command("弹幕")
    async def read(self, event: AstrMessageEvent, msg: str = ""):
        """发送弹幕到OBS直播画面"""
        user_name = event.get_sender_name()
        
        if not msg:
            yield event.plain_result(f"{user_name}请输入弹幕内容，格式：/弹幕 你要发送的内容")
        else:
            danmu_content = f"{user_name}：{msg}"
            self.danmu_history.append(danmu_content)
            if len(self.danmu_history) > self.MAX_DANMU:
                self.danmu_history.pop(0)
            self.socketio.emit('new_danmu', danmu_content)
            
            yield event.plain_result(f"✅ 弹幕已发送：{msg}")

    async def terminate(self):
        """插件卸载时自动停止WebSocket服务"""
        if self.ws_thread and self.ws_thread.is_alive():
            logger.info("正在停止WebSocket弹幕服务...")
            self.socketio.stop()
            self.ws_thread.join(timeout=2)
            logger.info("✅ WebSocket弹幕服务已停止")