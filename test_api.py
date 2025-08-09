import requests
import base64
import json

# The image we want to upload (the one from Step 1)
IMAGE_PATH = 'known_people/person_1.jpg' 
PERSON_NAME = 'Person One' # The name we want to associate with the image

# Flask API URLs
ADD_URL = 'http://127.0.0.1:5000/add_person'
GET_URL = 'http://127.0.0.1:5000/get_known_faces'

# 1. Test the /add_person endpoint
print(f"--- Adding '{PERSON_NAME}' to the database ---")
try:
    # Read the image file and encode it in base64
    with open(IMAGE_PATH, 'rb') as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

    # Prepare the JSON payload
    payload = {'name': PERSON_NAME, 'image': encoded_string}

    # Send the POST request
    response = requests.post(ADD_URL, json=payload)
    response.raise_for_status() # Raise an exception for bad status codes

    print("Response from /add_person:")
    print(json.dumps(response.json(), indent=2))

except requests.exceptions.RequestException as e:
    print(f"An error occurred while calling /add_person: {e}")
    if e.response:
        print("Error Response Body:", e.response.text)


# 2. Test the /get_known_faces endpoint
print("\n--- Retrieving all known faces from the database ---")
try:
    response = requests.get(GET_URL)
    response.raise_for_status()
    
    data = response.json()
    print("Response from /get_known_faces:")
    print(f"Found {len(data.get('known_face_names', []))} known people.")
    # print(json.dumps(data, indent=2)) # Uncomment to see the full data

except requests.exceptions.RequestException as e:
    print(f"An error occurred while calling /get_known_faces: {e}")