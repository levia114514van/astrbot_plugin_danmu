from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

import asyncio
from obswebsocket import obsws, requests

# OBS_HOST = "0.tcp.ap.ngrok.io"  # 例如 "123.45.67.89" 或 "my-obs.example.com"
# OBS_PORT = 16066                    # 你设置的端口号
OBS_HOST = "114.66.61.217"
OBS_PORT = 19143
OBS_PASSWORD = "password"  # 你设置的密码
OBS_TEXT_SOURCE_NAME = "DanmuSource"  # OBS 中用于显示弹幕的文本源名称

@register("弹幕插件", "114514", "11111", "1.0.0")
class DanmuPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("弹幕")
    async def read(self, event: AstrMessageEvent, msg: str):
        user_name = event.get_sender_name()
        message_chain = event.get_messages()
        logger.info(f"收到弹幕消息链: {message_chain}")

        if not msg or msg.strip() == "":
            yield event.plain_result(f"{user_name} 什么也没有说......")
            return

        # 发送到远程 OBS（或模拟服务器）
        try:
            result = await self.send_to_obs(user_name, msg)
            if result:
                yield event.plain_result(f"弹幕已发送: @{user_name}: {msg}")
            else:
                yield event.plain_result("弹幕发送失败，请检查 OBS 连接。")
        except Exception as e:
            logger.error(f"发送弹幕时发生异常: {e}")
            yield event.plain_result("弹幕发送失败，内部错误。")

    async def send_to_obs(self, user_name: str, message: str) -> bool:
        """异步包装，避免阻塞机器人主循环"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._send_to_obs_sync,
            user_name,
            message
        )

    def _send_to_obs_sync(self, user_name: str, message: str) -> bool:
        """同步函数：连接 OBS WebSocket 并更新文本源"""
        ws = None
        try:
            ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
            ws.connect()

            full_text = f"@{user_name}: {message}"

            # 调用 SetInputSettings 更新文本源
            ws.call(requests.SetInputSettings(
                inputName=OBS_TEXT_SOURCE_NAME,
                inputSettings={
                    "text": full_text
                }
            ))

            logger.info(f"已成功发送弹幕: {full_text}")
            return True

        except Exception as e:
            logger.error(f"OBS WebSocket 发送失败: {e}")
            return False

        finally:
            if ws:
                try:
                    ws.disconnect()
                except:
                    pass

    async def terminate(self):
        """插件卸载时调用"""
        pass