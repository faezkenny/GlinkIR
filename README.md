# IRPhotolink

A facial recognition and OCR search system for cloud photo folders. Search for people by face, jersey number, or text across Google Drive and OneDrive folders.

## Features

- **Google Drive** folder support via OAuth + Drive API
- **OneDrive** folder support via OAuth + Graph API
- **Facial recognition** with high recall (80%+ accuracy)
- **OCR text search** for jersey numbers and text
- **Real-time progress** tracking with image counts
- **Fast backend processing** (no browser downloads)

## Setup

### 1. Backend Setup

Navigate to the backend directory:
```bash
cd backend
```

Activate the virtual environment:
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Install Playwright browsers (for legacy scraping support):
```bash
playwright install
```

### 2. OAuth Configuration

#### Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Drive API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Choose **Web application**
6. Add **Authorized redirect URI**: `http://localhost:8000/auth/google/callback`
7. Copy **Client ID** and **Client Secret**

#### Microsoft OneDrive Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Set redirect URI: `http://localhost:8000/auth/microsoft/callback`
5. Go to **Certificates & secrets** → **New client secret**
6. Copy **Application (client) ID** and **Client secret**
7. Go to **API permissions** → Add **Microsoft Graph** → **Files.Read** permission

### 3. Environment Variables

Create a `.env` file in the `backend` directory (or set environment variables):

```bash
FRONTEND_ORIGIN=http://localhost:8080
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback
```

Or export them:
```bash
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"
# ... etc
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

1. **Login**: Click "Login with Google" or "Login with Microsoft" (depending on your folder provider)
2. **Enter folder link**: Paste a Google Drive or OneDrive folder link
3. **Upload face image** (optional) OR enter **search text** (jersey number, name, etc.)
4. **Click Search**: The system will:
   - List all images in the folder via API
   - Download and process each image
   - Show real-time progress: "Processed X / Y images"
   - Display matches as they're found
5. **Review results**: Click on matched images to view full size

## API Endpoints

- `GET /auth/google/start` - Start Google OAuth
- `GET /auth/microsoft/start` - Start Microsoft OAuth
- `GET /auth/me` - Check authentication status
- `POST /jobs/start` - Start a search job
- `GET /jobs/{jobId}/status` - Get job progress
- `POST /search` - Legacy scraping endpoint (still supported)

## Notes

- **High recall mode**: Configured to find 80%+ of matches (may include some false positives)
- **Caching**: Face encodings and OCR results are cached to speed up repeated searches
- **Progress tracking**: Real-time progress shows actual image counts from API
- **Production**: Replace in-memory session/job storage with Redis or database
