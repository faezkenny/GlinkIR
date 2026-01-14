# IRPhotolink

A facial recognition and OCR search system for public cloud photo links. Search for people by face, jersey number, or text across up to 5 cloud photo albums.

## Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Activate the virtual environment:
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

## Running the Application

1. Start the FastAPI server:
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Open `frontend/index.html` in your browser or serve it with a simple HTTP server:
```bash
cd frontend
python3 -m http.server 8080
```

Then navigate to `http://localhost:8080`

## Usage

1. Enter up to 5 public cloud photo links (e.g., Google Photos shared album links)
2. Upload a photo for face matching OR enter a jersey number/text to search
3. Click search and wait for results
4. Review and manually filter the results
