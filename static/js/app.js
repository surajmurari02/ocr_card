/**
 * CardScan Pro - Professional Business Card Scanner
 * AI-powered contact extraction and digitization
 */

class OCRCardApp {
    constructor() {
        this.currentFile = null;
        this.apiEndpoint = '/process_image';
        this.isProcessing = false;
        
        this.init();
    }
    
    init() {
        this.initTheme();
        this.bindEvents();
        this.loadSavedSettings();
        this.setupDragAndDrop();
    }
    
    initTheme() {
        // Check for saved theme or use system preference
        const savedTheme = localStorage.getItem('theme');
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        const currentTheme = savedTheme || systemTheme;
        
        // Apply theme
        this.setTheme(currentTheme);
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
    
    setTheme(theme) {
        const html = document.documentElement;
        if (theme === 'dark') {
            html.classList.add('dark');
        } else {
            html.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
    }
    
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.classList.contains('dark') ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        
        // Show notification
        this.showNotification(`Switched to ${newTheme} theme`, 'success');
    }
    
    bindEvents() {
        // File input
        const imageInput = document.getElementById('imageInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const scanBtn = document.getElementById('scanBtn');
        const settingsToggle = document.getElementById('settingsToggle');
        const saveSettingsBtn = document.getElementById('saveSettings');
        const modal = document.getElementById('resultModal');
        const modalClose = document.getElementById('modalClose');
        const themeToggle = document.getElementById('themeToggle');
        
        if (imageInput) {
            imageInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => imageInput?.click());
        }
        
        if (scanBtn) {
            scanBtn.addEventListener('click', () => this.scanBusinessCard());
        }
        
        if (settingsToggle) {
            settingsToggle.addEventListener('click', () => this.toggleSettings());
        }
        
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }
        
        if (modalClose) {
            modalClose.addEventListener('click', () => this.closeModal());
        }
        
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }
    
