// API endpoint (adjust if your backend runs on a different port)
const API_URL = 'http://localhost:8000';

// DOM elements
const searchForm = document.getElementById('searchForm');
const folderUrlInput = document.getElementById('folderUrlInput');
const faceImageInput = document.getElementById('faceImageInput');
const searchTextInput = document.getElementById('searchTextInput');
const searchButton = document.getElementById('searchButton');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const resultsContainer = document.getElementById('resultsContainer');
const resultsGrid = document.getElementById('resultsGrid');
const resultsSummary = document.getElementById('resultsSummary');
const faceImagePreview = document.getElementById('faceImagePreview');
const previewImg = document.getElementById('previewImg');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const loginStatus = document.getElementById('loginStatus');
const loginStatusText = document.getElementById('loginStatusText');
const googleLoginBtn = document.getElementById('googleLoginBtn');
const microsoftLoginBtn = document.getElementById('microsoftLoginBtn');
const smartLoginBtn = document.getElementById('smartLoginBtn');
const smartLoginText = document.getElementById('smartLoginText');
const providerHint = document.getElementById('providerHint');

let currentJobId = null;
let jobPollInterval = null;

// Detect provider from URL
function detectProvider(url) {
    if (!url || typeof url !== 'string') {
        return 'unknown';
    }
    
    const lowerUrl = url.toLowerCase().trim();
    
    // Google Drive patterns
    if (lowerUrl.includes('drive.google.com') || 
        lowerUrl.includes('docs.google.com') ||
        lowerUrl.includes('photos.google.com') ||
        lowerUrl.includes('photos.app.goo.gl')) {
        return 'google_drive';
    }
    
    // OneDrive patterns
    if (lowerUrl.includes('onedrive.live.com') || 
        lowerUrl.includes('1drv.ms') || 
        lowerUrl.includes('sharepoint.com') ||
        lowerUrl.includes('office365.com') ||
        lowerUrl.includes('microsoft.com/share')) {
        return 'onedrive';
    }
    
    return 'unknown';
}

// Update provider hint and smart login button
async function updateProviderUI(url) {
    // Ensure DOM elements exist
    if (!providerHint || !smartLoginBtn || !googleLoginBtn || !microsoftLoginBtn || !smartLoginText) {
        console.error('DOM elements not found');
        return;
    }
    
    if (!url || url.trim() === '') {
        providerHint.textContent = 'Enter a Google Drive or OneDrive folder link';
        providerHint.className = 'mt-1 text-sm text-gray-500';
        smartLoginBtn.classList.add('hidden');
        googleLoginBtn.classList.remove('hidden');
        microsoftLoginBtn.classList.remove('hidden');
        return;
    }
    
    const provider = detectProvider(url);
    console.log('Detected provider:', provider, 'for URL:', url);
    
    let authStatus = { loggedIn: false, google: false, microsoft: false };
    try {
        const response = await fetch(`${API_URL}/auth/me`, { 
            credentials: 'include',
            mode: 'cors'
        });
        if (response.ok) {
            authStatus = await response.json();
        }
    } catch (error) {
        // Silently fail - user might not be logged in yet
        console.debug('Auth check failed (this is OK if not logged in):', error.message);
        authStatus = { loggedIn: false, google: false, microsoft: false };
    }
    
    if (provider === 'google_drive') {
        providerHint.textContent = '✓ Google Drive folder detected';
        providerHint.className = 'mt-1 text-sm text-green-600 font-medium';
        
        if (authStatus.google) {
            providerHint.textContent = '✓ Google Drive folder detected - Already logged in';
            smartLoginBtn.classList.add('hidden');
            googleLoginBtn.classList.remove('hidden');
            microsoftLoginBtn.classList.remove('hidden');
        } else {
            // Show smart login button for Google
            smartLoginBtn.classList.remove('hidden');
            googleLoginBtn.classList.add('hidden');
            microsoftLoginBtn.classList.add('hidden');
            smartLoginText.textContent = '🔵 Login with Google';
            smartLoginBtn.onclick = () => {
                window.location.href = `${API_URL}/auth/google/start`;
            };
        }
    } else if (provider === 'onedrive') {
        providerHint.textContent = '✓ OneDrive folder detected';
        providerHint.className = 'mt-1 text-sm text-green-600 font-medium';
        
        if (authStatus.microsoft) {
            providerHint.textContent = '✓ OneDrive folder detected - Already logged in';
            smartLoginBtn.classList.add('hidden');
            googleLoginBtn.classList.remove('hidden');
            microsoftLoginBtn.classList.remove('hidden');
        } else {
            // Show smart login button for Microsoft
            smartLoginBtn.classList.remove('hidden');
            googleLoginBtn.classList.add('hidden');
            microsoftLoginBtn.classList.add('hidden');
            smartLoginText.textContent = '🔷 Login with Microsoft';
            smartLoginBtn.onclick = () => {
                window.location.href = `${API_URL}/auth/microsoft/start`;
            };
        }
    } else {
        providerHint.textContent = `⚠️ Unknown provider. Please use Google Drive or OneDrive link. (Detected: ${url.substring(0, 50)}...)`;
        providerHint.className = 'mt-1 text-sm text-orange-600';
        smartLoginBtn.classList.add('hidden');
        googleLoginBtn.classList.remove('hidden');
        microsoftLoginBtn.classList.remove('hidden');
    }
}

