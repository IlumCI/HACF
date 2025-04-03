/**
 * HACF Project Builder
 * 
 * Handles the simplified form-based project creation process with
 * visual feedback of the HACF layer processing.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const generateBtn = document.getElementById('generate-project-btn');
    const projectForm = document.getElementById('project-builder-form');
    const processingModal = new bootstrap.Modal(document.getElementById('processing-modal'));
    const progressBar = document.getElementById('progress-bar');
    const currentLayerText = document.getElementById('current-layer-text');
    const processingStatus = document.getElementById('processing-status');
    
    // Form fields
    const titleInput = document.getElementById('project-title');
    const descriptionInput = document.getElementById('project-description');
    const projectTypeSelect = document.getElementById('project-type');
    const techStackSelect = document.getElementById('tech-stack');
    
    // Generate Project Button
    if (generateBtn) {
        generateBtn.addEventListener('click', function() {
            // Validate form
            if (!titleInput.value || !descriptionInput.value) {
                alert('Please fill in the project title and description.');
                return;
            }
            
            // Show processing modal
            processingModal.show();
            
            // Start HACF processing
            processHACFLayers();
        });
    }
    
    // Process through all HACF layers with visual feedback
    function processHACFLayers() {
        const layers = [
            { name: "Layer 1: Task Definition & Planning", status: "Analyzing your project requirements...", progress: 20 },
            { name: "Layer 2: Refinement & Base Structure", status: "Creating technical specifications and selecting optimal technologies...", progress: 40 },
            { name: "Layer 3: Development & Execution", status: "Generating code implementation for your project...", progress: 60 },
            { name: "Layer 4: Debugging & Optimization", status: "Optimizing code and implementing security best practices...", progress: 80 },
            { name: "Layer 5: Final Output", status: "Packaging your project files for download...", progress: 100 }
        ];
        
        let currentLayer = 0;
        
        // Process each layer with a delay to simulate AI processing
        function processNextLayer() {
            if (currentLayer >= layers.length) {
                // All layers processed, create project via API
                createProject();
                return;
            }
            
            const layer = layers[currentLayer];
            updateProcessingUI(layer.name, layer.status, layer.progress);
            
            currentLayer++;
            
            // Simulate processing time (adjust for realistic feel)
            setTimeout(processNextLayer, 1500);
        }
        
        // Start the processing
        processNextLayer();
    }
    
    // Update the processing modal UI
    function updateProcessingUI(layerName, status, progress) {
        currentLayerText.textContent = layerName;
        processingStatus.textContent = status;
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        progressBar.textContent = `${progress}%`;
    }
    
    // Create project via API
    function createProject() {
        // Get priority value
        const priorityValue = document.querySelector('input[name="priority"]:checked').value;
        
        // Prepare form data
        const projectData = {
            title: titleInput.value,
            description: descriptionInput.value,
            project_type: projectTypeSelect.value,
            tech_stack: techStackSelect.value,
            priority: priorityValue
        };
        
        // Send API request
        fetch('/create_project', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(projectData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Hide modal and redirect to project detail page
                processingModal.hide();
                window.location.href = `/project/${data.project_id}`;
            } else {
                // Show error
                console.error('Error creating project:', data.message);
                alert(`Error creating project: ${data.message}`);
                processingModal.hide();
            }
        })
        .catch(error => {
            console.error('Error creating project:', error);
            alert('An error occurred while generating your project. Please try again.');
            processingModal.hide();
        });
    }
    
    // Tab navigation for HACF process explanation
    const processTabs = document.querySelectorAll('#hacf-process-tabs button');
    if (processTabs.length > 0) {
        processTabs.forEach(button => {
            button.addEventListener('click', function(event) {
                event.preventDefault();
                const target = document.querySelector(this.getAttribute('data-bs-target'));
                // Hide all tab panes
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('show', 'active');
                });
                // Show the selected tab pane
                target.classList.add('show', 'active');
                // Update active state for tabs
                processTabs.forEach(tab => tab.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }
});