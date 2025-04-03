// Hierarchical AI Collaboration Framework (HACF) JavaScript
let currentProject = null;

// Initialize HACF
document.addEventListener('DOMContentLoaded', async function() {
    // Check for existing projects
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        
        if (data.status === 'success' && data.projects.length > 0) {
            currentProject = data.projects[0]; // Use the most recent project
            loadProject(currentProject);
        }
    } catch (error) {
        console.error("Error loading projects:", error);
    }
});

// Load project data into the UI
function loadProject(project) {
    if (!project || !project.stages) return;
    
    document.getElementById('task-input').value = project.title || '';
    
    // Load each stage content
    project.stages.forEach(stage => {
        const outputElement = getOutputElementForStage(stage.stage_type);
        if (outputElement && stage.content) {
            outputElement.innerText = stage.content;
        }
    });
}

// Helper to get the output element for a specific stage
function getOutputElementForStage(stageType) {
    switch (stageType) {
        case 'task_definition':
            return document.getElementById('task-output');
        case 'refinement':
            return document.getElementById('refine-output');
        case 'development':
            return document.getElementById('develop-output');
        case 'optimization':
            return document.getElementById('optimize-output');
        case 'final_output':
            return document.getElementById('final-output');
        default:
            return null;
    }
}

// Create a new HACF project
async function createNewProject(title, description) {
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            currentProject = data.project;
            return currentProject;
        } else {
            throw new Error(data.message || 'Failed to create project');
        }
    } catch (error) {
        console.error("Error creating project:", error);
        throw error;
    }
}

// Add a stage to the current project
async function addProjectStage(stageType, content) {
    if (!currentProject) {
        throw new Error("No active project");
    }
    
    try {
        const response = await fetch(`/api/projects/${currentProject.id}/stages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                stage_type: stageType,
                content: content,
                completed: true
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Update the local project data
            if (!currentProject.stages) {
                currentProject.stages = [];
            }
            currentProject.stages.push(data.stage);
            return data.stage;
        } else {
            throw new Error(data.message || 'Failed to add stage');
        }
    } catch (error) {
        console.error(`Error adding ${stageType} stage:`, error);
        throw error;
    }
}

// Add a file to the current project
async function addProjectFile(filename, content) {
    if (!currentProject) {
        throw new Error("No active project");
    }
    
    try {
        const response = await fetch(`/api/projects/${currentProject.id}/files`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: filename,
                content: content
            })
        });
        
        const data = await response.json();
        return data.status === 'success';
    } catch (error) {
        console.error("Error adding file:", error);
        return false;
    }
}

// Define the task (first stage of HACF)
async function defineTask() {
    const taskDescription = document.getElementById('task-input').value;
    if (!taskDescription.trim()) {
        alert("Please enter a task description");
        return;
    }
    
    document.getElementById('task-output').innerText = "Processing...";
    
    try {
        // Create a new project if we don't have one
        if (!currentProject) {
            currentProject = await createNewProject(taskDescription, "Project created via HACF");
        }
        
        // Call Puter.js AI
        const response = await puter.ai.chat(taskDescription);
        document.getElementById('task-output').innerText = response;
        
        // Save this stage to the database
        await addProjectStage('task_definition', response);
        
        // Continue to the next stage
        await refineStructure(response);
    } catch (error) {
        document.getElementById('task-output').innerText = "Error: " + error.message;
        console.error("Error defining task:", error);
    }
}

// Refine the structure (second stage of HACF)
async function refineStructure(input) {
    document.getElementById('refine-output').innerText = "Processing...";
    
    try {
        const structurePrompt = `Refine the following plan into a technical roadmap with base code structure: ${input}`;
        const response = await puter.ai.chat(structurePrompt);
        document.getElementById('refine-output').innerText = response;
        
        // Save this stage to the database
        await addProjectStage('refinement', response);
        
        // Continue to the next stage
        await developCode(response);
    } catch (error) {
        document.getElementById('refine-output').innerText = "Error: " + error.message;
        console.error("Error refining structure:", error);
    }
}

// Develop the code (third stage of HACF)
async function developCode(input) {
    document.getElementById('develop-output').innerText = "Processing...";
    
    try {
        const developmentPrompt = `Generate the full backend code for the following technical roadmap: ${input}`;
        const response = await puter.ai.chat(developmentPrompt);
        document.getElementById('develop-output').innerText = response;
        
        // Save this stage to the database
        await addProjectStage('development', response);
        
        // Continue to the next stage
        await optimizeCode(response);
    } catch (error) {
        document.getElementById('develop-output').innerText = "Error: " + error.message;
        console.error("Error developing code:", error);
    }
}

// Optimize the code (fourth stage of HACF)
async function optimizeCode(input) {
    document.getElementById('optimize-output').innerText = "Processing...";
    
    try {
        const optimizationPrompt = `Review, debug, and optimize the following code. Add security features like input validation and authentication enforcement: ${input}`;
        const response = await puter.ai.chat(optimizationPrompt);
        document.getElementById('optimize-output').innerText = response;
        
        // Save this stage to the database
        await addProjectStage('optimization', response);
        
        // Continue to the final output
        await finalizeOutput(response);
    } catch (error) {
        document.getElementById('optimize-output').innerText = "Error: " + error.message;
        console.error("Error optimizing code:", error);
    }
}

// Finalize the output (final stage of HACF)
async function finalizeOutput(input) {
    try {
        // Try to parse the input as JSON to see if it contains multiple files
        let files;
        try {
            files = JSON.parse(input);
        } catch (e) {
            // If not JSON, treat as a single file
            files = [{
                name: 'HACF_Project.txt',
                content: input
            }];
        }

        // Save files to localStorage for download later
        localStorage.setItem('projectFiles', JSON.stringify(files));
        
        // Save to database too if possible
        if (Array.isArray(files)) {
            for (const file of files) {
                await addProjectFile(file.name, file.content);
            }
        }
        
        // Update the final output display
        document.getElementById('final-output').innerText = "Project ready for download.";
        
        // Save this final stage to the database
        await addProjectStage('final_output', JSON.stringify(files));
        
    } catch (error) {
        document.getElementById('final-output').innerText = "Error finalizing output: " + error.message;
        console.error("Error finalizing output:", error);
    }
}

// Generate download files
function generateDownload() {
    const files = JSON.parse(localStorage.getItem('projectFiles'));
    if (!files) {
        alert("No project data available for download.");
        return;
    }

    if (files.length === 1) {
        // Single file download
        const file = files[0];
        const blob = new Blob([file.content], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = file.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } else {
        // Multiple files download as a zip
        const zip = new JSZip();
        files.forEach(file => {
            zip.file(file.name, file.content);
        });
        zip.generateAsync({ type: 'blob' }).then(function(content) {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(content);
            a.download = 'HACF_Project.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
    }
}
