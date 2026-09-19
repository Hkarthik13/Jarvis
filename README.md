# JARVIS AI Assistant (Version 10 — Advanced Unified Architecture) ⚡

JARVIS (Just A Rather Very Intelligent System) is a state-of-the-art personal AI assistant unifying **FastAPI Gateway**, **Groq AI Brain LLMs**, **Edge-TTS Neural Voice**, **Whisper STT**, **Hybrid SQLite Vector Memory**, **Personal Knowledge RAG Vault**, **Windows Laptop Agent**, **Multi-Action Automation Engine**, and a **Cross-Platform Flutter Mobile Client**.

---

## 🏛️ Final Architecture

```text
                    ┌────────────────────────┐
                    │   MOBILE & WEB CLIENT  │
                    │ (Flutter Cyberpunk UI) │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    FASTAPI GATEWAY     │
                    │  (REST, WS, Security)  │
                    └───────────┬────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
  │   AI BRAIN   │       │ MEMORY & RAG │       │ TOOLS ENGINE │
  │  (Groq LLM)  │       │ (SQLite +Vec)│       │(Laptop Agent)│
  └──────┬───────┘       └──────┬───────┘       └──────┬───────┘
         │                      │                      │
         ▼                      ▼                      ▼
  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
  │ VOICE ENGINE │       │DOCUMENTS & DB│       │   WINDOWS    │
  │(Whisper +TTS)│       │(Vault Search)│       │ (System/Apps)│
  └──────────────┘       └──────────────┘       └──────────────┘
```

---

## 🌟 Version 10 Core Capabilities & Endpoints

### 1. Unified FastAPI Gateway (`/api/gateway/interact`)
Single multi-modal gateway endpoint that routes requests across:
- **Natural Language Routine Triggering**: Instant execution of multi-step workflows (`start_work`, `prepare_interview`, `focus_mode`, `relax_mode`, `lockdown`).
- **AI Brain Reasoning Loop**: Multi-step tool-calling with context injection.
- **RAG Ground-Truth Citations**: Automatic citation matching and relevance scoring.
- **Voice MP3 Synthesis**: Streaming Edge-TTS natural voice (`en-US-AnaNeural`).

### 2. Multi-Modal Voice Interaction (`/api/gateway/voice-interact`)
Audio recording upload -> Whisper STT (`whisper-large-v3-turbo`) -> Gateway Reasoning -> Edge-TTS Audio -> Base64 MP3 response.

### 3. Unified Diagnostics Suite (`/api/gateway/system-summary`)
Real-time telemetry aggregating:
- **Hardware**: CPU Load %, Logical Cores, RAM (GB / %), Disk Storage (GB / %), Battery & AC power.
- **Subsystems Health**: Groq AI Brain, SQLite Memory, RAG Knowledge Vault, Windows Laptop Agent, Automation Engine, Whisper/TTS.
- **Entity Counts**: Active Memories, Open Tasks, Indexed Documents, Knowledge Chunks, Workflows, Registered Tools.

---

## 📱 Mobile App (Version 10 Experience)

The Flutter mobile client provides a dark glassmorphism cyberpunk command center:
1. 🟢 **Gateway Status Bar**: Live header showing gateway connectivity, AI Brain, RAG Vault, and Windows Agent state with full diagnostics modal.
2. 🎙️ **Talk Mode**: Interactive animated Arc Reactor voice visualizer with Edge-TTS speech output.
3. 💬 **Chat Mode**: Real-time markdown conversational chat with tool execution logs.
4. 🧠 **Personal Knowledge / RAG Deck**: Multi-format document explorer, semantic search bar, and interactive source citation chips.
5. ⚡ **Automation Routines Deck**: Quick-launch buttons for routines, real-time step visualizer, and custom workflow builder.
6. 💻 **Laptop Telemetry Dashboard**: Live gauges for CPU %, RAM %, SSD Disk %, and battery status.
7. 🧠 **Memory Explorer**: Persistent long-term facts, user preferences, and task management.
8. 🔔 **Alerts & Diagnostics**: Real-time notifications and hardware alerts.
9. ⚙️ **Settings**: Dynamic server host IP configuration, API key auth, and speech toggles.

---

## 🚀 Complete Evolution Roadmap (V1 — V10)