    setupDragAndDrop() {
        const uploadSection = document.getElementById('uploadSection');
        
        if (!uploadSection) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadSection.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadSection.addEventListener(eventName, () => {
                uploadSection.classList.add('border-green-500', 'bg-green-50', 'scale-105');
                uploadSection.classList.remove('border-gray-300');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadSection.addEventListener(eventName, () => {
                uploadSection.classList.remove('border-green-500', 'bg-green-50', 'scale-105');
                uploadSection.classList.add('border-gray-300');
            }, false);
        });
        
        uploadSection.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        }, false);
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }
    
    handleFile(file) {
        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'];
        
        if (!allowedTypes.includes(file.type)) {
            this.showNotification('Please select a valid image file (JPEG, PNG, GIF, BMP, TIFF)', 'error');
            return;
        }
        
        // Validate file size (10MB limit)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            this.showNotification('File size must be less than 10MB', 'error');
            return;
        }
        
        this.currentFile = file;
        this.displayImagePreview(file);
        this.showScanButton();
    }
    
    displayImagePreview(file) {
        const reader = new FileReader();
        const uploadSection = document.getElementById('uploadSection');
        const processingSection = document.getElementById('processingSection');
        const previewImg = document.getElementById('imagePreview');
        const imageInfo = document.getElementById('imageInfo');
        
        reader.onload = (e) => {
            if (previewImg) {
                previewImg.src = e.target.result;
                
                // Hide upload section and show processing section
                uploadSection.style.display = 'none';
                processingSection.classList.remove('hidden');
                processingSection.classList.add('animate-slide-up');
                
                // Update file info with professional styling
                if (imageInfo) {
                    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
                    const fileType = file.type.split('/')[1].toUpperCase();
                    
                    imageInfo.innerHTML = `
                        <div class="space-y-2">
                            <div class="flex items-center justify-between">
                                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">File Name</span>
                                <span class="text-sm text-slate-600 dark:text-slate-400 font-mono">${file.name}</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Size</span>
                                <span class="text-sm text-slate-600 dark:text-slate-400">${sizeInMB} MB</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Format</span>
                                <span class="inline-flex items-center px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs font-medium rounded-lg">${fileType}</span>
                            </div>
                        </div>
                    `;
                }
            }
        };
        
        reader.readAsDataURL(file);
    }
    
    showScanButton() {
        // Button is already visible in the new layout
        // Just ensure it's enabled
        const scanBtn = document.getElementById('scanBtn');
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.classList.add('animate-scale-in');
        }
    }
    
    async scanBusinessCard() {
        if (!this.currentFile || this.isProcessing) {
            return;
        }
        
        this.setLoading(true);
        
        try {
            const formData = new FormData();
            formData.append('image', this.currentFile);
            
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }
            
            this.displayResults(data);
            this.showNotification('Contact information extracted successfully!', 'success');
            
        } catch (error) {
            console.error('Error processing image:', error);
            this.showError('Failed to process image: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(loading) {
        this.isProcessing = loading;
        const scanBtn = document.getElementById('scanBtn');
        const spinner = document.getElementById('loadingSpinner');
        const btnText = document.getElementById('scanBtnText');
        const scanIcon = document.getElementById('scanIcon');
        
        if (scanBtn && spinner && btnText) {
            scanBtn.disabled = loading;
            
            if (loading) {
                spinner.classList.remove('hidden');
                scanIcon.classList.add('hidden');
                btnText.textContent = 'Analyzing...';
                scanBtn.classList.add('opacity-75');
            } else {
                spinner.classList.add('hidden');
                scanIcon.classList.remove('hidden');
                btnText.textContent = 'Extract Contact Info';
                scanBtn.classList.remove('opacity-75');
            }
        }
    }
    
    displayResults(data) {
        const modal = document.getElementById('resultModal');
        const resultContent = document.getElementById('resultContent');
        
        if (!modal || !resultContent) return;
        
        // Store data for export
        this.lastResult = data;
        
        // Create result HTML
        const resultHTML = this.createResultHTML(data);
        resultContent.innerHTML = resultHTML;
        
        // Show modal with animation
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
    
    createResultHTML(data) {
        const fields = [
            { key: 'name', label: 'Name', icon: '👤', color: 'blue' },
            { key: 'designation', label: 'Designation', icon: '💼', color: 'teal' },
            { key: 'company', label: 'Company', icon: '🏢', color: 'cyan' },
            { key: 'mobile', label: 'Mobile', icon: '📱', color: 'emerald' },
            { key: 'email', label: 'Email', icon: '📧', color: 'rose' },
            { key: 'address', label: 'Address', icon: '📍', color: 'amber' }
        ];
        
        let resultCards = fields.map((field, index) => {
            const value = data[field.key] || data[field.key.replace('designation', 'company name')]; // Handle different key formats
            const displayValue = value && value !== 'null' ? value : 'Not available';
            const isEmpty = !value || value === 'null';
            
            return `
                <div class="card-glass rounded-xl p-4 border border-slate-200 dark:border-slate-600 transition-all duration-200 hover:shadow-elegant group animate-scale-in" style="animation-delay: ${index * 50}ms">
                    <div class="flex items-start space-x-3">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-gradient-to-br from-${field.color}-100 to-${field.color}-200 dark:from-${field.color}-900/30 dark:to-${field.color}-800/30 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                                <span class="text-sm">${field.icon}</span>
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">
                                ${field.label}
                            </div>
                            <div class="text-sm font-medium ${isEmpty ? 'text-slate-400 dark:text-slate-500 italic' : 'text-slate-800 dark:text-slate-200'} break-words leading-relaxed">
                                ${displayValue}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        const processingTime = data.processing_time ? `${data.processing_time.toFixed(2)}s` : 'N/A';
        
        return `
            <div class="space-y-5">
                <!-- Processing Summary -->
                <div class="card-glass rounded-xl p-4 border border-slate-200 dark:border-slate-600 mb-6">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <div class="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                                <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                                </svg>
                            </div>
                            <div>
                                <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200">Extraction Complete</h3>
                                <p class="text-xs text-slate-600 dark:text-slate-400">Extracted in ${processingTime}</p>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-lg font-bold text-green-600 dark:text-green-400">${processingTime}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Extracted Information -->
                <div class="space-y-3">
                    <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3">Contact Information</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        ${resultCards}
                    </div>
                </div>
                
                <!-- Export Options -->
                <div class="border-t border-slate-200 dark:border-slate-600 pt-5">
                    <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3">Export Options</h3>
                    <div class="grid grid-cols-3 gap-3">
                        <button 
                            class="flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-xl font-medium transition-all duration-200 shadow-sm hover:shadow-md group text-sm"
                            onclick="app.exportResults('json')"
                        >
                            <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                            </svg>
                            <span>JSON</span>
                        </button>
                        <button 
                            class="flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white p-3 rounded-xl font-medium transition-all duration-200 shadow-sm hover:shadow-md group text-sm"
                            onclick="app.exportResults('csv')"
                        >
                            <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                            <span>CSV</span>
                        </button>
                        <button 
                            class="flex items-center justify-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white p-3 rounded-xl font-medium transition-all duration-200 shadow-sm hover:shadow-md group text-sm"
                            onclick="app.exportResults('vcard')"
                        >
                            <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                            </svg>
                            <span>vCard</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    showError(message) {
        const modal = document.getElementById('resultModal');
        const resultContent = document.getElementById('resultContent');
        
        if (!modal || !resultContent) return;
        
        resultContent.innerHTML = `
            <div class="text-center py-8">
                <div class="text-6xl mb-4 animate-bounce">⚠️</div>
                <h3 class="text-2xl font-bold text-red-600 mb-3">Extraction Failed</h3>
                <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 max-w-md mx-auto">
                    <p class="text-red-700 dark:text-red-300">${message}</p>
                </div>
                <button 
                    class="mt-6 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-6 py-2 rounded-lg font-semibold transition-all duration-200 shadow-sm hover:shadow-md"
                    onclick="app.closeModal()"
                >
                    Try Again
                </button>
            </div>
        `;
        
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
    
    closeModal() {
        const modal = document.getElementById('resultModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
        }
    }
    
    toggleSettings() {
        const content = document.getElementById('settingsContent');
        if (content) {
            content.classList.toggle('hidden');
        }
    }
    
    saveSettings() {
        const apiUrlInput = document.getElementById('apiUrl');
        const timeoutInput = document.getElementById('requestTimeout');
        
        if (apiUrlInput) {
            localStorage.setItem('ocrApiUrl', apiUrlInput.value);
            this.apiEndpoint = apiUrlInput.value;
        }
        
        if (timeoutInput) {
            localStorage.setItem('requestTimeout', timeoutInput.value);
        }
        
        this.showNotification('Settings saved successfully!', 'success');
        this.toggleSettings();
    }
    
    loadSavedSettings() {
        const savedApiUrl = localStorage.getItem('ocrApiUrl');
        const savedTimeout = localStorage.getItem('requestTimeout');
        
        const apiUrlInput = document.getElementById('apiUrl');
        const timeoutInput = document.getElementById('requestTimeout');
        
        if (savedApiUrl && apiUrlInput) {
            apiUrlInput.value = savedApiUrl;
            this.apiEndpoint = savedApiUrl;
        }
        
        if (savedTimeout && timeoutInput) {
            timeoutInput.value = savedTimeout;
        }
    }
    
    exportResults(format) {
        if (!this.lastResult) {
            this.showNotification('No data to export', 'error');
            return;
        }
        
        let content, filename, mimeType;
        
        switch (format) {
            case 'json':
                content = JSON.stringify(this.lastResult, null, 2);
                filename = 'business_card_data.json';
                mimeType = 'application/json';
                break;
                
            case 'csv':
                content = this.convertToCSV(this.lastResult);
                filename = 'business_card_data.csv';
                mimeType = 'text/csv';
                break;
                
            case 'vcard':
                content = this.convertToVCard(this.lastResult);
                filename = 'business_card.vcf';
                mimeType = 'text/vcard';
                break;
                
            default:
                return;
        }
        
        this.downloadFile(content, filename, mimeType);
        this.showNotification(`Contact data exported as ${format.toUpperCase()}!`, 'success');
    }
    
    convertToCSV(data) {
        const headers = ['Field', 'Value'];
        const rows = Object.entries(data)
            .filter(([key, value]) => !['status', 'filename', 'processing_time', 'raw_response'].includes(key))
            .map(([key, value]) => [key, value || '']);
        
        const csvContent = [headers, ...rows]
            .map(row => row.map(field => `"${field}"`).join(','))
            .join('\\n');
            
        return csvContent;
    }
    
    convertToVCard(data) {
        return `BEGIN:VCARD
VERSION:3.0
FN:${data.name || ''}
TITLE:${data.designation || ''}
ORG:${data.company || ''}
TEL:${data.mobile || ''}
EMAIL:${data.email || ''}
ADR:;;${data.address || ''};;;;
END:VCARD`;
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    showNotification(message, type = 'success') {
        // Remove existing notifications
        const existing = document.querySelectorAll('.notification');
        existing.forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new OCRCardApp();
});