from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from flask import Flask
from flask_socketio import SocketIO
import threading

@register("弹幕", "114514", "111111", "1.0.0")
class Danmu(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # ===================== 仅需修改这两个配置 =====================
        self.WS_PORT = 5000        # 云服务器安全组开放的端口
        self.MAX_DANMU = 15        # 最多保留的弹幕历史数量
        # ============================================================
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.danmu_history = []
        self.ws_thread = None

    async def initialize(self):
        """插件初始化时自动启动WebSocket服务"""
        # 定义WebSocket连接处理
        @self.socketio.on('connect')
        def handle_connect():
            logger.info("OBS客户端已连接WebSocket")
            self.socketio.emit('init_danmu', self.danmu_history)
        
        # 后台线程启动WebSocket服务（不阻塞AstrBot主程序）
        self.ws_thread = threading.Thread(
            target=self.socketio.run,
            args=("0.0.0.0", self.WS_PORT),
            kwargs={"debug": False},
            daemon=True
        )
        self.ws_thread.start()
        logger.info(f"✅ WebSocket弹幕服务已启动，端口：{self.WS_PORT}")

    @filter.command("弹幕")
    async def read(self, event: AstrMessageEvent, msg: str = ""):
        """发送弹幕到OBS直播画面"""
        user_name = event.get_sender_name()
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        
        if not msg:
            # 空消息提示（保留原有逻辑）
            yield event.plain_result(f"{user_name}请输入弹幕内容，格式：/弹幕 你要发送的内容")
        else:
            # 替代原有yield，通过WebSocket发送弹幕到OBS
            danmu_content = f"{user_name}：{msg}"
            self.danmu_history.append(danmu_content)
            if len(self.danmu_history) > self.MAX_DANMU:
                self.danmu_history.pop(0)
            self.socketio.emit('new_danmu', danmu_content)
            
            # 可选：在群里回复发送成功提示（不需要可以删掉这行）
            yield event.plain_result(f"✅ 弹幕已发送：{msg}")

    async def terminate(self):
        """插件卸载时自动停止WebSocket服务"""
        if self.ws_thread and self.ws_thread.is_alive():
            logger.info("正在停止WebSocket弹幕服务...")
            self.socketio.stop()
            self.ws_thread.join(timeout=2)
            logger.info("✅ WebSocket弹幕服务已停止")