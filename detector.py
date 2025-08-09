import cv2
import numpy as np
import requests # New import for making API requests
import face_recognition
# --- New Function to Fetch Data from API ---
def fetch_known_faces_from_api():
    """
    Fetches known face encodings and names from our Flask API.
    """
    # The URL of our Flask API endpoint
    API_URL = "http://127.0.0.1:5000/get_known_faces"
    
    known_face_encodings = []
    known_face_names = []

    print("Fetching known faces from the API...")
    try:
        response = requests.get(API_URL)
        # Raise an exception if the request was unsuccessful
        response.raise_for_status() 
        
        data = response.json()
        
        # The encodings from JSON are lists, so we convert them back to numpy arrays
        known_face_encodings = [np.array(encoding) for encoding in data['known_face_encodings']]
        known_face_names = data['known_face_names']
        
        print(f"Successfully loaded {len(known_face_names)} known faces.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        # Return empty lists if the API is down or there's an error
        return [], []
        
    return known_face_encodings, known_face_names

# --- Video Detection Logic (This part is mostly unchanged) ---
def run_detection(known_face_encodings, known_face_names):
    """
    Captures video and performs real-time face recognition.
    """
    # Get a reference to webcam #0 (the default one)
    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("Error: Could not open video stream.")
        return

    print("\nStarting video stream and detection... Press 'q' to quit.")
    
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        # For performance, we can process every other frame
        # Or resize the frame to be smaller
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

        # Find all faces in the current frame
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
                    print(f"!!! MATCH FOUND: {name} !!!")

            # Scale back up face locations since the frame we detected in was scaled
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box and label
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        cv2.imshow('Missing Person Detector', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    print("Video stream stopped.")


# --- Main Execution ---
if __name__ == '__main__':
    # Fetch the data from our API instead of a local folder
    known_encodings, known_names = fetch_known_faces_from_api()

    if known_names:
        run_detection(known_encodings, known_names)
    else:
        print("Could not load any known faces from the API. Please add a person via the web interface and ensure the Flask server is running.")