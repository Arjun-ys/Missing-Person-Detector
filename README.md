# Missing Person Detector

An AI-driven application to identify missing persons in real-time using facial recognition. This project uses Python, OpenCV, Flask, and MongoDB to create a complete full-stack detection system.

![Project Demo GIF](link_to_your_demo_gif_here)

---

## ## Features

* **Real-Time Detection:** Uses a live webcam feed to perform facial recognition.
* **Web Interface:** A user-friendly web page to add and manage missing persons' data.
* **RESTful API:** A Flask backend provides API endpoints for data storage and retrieval.
* **Database Integration:** Uses MongoDB to persistently store face encodings and names.

---

## ## Tech Stack

* **Backend:** Python, Flask
* **AI/Computer Vision:** OpenCV, face_recognition, dlib
* **Database:** MongoDB
* **Frontend:** HTML, CSS, JavaScript

---

## ## Setup and Usage

Follow these steps to run the project locally.

### ### Prerequisites

* Python 3.8+
* MongoDB Atlas account
* C++ Build Tools & CMake (for Windows `dlib` installation)

### ### Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/your-username/missing-person-detector.git](https://github.com/your-username/missing-person-detector.git)
    cd missing-person-detector
    ```
2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You'll need to create a `requirements.txt` file for this to work. See instructions below.)*

### ### How to Run

1.  **Start the Backend Server:**
    ```bash
    python app.py
    ```
2.  **Add a Person:**
    Open a web browser and go to `http://127.0.0.1:5000`. Use the form to add a person's name and photo.
3.  **Run the Detector:**
    Open a second terminal and run:
    ```bash
    python detector.py
    ```