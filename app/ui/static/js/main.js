// Main JavaScript functionality

// Notification system
const notifications = {
    show(message, type = 'info', duration = 3000) {
        const container = document.getElementById('notifications');
        const notification = document.createElement('div');

        // Set notification styles based on type
        const baseClasses = 'notification-enter p-4 rounded-md shadow-lg mb-2';
        const typeClasses = {
            info: 'bg-blue-50 text-blue-800',
            success: 'bg-green-50 text-green-800',
            error: 'bg-red-50 text-red-800',
            warning: 'bg-yellow-50 text-yellow-800'
        };

        notification.className = `${baseClasses} ${typeClasses[type]}`;
        notification.textContent = message;

        // Add to container
        container.appendChild(notification);

        // Remove after duration
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
};

// File upload handling
const fileUpload = {
    maxSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: ['text/plain', 'application/pdf', 'text/markdown'],

    validate(file) {
        if (file.size > this.maxSize) {
            notifications.show('File size must be less than 10MB', 'error');
            return false;
        }

        if (!this.allowedTypes.includes(file.type)) {
            notifications.show('Invalid file type. Please upload TXT, PDF, or MD files', 'error');
            return false;
        }

        return true;
    },

    async upload(formData, progressCallback) {
        try {
            const response = await fetch('/admin/upload', {
                method: 'POST',
                body: formData,
                onUploadProgress: progressEvent => {
                    if (progressCallback) {
                        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        progressCallback(percentCompleted);
                    }
                }
            });

            if (!response.ok) throw new Error('Upload failed');

            const result = await response.json();
            notifications.show('Document uploaded successfully!', 'success');
            return result;
        } catch (error) {
            notifications.show('Failed to upload document: ' + error.message, 'error');
            throw error;
        }
    }
};

// Document management
const documentManager = {
    async list() {
        try {
            const response = await fetch('/admin/documents');
            if (!response.ok) throw new Error('Failed to fetch documents');
            return await response.json();
        } catch (error) {
            notifications.show('Failed to load documents', 'error');
            return [];
        }
    },

    async delete(documentId) {
        try {
            const response = await fetch(`/admin/documents/${documentId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete document');
            notifications.show('Document deleted successfully', 'success');
            return true;
        } catch (error) {
            notifications.show('Failed to delete document', 'error');
            return false;
        }
    }
};

// Training interface
const trainingInterface = {
    async startTraining(documentIds) {
        try {
            const response = await fetch('/admin/train', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ documentIds })
            });

            if (!response.ok) throw new Error('Failed to start training');
            notifications.show('Training started successfully', 'success');
            return await response.json();
        } catch (error) {
            notifications.show('Failed to start training', 'error');
            throw error;
        }
    },

    async getStatus(trainingId) {
        try {
            const response = await fetch(`/admin/train/${trainingId}/status`);
            if (!response.ok) throw new Error('Failed to get training status');
            return await response.json();
        } catch (error) {
            notifications.show('Failed to get training status', 'error');
            return null;
        }
    }
};

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    // Set up file drag and drop
    const dropZone = document.querySelector('.drop-zone');
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = document.querySelector('input[type="file"]');
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        }
    }

    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', e => {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip absolute bg-gray-900 text-white p-2 rounded text-sm';
            tooltip.textContent = element.dataset.tooltip;
            document.body.appendChild(tooltip);

            const rect = element.getBoundingClientRect();
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
            tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;

            element.addEventListener('mouseleave', () => tooltip.remove());
        });
    });
});