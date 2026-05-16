from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

import asyncio
from obswebsocket import obsws, requests

OBS_HOST = "114.66.61.131"  # 例如 "123.45.67.89" 或 "my-obs.example.com"
OBS_PORT = 19143                     # 你设置的端口号
OBS_PASSWORD = "password"  # 你设置的密码
OBS_TEXT_SOURCE_NAME = "DanmuSource"  # OBS 中用于显示弹幕的文本源名称

async def send_to_obs(self, user_name, message):
    """异步发送文本到 OBS 的指定文本源"""
    loop = asyncio.get_running_loop()
    # 使用 run_in_executor 将同步的 WebSocket 操作放入线程池，避免阻塞主线程
    return await loop.run_in_executor(
        None, 
        self._send_to_obs_sync, 
        user_name, 
        message
    )

#test
def _send_to_obs_sync(self, user_name, message):
    try:
        url = "http://192.168.68.119:19143/api/danmu"  # 同样需要穿透或公网
        payload = {"user": user_name, "text": message}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logger.info(f"弹幕已发送至HTTP调试服务器: @{user_name}: {message}")
            return True
    except Exception as e:
        logger.error(f"HTTP发送失败: {e}")
    return False

# def _send_to_obs_sync(self, user_name, message):
#     """同步执行：连接 OBS WebSocket 并更新文本源内容"""
#     ws = None
#     try:
#         # 1. 创建并连接 WebSocket 客户端
#         ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
#         ws.connect()

#         # 2. 构造要显示的完整文本
#         full_text = f"@{user_name}: {message}"

#         # 3. 调用 SetInputSettings 请求，更新指定文本源的文本内容
#         ws.call(requests.SetInputSettings(
#             inputName=OBS_TEXT_SOURCE_NAME,
#             inputSettings={
#                 "text": full_text
#             }
#         ))
#         logger.info(f"成功发送弹幕到 OBS: {full_text}")
#         return True
#     except Exception as e:
#         logger.error(f"OBS WebSocket 连接或发送失败: {e}")
#         return False
#     finally:
#         # 4. 无论成功与否，确保断开连接
#         if ws:
#             try:
#                 ws.disconnect()
#             except:
#                 pass


@filter.command("弹幕")
async def read(self, event: AstrMessageEvent, msg: str):
    user_name = event.get_sender_name()
    message_str = event.message_str
    # ... (logger.info 等部分代码不变)

    if not msg:
        yield event.plain_result(f"{user_name}什么也没有说......")
        return

    # 发送弹幕到 OBS
    try:
        result = await self.send_to_obs(user_name, msg)
        if result:
            yield event.plain_result(f"弹幕已发送: @{user_name}: {msg}")
        else:
            yield event.plain_result("弹幕发送失败，请检查 OBS 连接。")
    except Exception as e:
        logger.error(f"发送弹幕到 OBS 时发生错误: {e}")
        yield event.plain_result("弹幕发送失败，请稍后重试。")