document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('addPersonForm');
    const statusMessage = document.getElementById('statusMessage');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const name = document.getElementById('name').value;
        const imageFile = document.getElementById('image').files[0];

        if (!name || !imageFile) {
            alert('Please fill in both the name and select an image.');
            return;
        }

        const reader = new FileReader();
        reader.readAsDataURL(imageFile);

        reader.onload = async () => {
            const base64Image = reader.result.split(',')[1];
            
            statusMessage.textContent = 'Submitting...';
            statusMessage.className = ''; 

            try {
                const response = await fetch('/add_person', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, image: base64Image }),
                });

                const result = await response.json();

                if (response.ok) {
                    statusMessage.textContent = result.success;
                    statusMessage.className = 'success'; // Add the .success class
                    form.reset();
                } else {
                    statusMessage.textContent = `Error: ${result.error}`;
                    statusMessage.className = 'error'; // Add the .error class
                }
            } catch (error) {
                statusMessage.textContent = 'A network error occurred. Is the server running?';
                statusMessage.className = 'error';
                console.error('Fetch error:', error);
            }
        };
        reader.onerror = () => {
            statusMessage.textContent = 'Error reading the image file.';
            statusMessage.className = 'error';
        };
    });
});