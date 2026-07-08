import base64
import binascii
import io
import os
from datetime import datetime, timezone

import face_recognition
import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from PIL import Image, ImageOps, UnidentifiedImageError
from pymongo import MongoClient


load_dotenv()

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/missing_person_db")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "missing_person_db")
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.6"))
FACE_DETECTION_MODEL = os.getenv("FACE_DETECTION_MODEL", "hog")
FACE_UPSAMPLE = int(os.getenv("FACE_UPSAMPLE", "1"))
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "900"))

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = mongo_client[MONGO_DB_NAME]
persons_collection = db["persons"]
app.config["PERSONS_COLLECTION"] = persons_collection


def utc_now():
    return datetime.now(timezone.utc)


def get_collection():
    return app.config["PERSONS_COLLECTION"]


def parse_request_data():
    if request.is_json:
        return request.get_json(silent=True) or {}

    data = request.form.to_dict()
    image_file = request.files.get("image")
    if image_file:
        data["image"] = base64.b64encode(image_file.read()).decode("utf-8")
    return data


def decode_image(image_payload):
    if not image_payload:
        raise ValueError("Image is required")

    if "," in image_payload:
        image_payload = image_payload.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image_payload, validate=True)
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (binascii.Error, UnidentifiedImageError, ValueError) as exc:
        raise ValueError("Image must be a valid base64-encoded image") from exc

    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
    return np.ascontiguousarray(np.asarray(image), dtype=np.uint8)


def largest_face_location(face_locations):
    return max(
        face_locations,
        key=lambda location: (location[2] - location[0]) * (location[1] - location[3]),
    )


def get_face_encoding(image_array):
    try:
        face_locations = face_recognition.face_locations(
            image_array,
            number_of_times_to_upsample=FACE_UPSAMPLE,
            model=FACE_DETECTION_MODEL,
        )
        if not face_locations and FACE_UPSAMPLE < 2:
            face_locations = face_recognition.face_locations(
                image_array,
                number_of_times_to_upsample=2,
                model=FACE_DETECTION_MODEL,
            )
        if not face_locations:
            return None

        face_location = largest_face_location(face_locations)
        encodings = face_recognition.face_encodings(image_array, [face_location])
    except RuntimeError as exc:
        raise ValueError("Face recognition could not process this image. Try a clear JPG or PNG face photo.") from exc

    if not encodings:
        return None
    return encodings[0]


def serialize_person(person, include_encoding=False):
    serialized = {
        "id": str(person["_id"]),
        "name": person.get("name", ""),
        "age": person.get("age"),
        "last_seen_location": person.get("last_seen_location", ""),
        "last_seen_date": person.get("last_seen_date", ""),
        "contact_info": person.get("contact_info", ""),
        "status": person.get("status", "missing"),
        "notes": person.get("notes", ""),
        "photo": person.get("photo", ""),
        "created_at": person.get("created_at").isoformat()
        if person.get("created_at")
        else None,
        "updated_at": person.get("updated_at").isoformat()
        if person.get("updated_at")
        else None,
    }

    if include_encoding:
        serialized["encoding"] = person.get("encoding", [])

    return serialized


def parse_object_id(person_id):
    try:
        return ObjectId(person_id)
    except (InvalidId, TypeError) as exc:
        raise ValueError("Invalid person id") from exc