| Version | Feature Layer | Key Technologies |
|---|---|---|
| **V1** | Voice-to-Voice Pipeline | Whisper STT (`whisper-large-v3-turbo`) + Groq LLM + Edge-TTS |
| **V2** | Safe Laptop Controls | Safe system apps, browser URLs, file explorer, hardware telemetry |
| **V4** | Live Internet & Search | Open-Meteo weather, DuckDuckGo search, YouTube search, scraper |
| **V5** | Persistent Memory | SQLite WAL, semantic vector recall (256-dim), preference store, tasks |
| **V6** | Flutter Mobile Client | Cyberpunk Glassmorphism UI, cross-platform Android/iOS/Windows |
| **V7** | Remote Control & Agent | HMAC-SHA256 auth, screen capture, media volume, workstation lock |
| **V8** | Automation & Workflows | Multi-action routines engine, natural trigger matcher, custom builder |
| **V9** | Personal Knowledge / RAG | PDF/MD/Code chunker, vector store, hybrid search, citation synthesis |
| **V10** | Advanced Unified Gateway | Cohesive FastAPI Gateway, multi-modal interaction, system diagnostics |

---

## 📁 Repository Structure

```text
jarvis/
├── backend/
│   ├── main.py               # FastAPI Gateway & REST endpoints (v10.0.0)
│   ├── config.py             # Pydantic Settings & environment variables
│   ├── core/
│   │   ├── __init__.py
│   │   ├── gateway.py        # Central JarvisGatewayOrchestrator
│   │   └── models.py         # Unified interaction & diagnostics schemas
│   ├── ai/
│   │   ├── client.py         # Groq LLM reasoning loop & orchestrator
│   │   ├── registry.py       # Central ToolRegistry
│   │   ├── tools.py          # Safe system control tools
│   │   ├── internet_tools.py # V4 Live search & weather tools
│   │   ├── memory_tools.py   # V5 Memory recall & task tools
│   │   ├── remote_tools.py   # V7 Remote execution tools
│   │   ├── workflow_tools.py # V8 Automation routine tools
│   │   └── knowledge_tools.py# V9 Personal Knowledge & RAG tools
│   ├── automation/
│   │   ├── models.py         # Workflow & step schemas
│   │   └── engine.py         # Workflow execution engine & triggers
│   ├── knowledge/
│   │   ├── models.py         # DocumentSource & DocumentChunk schemas
│   │   ├── parser.py         # Multi-format extractors & chunker
│   │   └── engine.py         # Hybrid RAG search & vault scanner
│   ├── memory/
│   │   ├── database.py       # SQLite engine, sessions, WAL mode
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── vector_store.py   # 256-dim embeddings & cosine similarity
│   │   └── service.py        # High-level MemoryService API
│   ├── remote/
│   │   ├── laptop_agent.py   # System execution & hardware control
│   │   └── hub.py            # WebSocket & mobile controller hub
│   ├── voice/
│   │   ├── stt.py            # Whisper Audio transcription
│   │   └── tts.py            # Edge-TTS Audio synthesis
│   └── utils/
│       └── logger.py         # Loguru logger
├── knowledge_vault/          # Personal documents repository (Resumes, Projects, Notes)
│   ├── ai_resume_analyzer_project.md
│   ├── resume.md
│   └── ...
├── mobile/                   # Flutter Mobile App (Version 10)
│   ├── pubspec.yaml
│   └── lib/
│       ├── config/           # API endpoints & host configuration
│       ├── models/           # Models (Gateway, Knowledge, Workflows, Memory, System, Chat)
│       ├── providers/        # State management providers
│       ├── screens/          # Talk, Chat, RAG, Routines, Laptop, Memory, Alerts, Settings
│       ├── services/         # HTTP ApiService client
│       ├── theme/            # Glassmorphism dark cyberpunk theme
│       └── widgets/          # GatewayStatusBar, GlowingOrb, GlassContainer
├── tests/                    # Comprehensive Test Suite (100% Pass Rate)
│   ├── test_imports.py
│   ├── test_tools.py
│   ├── test_agent.py
│   ├── test_internet_tools.py
│   ├── test_memory.py
│   ├── test_remote_control.py
│   ├── test_automation.py
│   ├── test_rag_knowledge.py
│   └── test_v10_gateway.py
├── run_jarvis.py             # Server launcher with LAN discovery
├── start_jarvis.bat          # Windows double-click server runner
├── launch_jarvis_app.bat     # Windows double-click client runner
├── jarvis_memory.db          # Persistent SQLite memory database
├── jarvis_workflows.json     # Custom routines store
└── README.md
```

---

## 🛠️ Quick Start & Setup

### 1. Launch JARVIS Backend Gateway:
```bash
# In the project root (e:/Jarvis)
python run_jarvis.py
# Or double-click: start_jarvis.bat
```

### 2. Launch Mobile App:
```bash
cd mobile
flutter run
# Or double-click: launch_jarvis_app.bat
```
