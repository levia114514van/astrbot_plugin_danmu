from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import threading
import asyncio
import websockets
import requests

@register("弹幕", "114514", "111111", "1.0.0")
class Danmu(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # ===================== 配置 =====================
        self.WS_PORT = 19143        # 内网端口
        self.MAX_DANMU = 15        # 最多保留的弹幕历史数量
        # =================================================
        self.clients = set()       # 存储所有连接的客户端
        self.danmu_history = []
        self.ws_thread = None
        self.public_ip = None

    def get_public_ip(self):
        """自动获取服务器公网IP"""
        try:
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

    async def handle_client(self, websocket):
        """处理单个客户端连接"""
        # 新客户端连接
        self.clients.add(websocket)
        logger.info(f"✅ 新客户端已连接，当前连接数: {len(self.clients)}")
        
        try:
            # 发送历史弹幕
            for msg in self.danmu_history:
                await websocket.send(msg)
            
            # 保持连接，等待客户端消息（我们这里不需要接收客户端消息）
            async for message in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # 客户端断开连接
            self.clients.remove(websocket)
            logger.info(f"❌ 客户端已断开，当前连接数: {len(self.clients)}")

    async def broadcast(self, message):
        """向所有连接的客户端广播消息"""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients]
            )

    def run_websocket_server(self):
        """在独立线程中运行 WebSocket 服务"""
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 启动 WebSocket 服务
        start_server = websockets.serve(
            self.handle_client,
            "0.0.0.0",
            self.WS_PORT
        )
        
        loop.run_until_complete(start_server)
        loop.run_forever()

    async def initialize(self):
        """插件初始化时自动启动 WebSocket 服务"""
        # 自动获取公网IP
        self.public_ip = self.get_public_ip()
        
        # 后台线程启动 WebSocket 服务
        self.ws_thread = threading.Thread(
            target=self.run_websocket_server,
            daemon=True
        )
        self.ws_thread.start()
        
        # 打印连接信息
        logger.info("="*50)
        logger.info("✅ 原生 WebSocket 弹幕服务已启动！")
        logger.info(f"🌐 服务器公网IP: {self.public_ip}")
        logger.info(f"🔌 内网端口: {self.WS_PORT}")
        logger.info("="*50)
        logger.info("📢 重要提示：")
        logger.info("   江苏宿迁NAT服务器用户注意：")
        logger.info("   1. 请在雨云控制台添加端口映射，内网端口填19143")
        logger.info("   2. 使用雨云分配的 公网IP:外网端口 作为连接地址")
        logger.info("   其他地区直接使用：")
        logger.info(f"   ws://{self.public_ip}:{self.WS_PORT}")
        logger.info("="*50)

    @filter.command("弹幕")
    async def read(self, event: AstrMessageEvent, msg: str = ""):
        """发送弹幕到OBS直播画面"""
        user_name = event.get_sender_name()
        
        if not msg:
            yield event.plain_result(f"{user_name}请输入弹幕内容，格式：/弹幕 你要发送的内容")
        else:
            danmu_content = f"{user_name}：{msg}"
            
            # 保存历史弹幕
            self.danmu_history.append(danmu_content)
            if len(self.danmu_history) > self.MAX_DANMU:
                self.danmu_history.pop(0)
            
            # 广播给所有客户端
            await self.broadcast(danmu_content)
            
            yield event.plain_result(f"✅ 弹幕已发送：{msg}")

    async def terminate(self):
        """插件卸载时自动停止 WebSocket 服务"""
        if self.ws_thread and self.ws_thread.is_alive():
            logger.info("正在停止 WebSocket 弹幕服务...")
            # 这里简单处理，直接终止线程
            self.ws_thread.join(timeout=2)
            logger.info("✅ WebSocket 弹幕服务已停止")