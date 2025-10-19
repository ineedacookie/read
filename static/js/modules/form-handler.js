/**
 * Form Handler Module
 * Centralized form submission with validation and error handling
 * 
 * Usage:
 *   FormHandler.submit('#myForm', {
 *       onSuccess: (data) => console.log('Success!', data),
 *       onError: (errors) => console.error('Errors:', errors)
 *   });
 */

const FormHandler = {
    /**
     * Submit a form via AJAX
     */
    async submit(formSelector, options = {}) {
        const form = document.querySelector(formSelector);
        if (!form) {
            console.error(`Form '${formSelector}' not found`);
            return;
        }
        
        const {
            onSuccess = null,
            onError = null,
            onComplete = null,
            validateBeforeSubmit = true,
            showSuccessMessage = true,
            showErrorMessage = true
        } = options;
        
        // Validate form before submit
        if (validateBeforeSubmit && !this.validateForm(form)) {
            if (onError) onError({ general: 'Please fix form errors' });
            return;
        }
        
        // Disable form during submission
        this.disableForm(form);
        
        try {
            const formData = new FormData(form);
            const method = form.method || 'POST';
            const action = form.action;
            
            const response = await fetch(action, {
                method: method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.success !== false) {
                // Success
                if (showSuccessMessage) {
                    this.showMessage('success', data.message || 'Form submitted successfully!');
                }
                if (onSuccess) onSuccess(data);
            } else {
                // Server returned error
                if (showErrorMessage) {
                    this.showMessage('error', data.message || 'An error occurred');
                }
                if (data.errors) {
                    this.displayErrors(form, data.errors);
                }
                if (onError) onError(data.errors || {});
            }
        } catch (error) {
            console.error('Form submission error:', error);
            if (showErrorMessage) {
                this.showMessage('error', 'Network error. Please try again.');
            }
            if (onError) onError({ network: error.message });
        } finally {
            this.enableForm(form);
            if (onComplete) onComplete();
        }
    },
    
    /**
     * Validate form fields
     */
    validateForm(form) {
        let isValid = true;
        
        // Clear previous errors
        form.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
        form.querySelectorAll('.invalid-feedback').forEach(el => {
            el.remove();
        });
        
        // Check required fields
        form.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                this.markFieldInvalid(field, 'This field is required');
                isValid = false;
            }
        });
        
        // Check email fields
        form.querySelectorAll('input[type="email"]').forEach(field => {
            if (field.value && !this.isValidEmail(field.value)) {
                this.markFieldInvalid(field, 'Please enter a valid email');
                isValid = false;
            }
        });
        
        // Check number fields
        form.querySelectorAll('input[type="number"]').forEach(field => {
            const min = field.getAttribute('min');
            const max = field.getAttribute('max');
            const value = parseFloat(field.value);
            
            if (min !== null && value < parseFloat(min)) {
                this.markFieldInvalid(field, `Minimum value is ${min}`);
                isValid = false;
            }
            if (max !== null && value > parseFloat(max)) {
                this.markFieldInvalid(field, `Maximum value is ${max}`);
                isValid = false;
            }
        });
        
        return isValid;
    },
    
    /**
     * Mark field as invalid
     */
    markFieldInvalid(field, message) {
        field.classList.add('is-invalid');
        
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback d-block';
        feedback.textContent = message;
        
        field.parentNode.appendChild(feedback);
    },
    
    /**
     * Display server-side errors
     */
    displayErrors(form, errors) {
        Object.entries(errors).forEach(([fieldName, messages]) => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                const errorMessage = Array.isArray(messages) ? messages[0] : messages;
                this.markFieldInvalid(field, errorMessage);
            }
        });
    },
    
    /**
     * Validate email format
     */
    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },
    
    /**
     * Disable form during submission
     */
    disableForm(form) {
        form.querySelectorAll('input, select, textarea, button').forEach(el => {
            el.disabled = true;
        });
        
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.dataset.originalText = submitBtn.textContent;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
        }
    },
    
    /**
     * Enable form after submission
     */
    enableForm(form) {
        form.querySelectorAll('input, select, textarea, button').forEach(el => {
            el.disabled = false;
        });
        
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn && submitBtn.dataset.originalText) {
            submitBtn.textContent = submitBtn.dataset.originalText;
        }
    },
    
    /**
     * Show message to user
     */
    showMessage(type, message) {
        // Try to use existing alert system
        if (typeof showAlert === 'function') {
            showAlert(type, message);
        } else {
            // Fallback to console
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    },
    
    /**
     * Reset form
     */
    reset(formSelector) {
        const form = document.querySelector(formSelector);
        if (form) {
            form.reset();
            form.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
            });
            form.querySelectorAll('.invalid-feedback').forEach(el => {
                el.remove();
            });
        }
    }
};

// Make available globally
if (typeof window !== 'undefined') {
    window.FormHandler = FormHandler;
}

