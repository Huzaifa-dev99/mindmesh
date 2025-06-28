"""Utility functions"""
import os
import base64
from dotenv import load_dotenv

load_dotenv(override=True)

def save_base64_file(content_b64: str, input_id: str, input_type: str) -> str:
    """Save base64 content to the appropriate file and return file path"""
    ext_map = {
        "image": ".png",
        "audio": ".mp3",
        "video": ".mp4"
    }

    ext = ext_map.get(input_type, ".bin")
    os.makedirs(f"{os.getenv("INPUT_PATH")}/{input_type}", exist_ok=True)
    file_path = f"{os.getenv("INPUT_PATH")}/{input_type}/{input_id}{ext}"

    with open(file_path, "wb") as f:
        f.write(base64.b64decode(content_b64.split(",")[-1]))

    return file_path
