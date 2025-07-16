from fastapi import FastAPI, HTTPException
from uuid import uuid4
from datetime import datetime
from models import InputData
from db import save_input_to_db
import json
from utils import save_base64_file
import logging

app = FastAPI()

# Optional: Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/save-input")
async def save_input(data: InputData):
    try:
        input_id = data.id or str(uuid4())
        timestamp = data.timestamp or datetime.now().isoformat()

        content_raw = data.content_raw

        if not content_raw:
            raise HTTPException(status_code=400, detail="`content_raw` cannot be empty.")

        if data.type in {"image", "audio", "video"}:
            if content_raw.startswith("data:"):
                try:
                    content_raw = save_base64_file(content_raw, input_id, data.type)
                except Exception as e:
                    logger.error(f"Failed to save base64 file: {e}")
                    raise HTTPException(status_code=500, detail="Error processing media content.")
            else:
                logger.warning(f"Expected base64 for media type '{data.type}', but got raw data.")

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

    except Exception as e:
        logger.exception("Unhandled exception in /save-input")
        raise HTTPException(status_code=500, detail="Internal server error.")
