import streamlit as st
import base64
import requests
import datetime
from PIL import Image
import io
import fitz  # PyMuPDF
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, AudioProcessorBase

st.set_page_config(page_title="📥 Capture | MindMesh", layout="wide")

# Sidebar Upload
st.sidebar.title("📎 Upload Inspiration")
uploaded_file = st.sidebar.file_uploader(
    "Choose a file (text, image, audio, video, PDF)", 
    type=["txt", "png", "mp3", "mp4", "pdf"]
)

input_type = None
content_raw = None
file_preview = None

# Auto-detect type and read content
if uploaded_file:
    mime = uploaded_file.type
    file_bytes = uploaded_file.read()

    if mime.startswith("image/"):
        input_type = "image"
        content_raw = f"data:{mime};base64,{base64.b64encode(file_bytes).decode()}"
        file_preview = Image.open(io.BytesIO(file_bytes))

    elif mime.startswith("audio/"):
        input_type = "audio"
        content_raw = f"data:{mime};base64,{base64.b64encode(file_bytes).decode()}"

    elif mime.startswith("video/"):
        input_type = "video"
        content_raw = f"data:{mime};base64,{base64.b64encode(file_bytes).decode()}"

    elif mime == "application/pdf":
        input_type = "text"
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                text = "\n".join([page.get_text() for page in doc])
                content_raw = text.strip()
        except Exception as e:
            st.error(f"Failed to parse PDF: {e}")

    elif mime.startswith("text/"):
        input_type = "text"
        content_raw = file_bytes.decode("utf-8")

# Main UI
st.title("📥 Capture Inspiration")

if input_type:
    st.markdown(f"### Preview: `{input_type}` content")

    if input_type == "image":
        st.image(file_preview, caption="Uploaded Image", use_column_width=True)
    elif input_type == "text":
        st.code(content_raw[:2000], language="text")  # Limit long previews
    elif input_type == "audio":
        st.audio(content_raw)
    elif input_type == "video":
        st.video(content_raw)

    st.divider()

    # Metadata
    st.subheader("📝 Add Metadata")
    source = st.text_input("Source (e.g. upload, web, notes)", "upload")
    tags = st.text_input("Tags (comma-separated)")
    notes = st.text_area("Additional Notes")

    if st.button("💾 Save Input"):
        payload = {
            "type": input_type,
            "content_raw": content_raw,
            "source": source,
            "tags": [tag.strip() for tag in tags.split(",") if tag],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        if notes:
            if input_type == "text":
                payload["content_raw"] += f"\n\nNotes:\n{notes}"
            else:
                payload["notes"] = notes

        try:
            res = requests.post("http://localhost:8000/save-input", json=payload)
            res.raise_for_status()
            st.success(f"✅ Saved! ID: {res.json().get('id')}")
        except Exception as e:
            st.error(f"❌ Save failed: {e}")
else:
    st.info("📂 Upload a file from the sidebar to begin.")


st.sidebar.markdown("### 📷 Capture from Camera / Mic")
capture_mode = st.sidebar.selectbox("Choose capture mode", ["None", "Take Photo", "Record Audio", "Record Video"])

if capture_mode == "Take Photo":
    class SnapshotTransformer(VideoTransformerBase):
        def __init__(self):
            self.frame = None

        def transform(self, frame):
            self.frame = frame.to_ndarray(format="bgr24")
            return frame

    ctx = webrtc_streamer(
        key="snapshot",
        video_transformer_factory=SnapshotTransformer,
        media_stream_constraints={"video": True, "audio": False},
    )

    if ctx.video_transformer and ctx.video_transformer.frame is not None:
        st.image(ctx.video_transformer.frame, caption="📸 Captured Frame", channels="BGR")
        if st.button("💾 Save Photo"):
            input_type = "image"
            image = Image.fromarray(ctx.video_transformer.frame)
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            content_raw = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            file_preview = image

elif capture_mode == "Record Audio":
    webrtc_ctx = webrtc_streamer(
        key="audio",
        mode="sendonly",
        audio_processor_factory=AudioProcessorBase,
        media_stream_constraints={"video": False, "audio": True},
    )
    st.info("🎤 Record audio and click Save Input after you're done.")

elif capture_mode == "Record Video":
    webrtc_ctx = webrtc_streamer(
        key="video-record",
        mode="sendonly",
        media_stream_constraints={"video": True, "audio": True},
    )
    st.info("🎥 Recording... click Save Input when you're done.")
