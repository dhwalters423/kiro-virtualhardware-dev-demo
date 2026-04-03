# Pi Security Cam

A YOLOE-based security camera application for Raspberry Pi that detects a "knight in armor" using text-prompted zero-shot detection and streams annotated video via a web interface.

## Prerequisites

- Python 3.10+
- Raspberry Pi 4 (or ARM Virtual Hardware) with a USB webcam
- SSH access to the Pi

## Setup

1. Clone the repository:

```bash
git clone <repo-url>
cd pi-security-cam
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Configure SSH credentials:

```bash
cp .env.example .env
# Edit .env with your Pi's hostname, password, and SSH key path
```

4. (Optional) Edit `config.json` to adjust detection parameters:

```json
{
  "camera_device": 0,
  "confidence_threshold": 0.3,
  "web_port": 8080,
  "target_description": "knight in armor",
  "model_path": "yoloe-11s-seg.pt"
}
```

## Deploy to Pi

```bash
bash scripts/deploy.sh
```

## Run Tests on Pi

```bash
bash scripts/test.sh
```

Then open `test-reporter/index.html` in a browser to view results.

## Run Locally

```bash
python -m src.main --config config.json
```

Open `http://localhost:8080` in a browser to view the live feed.
