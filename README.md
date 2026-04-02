# 📄 OMR Scanner — Optical Mark Recognition System

A **ZipGrade-style** answer sheet scanner that reads filled bubble sheets using your phone camera. Built with **React + FastAPI + OpenCV**.

<p align="center">
  <img src="docs/demo.gif" width="300" alt="Demo" />
</p>

---

## ✨ Features

- **📋 Form Generator** — Creates printable A4 optical answer sheets (PDF) with ArUco alignment markers
- **📷 Camera Scanner** — Scan answer sheets using your phone camera (or upload photos)
- **🤖 OMR Engine** — OpenCV-powered bubble detection with adaptive thresholding
- **📊 Auto Grading** — Instant scoring against your answer key
- **📈 Statistics** — Class averages, score distribution, per-question analysis
- **📥 CSV Export** — Download all results for further analysis
- **🔧 Configurable** — 20 to 100 questions, A-B-C-D-E options

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────┐
│   React + Vite  │────▶│   FastAPI Backend     │
│   (Frontend)    │     │                       │
│                 │     │  ┌──────────────────┐ │
│  • Camera       │     │  │  OMR Engine      │ │
│  • Answer Key   │ API │  │  (OpenCV)        │ │
│  • Results      │◀────│  │  • ArUco detect  │ │
│  • Stats        │     │  │  • Perspective   │ │
│                 │     │  │  • Bubble read   │ │
└─────────────────┘     │  └──────────────────┘ │
                        │  ┌──────────────────┐ │
                        │  │  Form Generator  │ │
                        │  │  (ReportLab)     │ │
                        │  └──────────────────┘ │
                        └──────────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/YOUR_USERNAME/omr-scanner.git
cd omr-scanner
docker-compose up --build
```

Open **http://localhost:3000** on your phone or computer.

### Option 2: Manual Setup

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

> **Note:** For manual setup, update `vite.config.js` proxy target from `http://backend:8000` to `http://localhost:8000`.

## 📖 How to Use

### Step 1: Print the Form

1. Go to **Setup** tab
2. Select question count (20/40/60/80/100)
3. Click **"Download printable form"** to get the PDF
4. Print on A4 paper

### Step 2: Set Answer Key

1. In Setup tab, click each question's correct answer (A-B-C-D-E)
2. Click **"Start scanning"**

### Step 3: Scan Sheets

1. Go to **Scan** tab
2. Point your camera at a filled answer sheet
3. Align the 4 corner markers within the guide frame
4. Tap the capture button
5. Results appear instantly!

### Step 4: View Results

- **Results** tab shows all scanned sheets with scores
- Export to CSV for Excel/Google Sheets

## 📄 Answer Sheet Layout

The generated form includes:

```
┌──────────────────────────────────┐
│ [ArUco 0]          [ArUco 1]    │  ← Corner markers
│                                  │
│        SINAV OPTIK FORMU         │
│  Name: ___________  Class: ___   │
│                                  │
│  STUDENT NO                      │
│  ①②③④⑤⑥⑦⑧⑨⑩                    │  ← 10-digit bubble grid
│  ⓪⓪⓪⓪⓪⓪⓪⓪⓪⓪                    │
│  ...                             │
│                                  │
│  ANSWERS                         │
│  1. ⓐⓑⓒⓓⓔ  11. ⓐⓑⓒⓓⓔ         │  ← Answer bubbles
│  2. ⓐⓑⓒⓓⓔ  12. ⓐⓑⓒⓓⓔ         │
│  ...                             │
│                                  │
│ [ArUco 2]          [ArUco 3]    │  ← Corner markers
└──────────────────────────────────┘
```

## 🔬 How OMR Works

1. **ArUco Detection** — 4 corner markers are detected using OpenCV's ArUco module
2. **Perspective Transform** — Image is warped to a flat, top-down view regardless of camera angle
3. **Adaptive Thresholding** — Handles different lighting conditions (fluorescent, daylight, shadows)
4. **Bubble Analysis** — Each bubble region is masked with a circle and fill ratio is calculated
5. **Decision Logic**:
   - Fill ratio > 35% → marked
   - If multiple bubbles filled → picks highest or flags as ambiguous
   - Confidence score indicates detection reliability

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python 3.11, FastAPI |
| OMR Engine | OpenCV 4.10 (ArUco + adaptive threshold) |
| PDF Generation | ReportLab |
| Camera | react-webcam |
| Containerization | Docker, Docker Compose |

## 📁 Project Structure

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes
│   │   ├── omr_engine.py      # OpenCV OMR processing
│   │   ├── form_generator.py  # PDF form creation
│   │   └── models.py          # Pydantic schemas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main React app
│   │   ├── main.jsx           # Entry point
│   │   └── index.css          # Tailwind styles
│   ├── nginx.conf
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🎯 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/forms/download/{n}` | Download blank form PDF |
| `POST` | `/api/forms/generate` | Generate custom form |
| `POST` | `/api/sessions/create` | Create exam session with answer key |
| `GET` | `/api/sessions/{id}` | Get session details |
| `POST` | `/api/scan` | Scan from uploaded image |
| `POST` | `/api/scan/base64` | Scan from base64 (camera) |
| `GET` | `/api/sessions/{id}/stats` | Get exam statistics |
| `GET` | `/api/sessions/{id}/export` | Export results as CSV |

## ⚙️ Configuration

Key parameters in `omr_engine.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fill_threshold` | 0.35 | Min fill ratio to consider bubble marked |
| `ambiguity_threshold` | 0.15 | Min difference between top-2 bubbles |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco dictionary type |

## 🔧 Troubleshooting

**"Could not find all 4 markers"**
- Ensure all 4 corner markers are visible in the photo
- Avoid shadows on the markers
- Hold the camera steady, ~30cm above the sheet

**Low accuracy**
- Use a dark pen/pencil to fill bubbles completely
- Ensure good, even lighting
- Avoid crumpled or folded papers

**Camera not working**
- Allow camera permissions in your browser
- Use HTTPS or localhost (camera requires secure context)

## 📝 License

MIT License — Free for educational and commercial use.

---

Built with ❤️ for educators who deserve better tools.
