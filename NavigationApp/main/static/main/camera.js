(function () {
    const video = document.getElementById('video-feed');
    const startCameraBtn = document.getElementById('start-camera');
    const analyzeBtn = document.getElementById('analyze-btn');
    const loading = document.getElementById('loading');
    const errorDisplay = document.getElementById('error-display');
    const errorMessage = document.getElementById('error-message');
    const locationDisplay = document.getElementById('location-display');
    const locationName = document.getElementById('location-name');
    const instructionDisplay = document.getElementById('instruction-display');
    const confidenceDisplay = document.getElementById('confidence-display');
    const safeMode = document.getElementById('safe-mode');
    const promptBox = document.getElementById('prompt-box');
    const promptTitle = document.getElementById('prompt-title');
    const promptInstruction = document.getElementById('prompt-instruction');
    const promptConfidence = document.getElementById('prompt-confidence');

    let stream = null;

    function showError(message) {
        errorMessage.textContent = message;
        errorDisplay.classList.add('active');
        setTimeout(() => {
            errorDisplay.classList.remove('active');
        }, 5000);
    }

    function hideError() {
        errorDisplay.classList.remove('active');
    }

    async function startCamera() {
        try {
            hideError();
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            video.srcObject = stream;
            startCameraBtn.textContent = '⏹️ Zastavit kameru';
            startCameraBtn.onclick = stopCamera;
            analyzeBtn.disabled = false;
        } catch (err) {
            console.error('Error accessing camera:', err);
            showError('Nepodařilo se přistoupit k kameře. Zkontrolujte povolení.');
        }
    }

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            video.srcObject = null;
            startCameraBtn.textContent = '📷 Spustit kameru';
            startCameraBtn.onclick = startCamera;
            analyzeBtn.disabled = true;
        }
    }

    function captureImage() {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        return canvas.toDataURL('image/jpeg', 0.8);
    }

    async function analyzeImage() {
        try {
            hideError();
            loading.classList.add('active');
            analyzeBtn.disabled = true;

            const imageData = captureImage();
            
            // Convert base64 to blob
            const response = await fetch(imageData);
            const blob = await response.blob();
            
            // Create form data
            const formData = new FormData();
            formData.append('image', blob, 'camera_capture.jpg');

            // Send to API
            const apiResponse = await fetch('/api/classify/', {
                method: 'POST',
                body: formData
            });

            if (!apiResponse.ok) {
                const errorData = await apiResponse.json();
                throw new Error(errorData.error || 'Chyba při analýze');
            }

            const result = await apiResponse.json();
            
            // Update small badge
            locationDisplay.style.display = 'inline-block';
            locationName.textContent = result.location;

            // Normalize the location_key (remove diacritics) to match CSS classes
            function normalizeKey(s) {
                if (!s) return 'unknown';
                return s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
            }
            const normKey = normalizeKey(result.location_key || 'unknown');

            // Update large prompt box (visible, colored per-location)
            if (normKey && normKey !== 'unknown') {
                promptBox.style.display = 'block';
                promptTitle.textContent = result.location;
                promptInstruction.textContent = result.instruction;
                promptConfidence.textContent = `Jistota: ${(result.confidence * 100).toFixed(1)}%`;
                // reset class and apply per-location class
                promptBox.className = 'prompt-box';
                promptBox.classList.add('prompt-' + normKey);
            } else {
                promptBox.style.display = 'none';
            }

            // Also update the small instruction display for accessibility
            instructionDisplay.textContent = result.instruction;

            // Show safe mode if outside
            if (normKey === 'venek') {
                safeMode.classList.add('active');
            } else {
                safeMode.classList.remove('active');
            }

        } catch (err) {
            console.error('Error analyzing image:', err);
            showError(err.message || 'Chyba při analýze obrázku');
        } finally {
            loading.classList.remove('active');
            analyzeBtn.disabled = false;
        }
    }

    // Event listeners
    startCameraBtn.onclick = startCamera;
    analyzeBtn.onclick = analyzeImage;

    // Auto-analyze every 3 seconds when camera is running
    let autoAnalyzeInterval = null;
    
    startCameraBtn.addEventListener('click', function() {
        if (stream && !autoAnalyzeInterval) {
            autoAnalyzeInterval = setInterval(analyzeImage, 3000);
        }
    });

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            video.srcObject = null;
            startCameraBtn.textContent = '📷 Spustit kameru';
            startCameraBtn.onclick = startCamera;
            analyzeBtn.disabled = true;
            
            if (autoAnalyzeInterval) {
                clearInterval(autoAnalyzeInterval);
                autoAnalyzeInterval = null;
            }
        }
    }

    // Check if camera is available on load
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showError('Váš prohlížeč nepodporuje přístup k kameře');
        startCameraBtn.disabled = true;
    }
})();
