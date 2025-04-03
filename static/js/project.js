/**
 * Project Management JavaScript for HACF
 * Handles project creation, layer transitions, and file operations
 */

// Project data storage
let projectData = {
    taskDefinition: null,
    refinedStructure: null,
    developmentCode: null,
    optimizedCode: null,
    files: []
};

// Set a current active layer
let activeLayer = 1;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize code preview syntax highlighting if available
    initCodePreviewArea();
    
    // Setup layer transition animations
    setupLayerTransitions();
    
    // Initialize file explorer if files exist
    setupFileExplorer();
    
    // Setup export functionality
    setupExportOptions();
    
    // Setup layer processing buttons
    setupLayerProcessing();
});

/**
 * Initialize code preview area with syntax highlighting
 */
function initCodePreviewArea() {
    const codePreview = document.getElementById('code-preview');
    if (!codePreview) return;
    
    // If using a code editor library like CodeMirror or Monaco, initialize it here
    // For this implementation, we'll use a simple pre tag
}

/**
 * Setup animated transitions between HACF layers
 */
function setupLayerTransitions() {
    // Add smooth scrolling for layer navigation
    document.querySelectorAll('.list-group-item').forEach(item => {
        item.addEventListener('click', function(e) {
            if (this.classList.contains('disabled')) {
                e.preventDefault();
                return;
            }
            
            // Get the layer number
            const layerNum = this.getAttribute('href').replace('#layer', '');
            
            // Update active layer
            activeLayer = parseInt(layerNum);
            updateActiveLayerVisual();
        });
    });
    
    // Continue to next layer buttons
    document.querySelectorAll('[id^="continue-to-layer"]').forEach(button => {
        button.addEventListener('click', function() {
            const targetLayer = this.id.replace('continue-to-layer', '');
            activeLayer = parseInt(targetLayer);
            updateActiveLayerVisual();
        });
    });
}

/**
 * Update visual indicators for active layer
 */
function updateActiveLayerVisual() {
    // Remove active class from all layer cards
    document.querySelectorAll('.layer-card').forEach(card => {
        card.classList.remove('active');
    });
    
    // Add active class to current layer
    const activeCard = document.querySelector(`#layer${activeLayer}-content .layer-card`);
    if (activeCard) {
        activeCard.classList.add('active');
    }
    
    // Animate transition to the active layer
    animateLayerTransition(activeLayer);
}

/**
 * Animate transition to a specific layer
 */
function animateLayerTransition(layerNum) {
    // Add visual effect to show the transition between layers
    const arrows = document.querySelectorAll('.transition-arrow');
    
    // Reset all arrows
    arrows.forEach(arrow => {
        arrow.classList.remove('active');
    });
    
    // Highlight arrows up to the current layer
    for (let i = 1; i < layerNum; i++) {
        const arrow = document.querySelector(`.layer-transition:nth-of-type(${i})`);
        if (arrow) {
            arrow.querySelector('.transition-arrow').classList.add('active');
        }
    }
}

/**
 * Setup file explorer functionality
 */
function setupFileExplorer() {
    const fileList = document.getElementById('file-list');
    if (!fileList) return;
    
    // Add click handlers to file items
    document.querySelectorAll('.file-item').forEach(fileItem => {
        fileItem.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            
            // Remove active class from all file items
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Add active class to clicked item
            this.classList.add('active');
            
            // Load file content
            loadFileContent(filename);
        });
    });
    
    // Setup file preview modal handlers
    document.querySelectorAll('.view-file-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            showFilePreviewModal(filename);
        });
    });
    
    // Download individual file
    const downloadFileBtn = document.getElementById('download-single-file');
    if (downloadFileBtn) {
        downloadFileBtn.addEventListener('click', function() {
            const filename = document.getElementById('filePreviewModalLabel').textContent;
            downloadSingleFile(filename);
        });
    }
}

/**
 * Load file content into the preview area
 */
function loadFileContent(filename) {
    // This would normally fetch from the server
    fetch(`/project_file/${projectId}/${filename}`)
        .then(response => response.text())
        .then(content => {
            const codePreview = document.getElementById('code-preview');
            if (codePreview) {
                codePreview.textContent = content;
            }
        })
        .catch(error => {
            console.error('Error loading file:', error);
        });
}

/**
 * Show file preview modal with content
 */
