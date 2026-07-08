import os

import cv2
import face_recognition
import numpy as np
import requests
from dotenv import load_dotenv


load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.6"))


def fetch_known_faces_from_api():
    try:
        response = requests.get(f"{API_BASE_URL}/api/persons", timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not fetch people from API: {exc}")
        return [], []

    people = response.json().get("persons", [])
    names = []
    encodings = []

    # The public list endpoint intentionally omits encodings, so use the
    # legacy endpoint for this optional local detector mode.
    try:
        response = requests.get(f"{API_BASE_URL}/get_known_faces", timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not fetch face encodings from API: {exc}")
        return [], []

    data = response.json()
    for name, encoding in zip(
        data.get("known_face_names", []),
        data.get("known_face_encodings", []),
    ):
        names.append(name)
        encodings.append(np.array(encoding))

    print(f"Loaded {len(names)} active records from {API_BASE_URL}.")
    return encodings, names


def run_detection(known_face_encodings, known_face_names):
    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("Could not open webcam.")
        return

    print("Starting desktop detector. Press q to quit.")

    while True:
        ok, frame = video_capture.read()
        if not ok:
            break

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame,
            face_locations,
        )

        for (top, right, bottom, left), face_encoding in zip(
            face_locations,
            face_encodings,
        ):
            name = "Unknown"
            if known_face_encodings:
                distances = face_recognition.face_distance(
                    known_face_encodings,
                    face_encoding,
                )
                best_match_index = int(np.argmin(distances))
                if distances[best_match_index] <= MATCH_THRESHOLD:
                    name = known_face_names[best_match_index]
                    print(f"Match found: {name}")

            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (18, 105, 224), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (18, 105, 224), cv2.FILLED)
            cv2.putText(
                frame,
                name,
                (left + 6, bottom - 8),
                cv2.FONT_HERSHEY_DUPLEX,
                0.8,
                (255, 255, 255),
                1,
            )

        cv2.imshow("Missing Person Detector", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    encodings, names = fetch_known_faces_from_api()
    if not names:
        print("No active missing-person encodings found. Add records in the web app first.")
    else:
        run_detection(encodings, names)
