import base64
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest
from bson import ObjectId

import app as missing_app


TINY_IMAGE = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class FakeCursor(list):
    def sort(self, key, direction):
        reverse = direction == -1
        return FakeCursor(sorted(self, key=lambda item: item.get(key) or datetime.min, reverse=reverse))


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def insert_one(self, doc):
        doc["_id"] = ObjectId()
        self.docs.append(doc.copy())
        return SimpleNamespace(inserted_id=doc["_id"])

    def find(self, query=None, projection=None):
        query = query or {}
        docs = [doc.copy() for doc in self.docs if self._matches(doc, query)]
        return FakeCursor(docs)

    def find_one(self, query):
        for doc in self.docs:
            if self._matches(doc, query):
                return doc.copy()
        return None

    def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)

    def delete_one(self, query):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                del self.docs[index]
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def _matches(self, doc, query):
        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict) and "$ne" in expected:
                if actual == expected["$ne"]:
                    return False
            elif actual != expected:
                return False
        return True


@pytest.fixture()
def client(monkeypatch):
    collection = FakeCollection()
    missing_app.app.config["TESTING"] = True
    missing_app.app.config["PERSONS_COLLECTION"] = collection
    monkeypatch.setattr(
        missing_app.face_recognition,
        "face_locations",
        lambda image, *args, **kwargs: [(0, 1, 1, 0)],
    )
    monkeypatch.setattr(
        missing_app.face_recognition,
        "face_encodings",
        lambda image, locations=None: [np.array([0.1, 0.2, 0.3])],
    )
    with missing_app.app.test_client() as test_client:
        test_client.fake_collection = collection
        yield test_client


def test_create_person_requires_name_and_image(client):
    response = client.post("/api/persons", json={"name": ""})

    assert response.status_code == 400
    assert "Name is required" in response.get_json()["error"]


def test_create_person_rejects_image_with_no_face(client, monkeypatch):
    monkeypatch.setattr(missing_app.face_recognition, "face_encodings", lambda image, locations=None: [])

    response = client.post("/api/persons", json={"name": "Asha Rao", "image": TINY_IMAGE})

    assert response.status_code == 400
    assert response.get_json()["error"] == "No face found in the provided image"


def test_create_person_stores_profile_and_list_omits_encoding(client):
    response = client.post(
        "/api/persons",
        json={
            "name": "Asha Rao",
            "age": "24",
            "last_seen_location": "MG Road",
            "last_seen_date": "2026-07-01",
            "contact_info": "family@example.com",
            "status": "missing",
            "notes": "Blue jacket",
            "image": TINY_IMAGE,
        },
    )

    assert response.status_code == 201
    created = response.get_json()["person"]
    assert created["name"] == "Asha Rao"
    assert created["age"] == 24

    list_response = client.get("/api/persons")
    listed = list_response.get_json()["persons"][0]
    assert listed["name"] == "Asha Rao"
    assert "encoding" not in listed
    assert client.fake_collection.docs[0]["encoding"] == [0.1, 0.2, 0.3]


def test_match_returns_no_known_persons_when_database_empty(client):
    response = client.post("/api/match", json={"image": TINY_IMAGE})

    assert response.status_code == 200
    assert response.get_json()["matched"] is False
    assert response.get_json()["reason"] == "No known missing persons"


def test_match_returns_best_known_person(client, monkeypatch):
    person_id = ObjectId()
    now = datetime.now(timezone.utc)
    client.fake_collection.docs.append(
        {
            "_id": person_id,
            "name": "Asha Rao",
            "age": 24,
            "last_seen_location": "MG Road",
            "last_seen_date": "2026-07-01",
            "contact_info": "family@example.com",
            "status": "missing",
            "notes": "",
            "photo": TINY_IMAGE,
            "encoding": [0.1, 0.2, 0.3],
            "created_at": now,
            "updated_at": now,
        }
    )
    monkeypatch.setattr(missing_app.face_recognition, "face_distance", lambda known, face: np.array([0.2]))

    response = client.post("/api/match", json={"image": TINY_IMAGE})
    data = response.get_json()

    assert response.status_code == 200
    assert data["matched"] is True
    assert data["person"]["id"] == str(person_id)
    assert data["person"]["name"] == "Asha Rao"
