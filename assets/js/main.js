const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const scanButton = document.getElementById('scanButton');
const modal = document.getElementById('resultModal');

imageInput.addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
            scanButton.style.display = 'block';
        }
        reader.readAsDataURL(file);
    }
});

async function scanBusinessCard() {
    try {
        const formData = new FormData();
        formData.append('image', imageInput.files[0]);
        formData.append('query', JSON.stringify({
            "query": "I am providing business cards, What I want is to get json output of some keys like name, Designation, Company name, Mob. Number, e-mail id, address,. I want it all to be in a json output in a structured manner"
        }));

        const response = await fetch('http://4.240.46.255:1337/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        displayResults(data);
    } catch (error) {
        alert('Error processing the business card. Please try again.');
        console.error(error);
    }
}

function displayResults(data) {
    const resultContent = document.getElementById('resultContent');
    resultContent.innerHTML = '';

    for (const [key, value] of Object.entries(data)) {
        const div = document.createElement('div');
        div.className = 'info-item';
        div.innerHTML = `<strong>${key.charAt(0).toUpperCase() + key.slice(1)}:</strong> ${value}`;
        resultContent.appendChild(div);
    }

    modal.style.display = 'block';
}

function closeModal() {
    modal.style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}