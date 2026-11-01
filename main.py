from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ChannelManager:
    def __init__(self):
        self.channels: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.channels:
            if websocket in self.channels[channel]:
                self.channels[channel].remove(websocket)
            if not self.channels[channel]:
                del self.channels[channel]

    async def broadcast(self, channel: str, message, sender: WebSocket = None, is_bytes: bool = False):
        if channel in self.channels:
            for connection in self.channels[channel]:
                if connection != sender:
                    try:
                        if is_bytes:
                            await connection.send_bytes(message)
                        else:
                            await connection.send_text(message)
                    except Exception:
                        pass

manager = ChannelManager()

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/{channel}/{username}")
async def websocket_endpoint(websocket: WebSocket, channel: str, username: str):
    await manager.connect(websocket, channel)
    
    try:
        while True:
            # Dawata bisan unsa (text JSON para sa GPS o bytes para sa audio)
            message = await websocket.receive()
            
            if "text" in message:
                data = message["text"]
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "location":
                        await manager.broadcast(channel, data, websocket, is_bytes=False)
                except:
                    pass
            elif "bytes" in message:
                # Automatic audio streaming broadcast sa tanan sa channel
                await manager.broadcast(channel, message["bytes"], websocket, is_bytes=True)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)