def build_profile(data, existing=None):
    profile = {
        "name": (data.get("name") or "").strip(),
        "age": data.get("age") or None,
        "last_seen_location": (data.get("last_seen_location") or "").strip(),
        "last_seen_date": (data.get("last_seen_date") or "").strip(),
        "contact_info": (data.get("contact_info") or "").strip(),
        "status": (data.get("status") or "missing").strip().lower(),
        "notes": (data.get("notes") or "").strip(),
    }

    if existing:
        for key, value in profile.items():
            if key not in data:
                profile[key] = existing.get(key)

    if profile["age"] in ("", None):
        profile["age"] = None
    else:
        try:
            profile["age"] = int(profile["age"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Age must be a number") from exc

    if not profile["name"]:
        raise ValueError("Name is required")

    valid_statuses = {"missing", "found", "investigating"}
    if profile["status"] not in valid_statuses:
        raise ValueError("Status must be missing, found, or investigating")

    return profile


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/persons", methods=["POST"])
def create_person():
    data = parse_request_data()

    try:
        profile = build_profile(data)
        image_payload = data.get("image") or data.get("photo")
        image_array = decode_image(image_payload)
        face_encoding = get_face_encoding(image_array)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if face_encoding is None:
        return jsonify({"error": "No face found in the provided image"}), 400

    now = utc_now()
    person = {
        **profile,
        "photo": image_payload.split(",", 1)[-1],
        "encoding": face_encoding.tolist(),
        "created_at": now,
        "updated_at": now,
    }
    result = get_collection().insert_one(person)
    person["_id"] = result.inserted_id

    return jsonify({"person": serialize_person(person)}), 201


@app.route("/api/persons", methods=["GET"])
def list_persons():
    persons = list(get_collection().find({}).sort("created_at", -1))
    return jsonify({"persons": [serialize_person(person) for person in persons]})


@app.route("/api/persons/<person_id>", methods=["GET"])
def get_person(person_id):
    try:
        object_id = parse_object_id(person_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    person = get_collection().find_one({"_id": object_id})
    if not person:
        return jsonify({"error": "Person not found"}), 404

    return jsonify({"person": serialize_person(person)})


@app.route("/api/persons/<person_id>", methods=["PUT"])
def update_person(person_id):
    try:
        object_id = parse_object_id(person_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    existing = get_collection().find_one({"_id": object_id})
    if not existing:
        return jsonify({"error": "Person not found"}), 404

    data = parse_request_data()
    try:
        update_doc = build_profile(data, existing=existing)
        image_payload = data.get("image") or data.get("photo")
        if image_payload:
            image_array = decode_image(image_payload)
            face_encoding = get_face_encoding(image_array)
            if face_encoding is None:
                return jsonify({"error": "No face found in the provided image"}), 400
            update_doc["photo"] = image_payload.split(",", 1)[-1]
            update_doc["encoding"] = face_encoding.tolist()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    update_doc["updated_at"] = utc_now()
    get_collection().update_one({"_id": object_id}, {"$set": update_doc})
    updated = get_collection().find_one({"_id": object_id})

    return jsonify({"person": serialize_person(updated)})


@app.route("/api/persons/<person_id>", methods=["DELETE"])
def delete_person(person_id):
    try:
        object_id = parse_object_id(person_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result = get_collection().delete_one({"_id": object_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Person not found"}), 404

    return jsonify({"success": True})


@app.route("/api/match", methods=["POST"])
def match_face():
    data = parse_request_data()

    try:
        image_array = decode_image(data.get("image") or data.get("frame"))
        face_encoding = get_face_encoding(image_array)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if face_encoding is None:
        return jsonify({"matched": False, "reason": "No face detected"})

    known_people = [
        person
        for person in get_collection().find({"status": {"$ne": "found"}})
        if person.get("encoding")
    ]
    known_encodings = [np.array(person["encoding"]) for person in known_people]

    if not known_encodings:
        return jsonify({"matched": False, "reason": "No known missing persons"})

    distances = face_recognition.face_distance(known_encodings, face_encoding)
    best_match_index = int(np.argmin(distances))
    best_distance = float(distances[best_match_index])
    matched = best_distance <= MATCH_THRESHOLD

    response = {
        "matched": matched,
        "distance": best_distance,
        "threshold": MATCH_THRESHOLD,
        "confidence": max(0.0, round((1 - best_distance) * 100, 2)),
    }

    if matched:
        response["person"] = serialize_person(known_people[best_match_index])
    else:
        response["reason"] = "Unknown person"

    return jsonify(response)


# Backward-compatible endpoints for older scripts.
@app.route("/add_person", methods=["POST"])
def legacy_add_person():
    return create_person()


@app.route("/get_known_faces", methods=["GET"])
def legacy_get_known_faces():
    people = list(get_collection().find({"status": {"$ne": "found"}}))
    return jsonify(
        {
            "known_face_encodings": [person.get("encoding", []) for person in people],
            "known_face_names": [person.get("name", "") for person in people],
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
