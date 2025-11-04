document.addEventListener('DOMContentLoaded', function () {
    // --- Element Selection ---
    const fileInput = document.getElementById('file-input');
    const imagePreview = document.getElementById('image-preview');
    const originalBox = document.getElementById('original-box');
    const processedBox = document.getElementById('processed-box');
    const cartoonImage = document.getElementById('cartoon-image');
    const uploadForm = document.getElementById('upload-form');
    const loader = document.getElementById('loader');
    const downloadBtn = document.getElementById('download-btn');
    const uploadArea = document.getElementById('upload-area');
    const uploadLabel = document.querySelector('.upload-label');
    const uploadSubtext = document.querySelector('.upload-subtext');
    const submitBtn = document.querySelector("button[type='submit']");

    // Utility animation functions
    function animateEl(el, animation) {
        el.style.animation = animation;
        el.addEventListener("animationend", () => {
            el.style.animation = "";
        }, { once: true });
    }

    // --- Entire upload box clickable ---
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // --- Preview on file select ---
    fileInput.addEventListener('change', function () {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                imagePreview.src = e.target.result;
                originalBox.style.display = 'block';
                
                // Reset processing box
                processedBox.style.display = 'none';
                cartoonImage.src = "#";
                downloadBtn.style.display = 'none';

                uploadLabel.innerHTML = `Selected file: <strong>${file.name}</strong>`;
                uploadSubtext.textContent = "Ready to Cartoonify!";

                // Animation: pulse when file chosen
                animateEl(uploadArea, "pulseSelect 0.4s ease");
                // Fade-in preview
                animateEl(imagePreview, "fadeInScale 0.5s ease");
            };
            reader.readAsDataURL(file);
        }
    });

    // --- Form Submit / Upload ---
    uploadForm.addEventListener('submit', function (e) {
        e.preventDefault();

        if (!fileInput.files.length) {
            alert('Please select an image file first.');
            return;
        }

        processedBox.style.display = 'block';
        loader.style.display = 'block';
        cartoonImage.style.display = 'none';
        downloadBtn.style.display = 'none';

        // Button animation loading
        submitBtn.disabled = true;
        submitBtn.classList.add("btn-loading");
        submitBtn.innerHTML = `<span class="spinner"></span> Processing...`;

        const formData = new FormData(this);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                loader.style.display = 'none';
                submitBtn.disabled = false;
                submitBtn.classList.remove("btn-loading");
                submitBtn.innerHTML = `Cartoonify! ✨`;
            } else {
                cartoonImage.src = data.cartoon_image_url + '?t=' + Date.now();
                downloadBtn.href = data.cartoon_image_url;

                cartoonImage.onload = () => {
                    loader.style.display = 'none';
                    cartoonImage.style.display = 'block';
                    downloadBtn.style.display = 'block';

                    // Result animation
                    animateEl(cartoonImage, "popIn 0.5s ease");
                    animateEl(downloadBtn, "glowIn 0.6s ease");

                    // Reset button
                    submitBtn.disabled = false;
                    submitBtn.classList.remove("btn-loading");
                    submitBtn.innerHTML = `Done ✅`;
                    
                    setTimeout(() => {
                        submitBtn.innerHTML = `Cartoonify! ✨`;
                    }, 1200);
                };
            }
        })
        .catch(err => {
            alert('Unexpected error. Try again.');
            loader.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.classList.remove("btn-loading");
            submitBtn.innerHTML = `Cartoonify! ✨`;
        });
    });

    // --- Drag & Drop ---
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change'));
        }
    });
});

