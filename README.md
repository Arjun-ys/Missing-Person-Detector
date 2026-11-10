# Missing Person Detector

A full-stack AI application that registers missing-person profiles, stores facial encodings in MongoDB, and matches live webcam frames against active records using OpenCV, dlib, and face_recognition.

## Features

- Browser-based missing-person registration with image preview and case metadata.
- MongoDB-backed profile management for viewing, editing, deleting, and updating case status.
- Flask REST API for person records and real-time face matching.
- Live webcam matching in the web app through `navigator.mediaDevices.getUserMedia`.
- Optional OpenCV desktop detector in `detector.py` for two-terminal demos.

## Tech Stack

- **Backend**: Python 3.12, Flask, REST API
- **Computer Vision / AI**: OpenCV, dlib, `face_recognition`, Pillow, NumPy
- **Database**: MongoDB Atlas or local MongoDB (PyMongo)
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (WebRTC `getUserMedia` + Canvas API)

---

## Architecture Diagrams

### 1. System Architecture (How the Project Works)

```mermaid
flowchart TB
    subgraph Client["Browser Client (HTML / CSS / JS)"]
        UI_Reg["Register Person Form\n(Case Details + Face Photo)"]
        UI_Rec["Saved Records Panel\n(View / Edit / Delete)"]
        UI_Cam["Live Webcam Match\n(getUserMedia + Canvas 1.8s loop)"]
    end

    subgraph Backend["Flask Backend (app.py)"]
        API_Persons["CRUD Routes\n/api/persons"]
        API_Match["Match Route\nPOST /api/match"]
        Decoder["decode_image()\nBase64 -> Pillow RGB -> Resize <= 900px"]
        Encoder["get_face_encoding()\nHOG Face Detection -> dlib 128-D Vector"]
        Matcher["face_distance()\nEuclidean Distance Check (Threshold <= 0.6)"]
    end

    subgraph DB["MongoDB (missing_person_db)"]
        Collection[("persons Collection\n• Profile Metadata & Status\n• Base64 Photo\n• 128-D Float Encoding")]
    end

    subgraph Desktop["Optional Desktop Mode (detector.py)"]
        CV2["OpenCV VideoCapture\nLocal Webcam + Bounding Box"]
    end

    UI_Reg -->|"POST JSON + Base64 Photo"| API_Persons
    API_Persons --> Decoder --> Encoder -->|"insert_one()"| Collection
    UI_Rec <-->|"GET / PUT / DELETE"| API_Persons <--> Collection

    UI_Cam -->|"POST Frame (JPEG Base64)"| API_Match
    API_Match --> Decoder --> Encoder --> Matcher
    Collection -->|"Load Active Records (status != 'found')"| Matcher
    Matcher -->|"JSON: matched, confidence %, person"| UI_Cam

    CV2 -->|"GET /get_known_faces"| API_Persons
```

### 2. Frontend & Backend Interaction Flow

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Browser
    participant FE as Frontend (script.js + index.html)
    participant BE as Backend API (Flask / app.py)
    participant AI as Vision Engine (Pillow + dlib)
    participant DB as MongoDB (persons)

    rect rgba(59, 130, 246, 0.12)
        note over User,DB: Flow 1: Registering a Missing Person
        User->>FE: Fill form & choose face image
        FE->>FE: FileReader encodes image to Base64 Data URL
        FE->>BE: POST /api/persons (JSON metadata + image)
        BE->>AI: decode_image() -> EXIF transpose, RGB, max 900px
        AI->>AI: face_locations() (HOG) + face_encodings() (128-D)
        AI-->>BE: Return 128-float face vector
        BE->>DB: insert_one(profile, photo, encoding, timestamps)
        DB-->>BE: Return inserted_id
        BE-->>FE: 201 Created (serialized person without encoding)
        FE->>User: Render profile card in Saved Records
    end

    rect rgba(16, 185, 129, 0.12)
        note over User,DB: Flow 2: Live Webcam Face Matching
        User->>FE: Click "Start Camera" & allow permissions
        loop Every 1800 ms
            FE->>FE: Draw video frame onto hidden canvas (480px JPEG)
            FE->>BE: POST /api/match (Base64 frame)
            BE->>AI: Decode frame & extract live 128-D face encoding
            BE->>DB: find({ status: { $ne: "found" } })
            DB-->>BE: Return active missing-person encodings
            BE->>AI: face_distance(known_encodings, live_encoding)
            AI-->>BE: Minimum Euclidean distance (match if <= 0.6)
            BE-->>FE: 200 OK (matched, confidence %, distance, person)
            FE->>User: Update Match Banner (Matched / Unknown / No Face)
        end
    end
```

---

## Setup

### 1. Create and Activate a Virtual Environment

**macOS / Linux:**
```bash
uv venv
source .venv/bin/activate
```
*(Or using standard Python: `python3 -m venv .venv && source .venv/bin/activate`)*

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies

**macOS (Apple Silicon):**
Requires `cmake` (`brew install cmake`) for `dlib`. Disable dlib's legacy bundled PNG loader on modern macOS SDKs:
```bash
CMAKE_ARGS="-DDLIB_PNG_SUPPORT=OFF" uv pip install -r requirements.txt
```

**Windows / Linux:**
```bash
pip install -r requirements.txt
```
*(On Windows, `dlib` requires CMake and Visual Studio C++ Build Tools. If installation fails, install a Python-version-compatible `dlib` wheel first, then rerun `pip install -r requirements.txt`.)*

### 3. Configure MongoDB

```bash
cp .env.example .env
```
*(On Windows CMD, use `copy .env.example .env`)*

For MongoDB Atlas, edit `.env` and set `MONGO_URI` to your Atlas connection string. For local MongoDB (native or via Docker on port `27017`), the default `.env` URI works out of the box.

---

## Run The Web App

```bash
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

> **macOS Note:** macOS enables **AirPlay Receiver** on port `5000` by default. If you see `Address already in use`, disable **AirPlay Receiver** in **System Settings → General → AirDrop & AirPlay**.

Recommended demo flow:

1. Register a missing-person profile with a clear face image.
2. Confirm the record appears in **Saved Records**.
3. Start the webcam in **Live Webcam Match**.
4. Observe matched, unknown, and no-face states from the browser.

## Optional Desktop Detector

Start the Flask app first, then run:

```bash
python detector.py
```

The detector uses `API_BASE_URL` and `MATCH_THRESHOLD` from `.env`. Press `q` to close the OpenCV window.

## API Summary

- `POST /api/persons` - create a missing-person record with profile fields and image.
- `GET /api/persons` - list saved records without raw face encodings.
- `GET /api/persons/<id>` - fetch one record.
- `PUT /api/persons/<id>` - update profile metadata, status, and optionally face image.
- `DELETE /api/persons/<id>` - delete one record.
- `POST /api/match` - match a base64 webcam frame against active missing-person records.

Legacy endpoints `/add_person` and `/get_known_faces` remain available for older scripts.

## Tests

```bash
python -m pytest
```

The tests use mocked face-recognition behavior and an in-memory collection, so they do not require a live MongoDB server or webcam.