// Add event listener with debouncing
let updateTimeout = null;
folderUrlInput.addEventListener('input', (e) => {
    clearTimeout(updateTimeout);
    updateTimeout = setTimeout(() => {
        updateProviderUI(e.target.value.trim());
    }, 300); // Debounce for 300ms
});

// Also trigger on paste
folderUrlInput.addEventListener('paste', (e) => {
    setTimeout(() => {
        updateProviderUI(folderUrlInput.value.trim());
    }, 100);
});

// Login buttons
googleLoginBtn.addEventListener('click', () => {
    window.location.href = `${API_URL}/auth/google/start`;
});

microsoftLoginBtn.addEventListener('click', () => {
    window.location.href = `${API_URL}/auth/microsoft/start`;
});

// Check auth status
async function checkAuthStatus() {
    if (!loginStatus || !loginStatusText) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            credentials: 'include',
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        loginStatus.classList.remove('hidden');
        
        if (data.loggedIn) {
            const providers = [];
            if (data.google) providers.push('🔵 Google');
            if (data.microsoft) providers.push('🔷 Microsoft');
            loginStatusText.textContent = `✓ Logged in with: ${providers.join(', ')}`;
            loginStatus.className = 'bg-green-50 border border-green-200 rounded-lg shadow-md p-4 mb-6';
        } else {
            loginStatusText.textContent = 'Not logged in. Enter a folder link above to see which provider to login with.';
            loginStatus.className = 'bg-yellow-50 border border-yellow-200 rounded-lg shadow-md p-4 mb-6';
        }
        
        // Update provider UI if URL is already entered
        const url = folderUrlInput ? folderUrlInput.value.trim() : '';
        if (url) {
            updateProviderUI(url);
        }
    } catch (error) {
        // Don't show error if backend is not available - user might be setting up
        console.debug('Auth check failed (backend may not be running):', error.message);
        loginStatus.classList.remove('hidden');
        loginStatusText.textContent = 'Backend not connected. Make sure the server is running on port 8000.';
        loginStatus.className = 'bg-gray-50 border border-gray-200 rounded-lg shadow-md p-4 mb-6';
    }
}

// Show face image preview
faceImageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            previewImg.src = event.target.result;
            faceImagePreview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    } else {
        faceImagePreview.classList.add('hidden');
    }
});

// Handle form submission
searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Validate inputs
    const folderUrl = folderUrlInput.value.trim();
    const faceImage = faceImageInput.files[0];
    const searchText = searchTextInput.value.trim();
    
    if (!folderUrl) {
        showError('Please enter a folder link');
        return;
    }
    
    const provider = detectProvider(folderUrl);
    if (provider === 'unknown') {
        showError('Please enter a valid Google Drive or OneDrive folder link');
        return;
    }
    
    if (!faceImage && !searchText) {
        showError('Please provide either a face image or search text');
        return;
    }
    
    // Check auth
    const authStatus = await fetch(`${API_URL}/auth/me`, { credentials: 'include' }).then(r => r.json());
    if (provider === 'google_drive' && !authStatus.google) {
        showError('Please login with Google first');
        return;
    }
    if (provider === 'onedrive' && !authStatus.microsoft) {
        showError('Please login with Microsoft first');
        return;
    }
    
    // Show loading state
    setLoading(true);
    hideError();
    hideResults();
    
    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('folder_url', folderUrl);
        
        if (faceImage) {
            formData.append('face_image', faceImage);
        }
        
        if (searchText) {
            formData.append('search_text', searchText);
        }
        
        updateProgress(5, 'Starting job...');
        
        // Start job
        const response = await fetch(`${API_URL}/jobs/start`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        const jobData = await response.json();
        
        if (!response.ok) {
            throw new Error(jobData.detail || 'Failed to start job');
        }
        
        currentJobId = jobData.jobId;
        
        // Start polling
        startJobPolling(currentJobId);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred while starting the search.');
        setLoading(false);
    }
});

