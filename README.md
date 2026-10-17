# Emotion AI Studio — Facial Emotion Recognition

A Python-based facial emotion recognition application powered by PyTorch. Emotion AI Studio provides multiple ways to analyze facial expressions through a desktop interface and a web-based frontend.

## Features

- **Image analysis:** Predict emotions from an image.
- **Video analysis:** Analyze facial expressions in video.
- **Live camera:** Perform real-time emotion recognition using a webcam.
- **Model selection:** Load a compatible `.pth` model.
- **Web interface:** Use the frontend with a Python backend.
- **User accounts:** Store account information in a local SQLite database.

## Technologies

- Python
- PyTorch
- Tkinter
- OpenCV
- Pillow
- Flask or the backend framework configured in `backend/server.py`
- HTML, CSS, JavaScript
- SQLite

## Project Structure

```text
facial-emotion-recognition/
├── app.py
├── model.pth
├── model_loader.py
├── requirements.txt
├── start_project.bat
├── backend/
│   ├── README.md
│   └── server.py
└── frontend/
    ├── index.html
    ├── script.js
    └── styles.css
```

## Requirements

- Python installed on your computer
- A compatible `.pth` model file
- Dependencies listed in `requirements.txt`

## Installation

Clone the repository:

```bash
git clone https://github.com/amaliknouamane-cpu/facial-emotion-recognition.git
cd facial-emotion-recognition
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the Desktop Application

```bash
python app.py
```

## Run the Web Application

Open a terminal in the project directory and start the backend:

```bash
python backend/server.py
```

In a second terminal, start the frontend server:

```bash
python -m http.server 5500 -d frontend
```

Open the frontend in your browser:

http://127.0.0.1:5500

Make sure the backend is running and that the frontend is configured to communicate with its correct address.

## Model

The application uses `model.pth` by default. The current model loader identifies the included model as **ReXNet-150**.

To use another checkpoint, select a compatible `.pth` file through the application's model-selection interface, where supported.

The checkpoint must match an architecture supported by `model_loader.py`.

## User Data

User accounts are stored locally in an SQLite database named `users.db`. This database is generated at runtime and is excluded from version control.

## Notes

- Webcam functionality requires a working camera and appropriate permissions.
- Model predictions depend on the checkpoint, preprocessing, and training data.
- Large model files may increase download time.

## Author

**Nouamane**

GitHub: https://github.com/amaliknouamane-cpu
