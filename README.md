# 🧠 MindMesh

A powerful FastAPI-based backend for handling natural language queries, audio input, and dynamic chart generation from structured and unstructured data sources.

---

## 🚀 Features

- 🎙️ **Audio Input Support** — Submit and process voice input in real-time
- 🧾 **Natural Language Querying** — Understand and respond to queries on structured (tabular) and unstructured data
- 📊 **Chart and Visualization Generator** — Auto-generates visuals from queries
- 🔐 **Compliance-Ready Architecture** — Designed with data governance in mind

---

## 🛠️ Tech Stack

- **Backend**: FastAPI
- **Database**: SQLite (with plans to support PostgreSQL)
- **ORM**: SQLAlchemy (recommended)
- **Deployment**: Uvicorn
- **Language**: Python 3.12+

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mindmesh.git
cd mindmesh

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Running the App

```bash
# Start the FastAPI server
uvicorn backend.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` to explore the interactive Swagger UI.

---

## 📂 Project Structure

```
mindmesh/
│
├── backend/
│   ├── main.py         # FastAPI app
│   ├── db.py           # Database functions
│   └── ...
├── requirements.txt
└── README.md
```

---

## ❤️ Contributing

We welcome contributions! Please submit a pull request or open an issue to discuss improvements, bugs, or new ideas.