function startJobPolling(jobId) {
    if (jobPollInterval) {
        clearInterval(jobPollInterval);
    }
    
    jobPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/jobs/${jobId}/status`, {
                credentials: 'include'
            });
            const job = await response.json();
            
            // Update progress
            if (job.total > 0) {
                const percentage = (job.processed / job.total) * 100;
                updateProgress(percentage, `Processed ${job.processed} / ${job.total} images`);
            } else if (job.phase === 'listing') {
                updateProgress(10, 'Listing files...');
            } else if (job.phase === 'queued') {
                updateProgress(5, 'Job queued...');
            }
            
            // Check if done
            if (job.phase === 'done' || job.phase === 'error') {
                clearInterval(jobPollInterval);
                jobPollInterval = null;
                
                if (job.phase === 'error') {
                    showError(job.error || 'Job failed');
                    setLoading(false);
                } else {
                    updateProgress(100, `Complete! Found ${job.matches.length} matches`);
                    displayJobResults(job);
                    setTimeout(() => {
                        setLoading(false);
                    }, 1000);
                }
            }
        } catch (error) {
            console.error('Error polling job:', error);
            clearInterval(jobPollInterval);
            jobPollInterval = null;
            showError('Error checking job status');
            setLoading(false);
        }
    }, 1000); // Poll every second
}

function displayJobResults(job) {
    const matches = job.matches || [];
    const total = job.total || 0;
    
    // Update summary
    resultsSummary.innerHTML = `
        <div>Found <strong>${matches.length}</strong> matching image(s) out of <strong>${total}</strong> total images searched.</div>
    `;
    
    // Clear previous results
    resultsGrid.innerHTML = '';
    
    if (matches.length === 0) {
        resultsGrid.innerHTML = '<div class="text-center text-gray-500 py-8">No matches found.</div>';
        resultsContainer.classList.remove('hidden');
        return;
    }
    
    // Create image grid
    const imageGrid = document.createElement('div');
    imageGrid.className = 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4';
    
    matches.forEach(match => {
        const imageCard = document.createElement('div');
        imageCard.className = 'relative group';
        
        const img = document.createElement('img');
        // Use thumbnail if available, otherwise use download link
        img.src = match.thumbnailLink || match.webContentLink || match.downloadUrl || match.webUrl || '';
        img.alt = match.name || 'Matching photo';
        img.className = 'w-full h-48 object-cover rounded-md shadow-sm hover:shadow-lg transition-shadow cursor-pointer';
        img.loading = 'lazy';
        
        // Open full image on click
        img.addEventListener('click', () => {
            const url = match.webContentLink || match.downloadUrl || match.webUrl;
            if (url) {
                window.open(url, '_blank');
            }
        });
        
        // Add name overlay
        if (match.name) {
            const nameOverlay = document.createElement('div');
            nameOverlay.className = 'absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-2 rounded-b-md';
            nameOverlay.textContent = match.name;
            imageCard.appendChild(nameOverlay);
        }
        
        imageCard.appendChild(img);
        imageGrid.appendChild(imageCard);
    });
    
    resultsGrid.appendChild(imageGrid);
    resultsContainer.classList.remove('hidden');
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setLoading(isLoading) {
    if (isLoading) {
        loadingIndicator.classList.remove('hidden');
        searchButton.disabled = true;
        searchButton.classList.add('opacity-50', 'cursor-not-allowed');
        updateProgress(0, 'Starting...');
    } else {
        loadingIndicator.classList.add('hidden');
        searchButton.disabled = false;
        searchButton.classList.remove('opacity-50', 'cursor-not-allowed');
        updateProgress(0, '');
        if (jobPollInterval) {
            clearInterval(jobPollInterval);
            jobPollInterval = null;
        }
    }
}

function updateProgress(percentage, message) {
    if (progressBar && progressText) {
        progressBar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        if (message) {
            progressText.textContent = `${Math.round(percentage)}% - ${message}`;
        } else {
            progressText.textContent = `${Math.round(percentage)}%`;
        }
    }
}

function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function hideResults() {
    resultsContainer.classList.add('hidden');
}

function truncateUrl(url, maxLength = 60) {
    if (url.length <= maxLength) {
        return url;
    }
    return url.substring(0, maxLength) + '...';
}

// Initialize on load
window.addEventListener('load', async () => {
    // Check API health
    try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) {
            showError('Backend API is not available. Please make sure the server is running on port 8000.');
        }
    } catch (error) {
        showError('Cannot connect to backend API. Please make sure the server is running on port 8000.');
    }
    
    // Check auth status
    await checkAuthStatus();
    
    // Check if URL is already in input field
    if (folderUrlInput && folderUrlInput.value.trim()) {
        updateProviderUI(folderUrlInput.value.trim());
    }
});
