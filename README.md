# 🔐 AI Theft Detection System

Real-time object theft detection using **YOLOv8 + OpenCV** with instant **WhatsApp mobile alerts**.

---

## 🚀 Features

- 🎯 YOLOv8 real-time object detection & tracking
- 🤝 Interaction detection (person/hand near item = safe)
- 👻 Occlusion-aware — won't false-alarm when item is being handled
- 🚨 Stolen alert after item missing for 5+ seconds
- 📱 Auto sends WhatsApp alert with screenshot to your phone
- 🖥️ Live HUD: `SCANNING` → `SECURE` → `INTERACTION` → `STOLEN!!`

---

## 🛠️ Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pyautogui

# 2. Set your phone number in theft_alert_code/main.py
TARGET_PHONE = "+91XXXXXXXXXX"

# 3. Run
cd theft_alert_code
python main.py
```

> Draw the **ROI (shelf/counter area)** on startup, then press `ENTER` to confirm.

---

## ⚙️ Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TARGET_PHONE` | — | Your WhatsApp number (international format) |
| `MISSING_TIME_THRESH` | `5.0s` | Seconds before triggering theft alert |
| `INTERACTION_PADDING` | `100px` | Proximity zone around items for interaction detection |

---

## 📦 Dependencies

`opencv-python` · `ultralytics` · `numpy` · `pyautogui` · `requests`


---

## ⚠️ Note

Keep **WhatsApp Web logged in** before running. Don't touch your mouse/keyboard for ~30s after a theft is detected — the alert automation needs control.

---


