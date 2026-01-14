// API endpoint (adjust if your backend runs on a different port)
const API_URL = 'http://localhost:8000';

// DOM elements
const searchForm = document.getElementById('searchForm');
const linksInput = document.getElementById('linksInput');
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
    const links = linksInput.value.trim();
    const faceImage = faceImageInput.files[0];
    const searchText = searchTextInput.value.trim();
    
    if (!links) {
        showError('Please enter at least one photo album link');
        return;
    }
    
    if (!faceImage && !searchText) {
        showError('Please provide either a face image or search text');
        return;
    }
    
    // Show loading state
    setLoading(true);
    hideError();
    hideResults();
    
    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('links', links);
        
        if (faceImage) {
            formData.append('face_image', faceImage);
        }
        
        if (searchText) {
            formData.append('search_text', searchText);
        }
        
        // Update progress
        updateProgress(5, 'Preparing request...');
        
        // Make API request
        const response = await fetch(`${API_URL}/search`, {
            method: 'POST',
            body: formData
        });
        
        updateProgress(15, 'Scraping photo links...');
        
        // Track progress with better estimation
        let currentProgress = 15;
        let progressStep = 0;
        
        // Simulate progress while waiting for response
        // We'll update based on estimated time
        const progressInterval = setInterval(() => {
            currentProgress = parseInt(progressBar.style.width) || 15;
            if (currentProgress < 95) {
                // Gradually increase progress
                progressStep += 0.5;
                const newProgress = Math.min(95, 15 + progressStep);
                updateProgress(newProgress, 'Processing images...');
            }
        }, 500);
        
        const data = await response.json();
        
        clearInterval(progressInterval);
        
        // Show final progress with image count
        const totalImages = data.total_images_searched || 0;
        const imagesByAlbum = data.images_by_album || {};
        let albumInfo = '';
        if (Object.keys(imagesByAlbum).length > 0) {
            const albumCounts = Object.entries(imagesByAlbum)
                .map(([url, count]) => `${truncateUrl(url, 30)}: ${count} images`)
                .join(', ');
            albumInfo = ` (${albumCounts})`;
        }
        
        updateProgress(100, `Complete! Searched ${totalImages} images${albumInfo}`);
        
        if (!response.ok) {
            throw new Error(data.detail || 'Search failed');
        }
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred while searching. Please try again.');
    } finally {
        setTimeout(() => {
            setLoading(false);
        }, 500);
    }
});

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

function displayResults(data) {
    const results = data.results || {};
    const totalMatches = data.total_matches || 0;
    const totalSearched = data.total_images_searched || 0;
    const imagesByAlbum = data.images_by_album || {};
    
    // Update summary with detailed info
    let summaryText = `Found ${totalMatches} matching image(s) out of ${totalSearched} total images searched.`;
    
    if (Object.keys(imagesByAlbum).length > 0) {
        summaryText += '\n\nImages found per link:';
        for (const [url, count] of Object.entries(imagesByAlbum)) {
            summaryText += `\n• ${truncateUrl(url, 50)}: ${count} images`;
        }
    }
    
    resultsSummary.innerHTML = summaryText.split('\n').map(line => {
        if (line.startsWith('•')) {
            return `<div class="text-sm mt-1">${line}</div>`;
        }
        return `<div>${line}</div>`;
    }).join('');
    
    // Clear previous results
    resultsGrid.innerHTML = '';
    
    // Display results by album
    for (const [albumUrl, imageUrls] of Object.entries(results)) {
        if (imageUrls.length === 0) {
            continue;
        }
        
        const albumSection = document.createElement('div');
        albumSection.className = 'bg-white rounded-lg shadow-md p-6';
        
        const albumHeader = document.createElement('div');
        albumHeader.className = 'mb-4';
        
        const albumTitle = document.createElement('h3');
        albumTitle.className = 'text-xl font-semibold text-gray-900 mb-2';
        albumTitle.textContent = `Album: ${truncateUrl(albumUrl)}`;
        albumHeader.appendChild(albumTitle);
        
        const matchCount = document.createElement('p');
        matchCount.className = 'text-sm text-gray-600';
        matchCount.textContent = `${imageUrls.length} matching image(s)`;
        albumHeader.appendChild(matchCount);
        
        albumSection.appendChild(albumHeader);
        
        // Create image grid
        const imageGrid = document.createElement('div');
        imageGrid.className = 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4';
        
        imageUrls.forEach(imageUrl => {
            const imageCard = document.createElement('div');
            imageCard.className = 'relative group';
            
            const img = document.createElement('img');
            img.src = imageUrl;
            img.alt = 'Matching photo';
            img.className = 'w-full h-48 object-cover rounded-md shadow-sm hover:shadow-lg transition-shadow cursor-pointer';
            img.loading = 'lazy';
            
            // Open full image on click
            img.addEventListener('click', () => {
                window.open(imageUrl, '_blank');
            });
            
            imageCard.appendChild(img);
            imageGrid.appendChild(imageCard);
        });
        
        albumSection.appendChild(imageGrid);
        resultsGrid.appendChild(albumSection);
    }
    
    // Show results container
    resultsContainer.classList.remove('hidden');
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function truncateUrl(url, maxLength = 60) {
    if (url.length <= maxLength) {
        return url;
    }
    return url.substring(0, maxLength) + '...';
}

// Check API health on load
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) {
            showError('Backend API is not available. Please make sure the server is running on port 8000.');
        }
    } catch (error) {
        showError('Cannot connect to backend API. Please make sure the server is running on port 8000.');
    }
});
