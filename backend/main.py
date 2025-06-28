from fastapi import FastAPI
from uuid import uuid4
from datetime import datetime
from models import InputData
from db import save_input_to_db
import json
from utils import save_base64_file

app = FastAPI()

@app.post("/save-input")
async def save_input(data: InputData):
    input_id = data.id or str(uuid4())
    timestamp = data.timestamp or datetime.now().isoformat()

    # Will be replaced if it's base64
    content_raw = data.content_raw

    if data.type in ["image", "audio", "video"] and content_raw.startswith("data:"):
        # It's base64 media
        content_raw = save_base64_file(content_raw, input_id, data.type)

    # For text or other raw types, we keep content_raw as-is
    record = {
        "id": input_id,
        "type": data.type,
        "content_raw": content_raw,
        "source": data.source,
        "tags": json.dumps(data.tags or []),
        "timestamp": timestamp
    }

    save_input_to_db(record)

    return {"status": "ok", "id": input_id}
