# JARVIS Mobile App (Version 6)

Cross-platform Flutter mobile application for **JARVIS AI Assistant**.

---

## 📱 Features

1. 🎙️ **Talk Mode**: Interactive animated Arc Reactor voice visualizer with Edge-TTS speech synthesis.
2. 💬 **Chat Mode**: Real-time markdown conversational chat with quick suggestion chips and tools execution status.
3. 💻 **Laptop Telemetry Dashboard**: Live hardware monitoring gauges (CPU load %, RAM usage, SSD Disk space, Battery charge/plug state, OS architecture).
4. 🧠 **Memory Explorer**: View, search, and manage long-term facts, user preferences, and project tasks.
5. 🔔 **Notifications & Alerts**: Real-time hardware health alerts (e.g. low battery, high CPU spike, task deadlines).
6. ⚙️ **Settings**: Dynamic server host IP configuration (Local Wi-Fi / Hotspot / Emulator / Ngrok), API key auth, and voice response toggles.

---

## 🏗️ Architecture

```text
                  Internet / Local Wi-Fi
                            │
                     ┌──────▼──────┐
                     │   FastAPI   │
                     │   JARVIS    │
                     └──────┬──────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
         Laptop Agent                Mobile App
     (Local System Tools)        (Flutter Multiplatform)
```

---

## 🚀 How to Run the Mobile App

### Prerequisites
- [Flutter SDK (3.0+)](https://flutter.dev/docs/get-started/install)
- Android Studio / VS Code with Flutter extensions
- Android device or emulator / iOS Simulator

### 1. Ensure Backend Server is Running on Laptop:
```bash
# In the project root (e:/Jarvis)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
*(Using `--host 0.0.0.0` allows connections from other devices on your local Wi-Fi network)*

### 2. Configure Host Address in Mobile App Settings:
- **Android Studio Emulator**: Use `http://10.0.2.2:8000`
- **Physical Phone connected to same Wi-Fi**: Use `http://<YOUR-LAPTOP-IP>:8000` (e.g. `http://192.168.1.15:8000`)
- **iOS Simulator**: Use `http://127.0.0.1:8000`

### 3. Launch the Flutter App:
```bash
cd mobile
flutter pub get
flutter run
```