function showFilePreviewModal(filename) {
    fetch(`/project_file/${projectId}/${filename}`)
        .then(response => response.text())
        .then(content => {
            document.getElementById('filePreviewModalLabel').textContent = filename;
            document.getElementById('file-preview-content').textContent = content;
            
            const fileModal = new bootstrap.Modal(document.getElementById('filePreviewModal'));
            fileModal.show();
        })
        .catch(error => {
            console.error('Error loading file for preview:', error);
        });
}

/**
 * Download a single file
 */
function downloadSingleFile(filename) {
    fetch(`/project_file/${projectId}/${filename}`)
        .then(response => response.text())
        .then(content => {
            const blob = new Blob([content], { type: 'text/plain' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error downloading file:', error);
        });
}

/**
 * Setup export options
 */
function setupExportOptions() {
    // ZIP download
    const exportZipBtn = document.getElementById('export-zip');
    if (exportZipBtn) {
        exportZipBtn.addEventListener('click', function() {
            downloadProjectAsZip();
        });
    }
    
    // GitHub export
    const exportGithubBtn = document.getElementById('export-github');
    if (exportGithubBtn) {
        exportGithubBtn.addEventListener('click', function() {
            exportToGitHub();
        });
    }
    
    // JSON export
    const exportJsonBtn = document.getElementById('export-json');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', function() {
            exportProjectAsJson();
        });
    }
    
    // Main download button
    const downloadProjectBtn = document.getElementById('download-project');
    if (downloadProjectBtn) {
        downloadProjectBtn.addEventListener('click', function() {
            downloadProjectAsZip();
        });
    }
}

/**
 * Download project as a ZIP file
 */
function downloadProjectAsZip() {
    fetch(`/project_zip/${projectId}`)
        .then(response => response.blob())
        .then(blob => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'project.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error downloading project:', error);
            alert('Error downloading project. Please try again.');
        });
}

/**
 * Export project to GitHub
 */
function exportToGitHub() {
    // This would open a modal to get GitHub credentials and repo details
    alert('GitHub export feature coming soon!');
}

/**
 * Export project as JSON
 */
function exportProjectAsJson() {
    fetch(`/project_json/${projectId}`)
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'project.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error exporting project as JSON:', error);
            alert('Error exporting project. Please try again.');
        });
}

/**
 * Setup layer processing functionality
 */
function setupLayerProcessing() {
    // Process layer buttons
    document.querySelectorAll('[id^="process-layer"]').forEach(button => {
        button.addEventListener('click', async function() {
            const layerNum = this.id.replace('process-layer', '');
            await processLayer(layerNum);
        });
    });
}

/**
 * Process a specific HACF layer
 */
async function processLayer(layerNum) {
    const button = document.getElementById(`process-layer${layerNum}`);
    if (!button) return;
    
    // Disable button and show loading state
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    try {
        let inputData = null;
        
        // Get appropriate input data based on layer
        switch(parseInt(layerNum)) {
            case 1:
                // Task Definition Layer
                inputData = document.getElementById('task-description').value;
                break;
            case 2:
                // Refinement Layer - uses output from Layer 1
                inputData = projectData.taskDefinition;
                break;
            case 3:
                // Development Layer - uses output from Layer 2
                inputData = projectData.refinedStructure;
                break;
            case 4:
                // Optimization Layer - uses output from Layer 3
                inputData = projectData.developmentCode;
                break;
            case 5:
                // Final Output Layer - uses output from Layer 4
                inputData = projectData.optimizedCode;
                break;
        }
        
        if (!inputData) {
            throw new Error('No input data available for this layer');
        }
        
        // Call the API to process this layer
        const response = await fetch(`/process_layer/${projectId}/${layerNum}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ input: inputData })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Store the result in project data
        switch(parseInt(layerNum)) {
            case 1:
                projectData.taskDefinition = result.output;
                break;
            case 2:
                projectData.refinedStructure = result.output;
                break;
            case 3:
                projectData.developmentCode = result.output;
                break;
            case 4:
                projectData.optimizedCode = result.output;
                break;
            case 5:
                projectData.files = result.files;
                break;
        }
        
        // Refresh the page to show updates
        window.location.reload();
    } catch (error) {
        console.error(`Error processing layer ${layerNum}:`, error);
        alert(`Error processing layer ${layerNum}: ${error.message}`);
        
        // Reset button state
        button.disabled = false;
        button.innerHTML = `Process Layer ${layerNum}`;
    }
}