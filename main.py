from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form, Depends, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import os
import base64
import json
import uuid
from datetime import datetime
import dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# Import AI functions
from ai import run_with_tools
from tools import recognize_speech

# Загрузка переменных окружения
dotenv.load_dotenv()

app = FastAPI(title="Chat with LLM")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
def get_openai_client():
    from config import github_token
    api_key = github_token
    base_url = "https://models.inference.ai.azure.com"

    
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    return client

# Models
class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    conversation_id: Optional[str] = None
    
class ImageMessage(BaseModel):
    image_data: str

class TitleRequest(BaseModel):
    message: str
    
class ConversationTitleUpdate(BaseModel):
    title: str

# List of models that support image input
MODELS_WITH_IMAGE_SUPPORT = [
    "gpt-4o", 
    "gpt-4o-mini", 
    "o1", 
    "o1-mini", 
    "o1-preview", 
    "o3-mini",
    "phi-3.5-vision-instruct", 
    "phi-4-multimodal-instruct",
    "llama-3.2-11b-vision-instruct", 
    "llama-3.2-90b-vision-instruct"
]
    
# In-memory storage for chat history катя шлюха
chat_history = {}
chat_titles = {}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/api/generate-title")
async def generate_title(request: TitleRequest):
    client = get_openai_client()
    
    try:
        response = client.chat.completions.create(
            model="phi-4-mini-instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Create a concise title (2-3 words) that captures the essence of the user's message."},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=20
        )
        
        title = response.choices[0].message.content.strip()
        # Remove quotes if present
        title = title.strip('"\'')
        
        return {"title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate title: {str(e)}")

@app.get("/api/model-capabilities")
async def get_model_capabilities():
    return {
        "models_with_image_support": MODELS_WITH_IMAGE_SUPPORT
    }

@app.post("/api/chat")
async def chat(chat_request: ChatRequest):
    try:
        # Handle both direct message form and structured request
        user_message = ""
        if chat_request.messages and len(chat_request.messages) > 0:
            for msg in chat_request.messages:
                if msg.role == "user":
                    if isinstance(msg.content, str):
                        user_message = msg.content
                        break
                    elif isinstance(msg.content, list):
                        # Handle complex message structure with text parts
                        for part in msg.content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                user_message = part.get("text", "")
                                break
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found in request")
        
        # Use the run_with_tools function to get a response
        try:
            response_content = run_with_tools(user_message, model=chat_request.model)
            
            # Record conversation in history if we have a conversation ID
            conversation_id = chat_request.conversation_id or str(uuid.uuid4())
            if conversation_id not in chat_history:
                chat_history[conversation_id] = []
                
            # Add to conversation history
            chat_history[conversation_id].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            chat_history[conversation_id].append({
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.now().isoformat()
            })
                
            return {
                "conversation_id": conversation_id,
                "response": response_content
            }
        except Exception as e:
            print(f"Error processing message with run_with_tools: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
    
    except Exception as e:
        print(f"Error in chat API: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

# Alternative endpoint that accepts form data for compatibility
@app.post("/api/chat/form")
async def chat_form(message: str = Form(...)):
    try:
        response_content = run_with_tools(message)
        return {"response": response_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/speech-to-text")
async def speech_to_text():
    try:
        # Call the recognize_speech function to get the transcribed text
        speech_result = recognize_speech()
        speech_data = json.loads(speech_result)
        
        if speech_data.get("status") == "success":
            # If speech recognition was successful, return the transcribed text
            return {"text": speech_data.get("text"), "status": "success"}
        else:
            # If there was an error during speech recognition
            return {"status": "error", "message": speech_data.get("message")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Проверка размера файла (максимум 4MB для большинства моделей)
        max_size = 4 * 1024 * 1024  # 4 MB
        file_size = 0
        contents = bytearray()
        
        while True:
            chunk = await file.read(8192)  # Чтение по частям, чтобы избежать проблем с памятью
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > max_size:
                raise HTTPException(status_code=413, detail="Image file too large (max 4MB)")
            contents.extend(chunk)
        
        # Проверка типа файла
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=415, detail="Uploaded file is not an image")
        
        encoded = base64.b64encode(contents).decode("utf-8")
        return {"image_data": encoded}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def get_conversations():
    return {
        "conversations": [
            {
                "id": conv_id,
                "title": chat_titles.get(conv_id, "Untitled Chat"),
                "timestamp": max([msg.get("timestamp", datetime.min.isoformat()) for msg in history], default=datetime.now().isoformat()) if history else datetime.now().isoformat()
            } for conv_id, history in chat_history.items()
        ]
    }

@app.post("/api/conversations/{conversation_id}/title")
async def set_conversation_title(conversation_id: str, title_update: ConversationTitleUpdate):
    # Если чат не существует, создаем его
    if conversation_id not in chat_history:
        chat_history[conversation_id] = []
    
    # Устанавливаем название чата
    chat_titles[conversation_id] = title_update.title
    return {"success": True, "title": title_update.title}

@app.get("/api/conversations/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    if conversation_id not in chat_history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "history": chat_history[conversation_id],
        "title": chat_titles.get(conversation_id, "Untitled Chat")
    }

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if conversation_id in chat_history:
        del chat_history[conversation_id]
    if conversation_id in chat_titles:
        del chat_titles[conversation_id]
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)