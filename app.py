import base64
import io
import face_recognition
import numpy as np
# Add render_template import
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from PIL import Image

# --- Flask App Initialization ---
app = Flask(__name__)

# --- MongoDB Connection ---
# ... (your connection string remains here)
MONGO_URI = "mongodb+srv://ysarjun1234:ysarjun1234@cluster0.pidkbb4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
client = MongoClient(MONGO_URI)
db = client['missing_person_db'] # Database name
persons_collection = db['persons'] # Collection name

print("Successfully connected to MongoDB.")

# --- Add this new route to serve the HTML page ---
@app.route('/')
def index():
    """
    Serves the main HTML page for the web interface.
    """
    return render_template('index.html')


# --- API Endpoints ---

@app.route('/add_person', methods=['POST'])
def add_person():
    """
    API endpoint to add a new missing person to the database.
    Expects a JSON payload with 'name' and 'image' (base64 encoded string).
    """
    data = request.get_json()
    if not data or 'name' not in data or 'image' not in data:
        return jsonify({'error': 'Missing name or image in request'}), 400

    name = data['name']
    base64_image = data['image']

    try:
        # Decode the base64 image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        # Convert PIL image to numpy array for face_recognition
        image_np = np.array(image)

        # Find face encodings. We assume one face per image.
        face_encodings = face_recognition.face_encodings(image_np)

        if len(face_encodings) == 0:
            return jsonify({'error': 'No face found in the provided image'}), 400
        
        # Take the first face encoding found
        face_encoding = face_encodings[0]

        # Store in MongoDB. Note: Encodings are numpy arrays, so convert to list.
        person_doc = {
            'name': name,
            'encoding': face_encoding.tolist() # Convert numpy array to list for MongoDB
        }
        persons_collection.insert_one(person_doc)

        return jsonify({'success': f'Person {name} added successfully'}), 201

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/get_known_faces', methods=['GET'])
def get_known_faces():
    """
    API endpoint to retrieve all known faces from the database.
    This will be used by the detector script.
    """
    try:
        persons = list(persons_collection.find({}, {'_id': 0})) # Find all, exclude the _id field
        
        known_face_encodings = [person['encoding'] for person in persons]
        known_face_names = [person['name'] for person in persons]

        return jsonify({
            'known_face_encodings': known_face_encodings,
            'known_face_names': known_face_names
        })

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # Use 0.0.0.0 to make the app accessible on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)