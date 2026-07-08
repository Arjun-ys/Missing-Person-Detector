# Missing Person Detector

A full-stack AI application that registers missing-person profiles, stores facial encodings in MongoDB, and matches live webcam frames against active records using OpenCV, dlib, and face_recognition.

## Features

- Browser-based missing-person registration with image preview and case metadata.
- MongoDB-backed profile management for viewing, editing, deleting, and updating case status.
- Flask REST API for person records and real-time face matching.
- Live webcam matching in the web app through `navigator.mediaDevices.getUserMedia`.
- Optional OpenCV desktop detector in `detector.py` for two-terminal demos.

## Tech Stack

- Python, Flask, REST API
- OpenCV, dlib, face_recognition
- MongoDB Atlas or local MongoDB
- HTML, CSS, JavaScript

## Setup

1. Create and activate a virtual environment.

    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

2. Install dependencies.

    ```bash
    pip install -r requirements.txt
    ```

    On Windows, `dlib` may require CMake and C++ Build Tools. If regular installation fails, install a Python-version-compatible `dlib` wheel first, then rerun the requirements command.

3. Configure MongoDB.

    ```bash
    copy .env.example .env
    ```

    For MongoDB Atlas, edit `.env` and set `MONGO_URI` to your Atlas connection string. For local MongoDB, the default URI works if MongoDB is running locally.

## Run The Web App

```bash
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

Recommended demo flow:

1. Register a missing-person profile with a clear face image.
2. Confirm the record appears in Saved Records.
3. Start the webcam in Live Webcam Match.
4. Show matched, unknown, and no-face states from the browser.

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
