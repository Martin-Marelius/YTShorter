document.addEventListener('DOMContentLoaded', function () {
    // Load saved form data when the popup is opened
    loadFormData();

    // Event listener for form input changes to auto-save the data
    document.getElementById('dataForm').addEventListener('input', function () {
        saveFormData();
    });

    // Event listener for the "Get Voice Lengths" button
    document.getElementById('getVoiceLengthBtn').addEventListener('click', function () {
        // Get the values for voice1 and voice2
        const voice1 = document.getElementById('voice1').value;
        const voice2 = document.getElementById('voice2').value;

        // Send a POST request to the server to get the lengths
        fetch('http://localhost:5000/getLength', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ voice1: voice1, voice2: voice2 })  // Send data as JSON
        })
        .then(response => response.json())
        .then(data => {
            if (data.total_length !== undefined) {
                
                // Set the voice length preview input with the total length
                document.getElementById('voiceLength').value = data.total_length;
                
                // Save the updated form data
                saveFormData();
            } else {
                alert('Error retrieving voice lengths');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });

    // Form submission to save the data
    document.getElementById('dataForm').addEventListener('submit', function (event) {
        event.preventDefault();
        
        // Get the active tab's URL
        chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
            const currentUrl = tabs[0].url;

            // Collect form data
            const formData = {
                title: document.getElementById('title').value,
                description: document.getElementById('description').value,
                voice1: document.getElementById('voice1').value,
                voice2: document.getElementById('voice2').value,
                captionPosition: document.getElementById('captionPosition').value,
                song: document.getElementById('song').value,
                tags: document.getElementById('tags').value,
                voiceLength: document.getElementById('voiceLength').value,
                volume: document.getElementById('volume').value,  // NEW: Video volume field
                url: currentUrl
            };

            // Send form data to the server
            fetch('http://localhost:5000/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    });
});

// Function to save form data to chrome storage
function saveFormData() {
    const formData = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        voice1: document.getElementById('voice1').value,
        voice2: document.getElementById('voice2').value,
        captionPosition: document.getElementById('captionPosition').value,
        song: document.getElementById('song').value,
        tags: document.getElementById('tags').value,
        voiceLength: document.getElementById('voiceLength').value,
        volume: document.getElementById('volume').value
    };

    chrome.storage.local.set({ formData }, function() {
        console.log('Form data saved automatically');
    });
}

// Function to load saved form data
function loadFormData() {
    chrome.storage.local.get(['formData'], function(result) {
        if (result.formData) {
            const formData = result.formData;

            // Populate the form fields with saved data
            document.getElementById('title').value = formData.title || '';
            document.getElementById('description').value = formData.description || '';
            document.getElementById('voice1').value = formData.voice1 || '';
            document.getElementById('voice2').value = formData.voice2 || '';
            document.getElementById('captionPosition').value = formData.captionPosition || 'bottom';
            document.getElementById('song').value = formData.song || '';
            document.getElementById('tags').value = formData.tags || '';
            document.getElementById('voiceLength').value = formData.voiceLength || '';
            document.getElementById('volume').value = formData.volume || '';
        }
    });
}
