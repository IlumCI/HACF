// Hierarchical AI Collaboration Framework (HACF) JavaScript
async function defineTask() {
    const taskDescription = document.getElementById('task-input').value;
    if (!taskDescription.trim()) {
        alert("Please enter a task description");
        return;
    }
    
    document.getElementById('task-output').innerText = "Processing...";
    
    try {
        const response = await puter.ai.chat(taskDescription);
        document.getElementById('task-output').innerText = response;
        await refineStructure(response);
    } catch (error) {
        document.getElementById('task-output').innerText = "Error: " + error.message;
        console.error("Error defining task:", error);
    }
}

async function refineStructure(input) {
    document.getElementById('refine-output').innerText = "Processing...";
    
    try {
        const structurePrompt = `Refine the following plan into a technical roadmap with base code structure: ${input}`;
        const response = await puter.ai.chat(structurePrompt);
        document.getElementById('refine-output').innerText = response;
        await developCode(response);
    } catch (error) {
        document.getElementById('refine-output').innerText = "Error: " + error.message;
        console.error("Error refining structure:", error);
    }
}

async function developCode(input) {
    document.getElementById('develop-output').innerText = "Processing...";
    
    try {
        const developmentPrompt = `Generate the full backend code for the following technical roadmap: ${input}`;
        const response = await puter.ai.chat(developmentPrompt);
        document.getElementById('develop-output').innerText = response;
        await optimizeCode(response);
    } catch (error) {
        document.getElementById('develop-output').innerText = "Error: " + error.message;
        console.error("Error developing code:", error);
    }
}

async function optimizeCode(input) {
    document.getElementById('optimize-output').innerText = "Processing...";
    
    try {
        const optimizationPrompt = `Review, debug, and optimize the following code. Add security features like input validation and authentication enforcement: ${input}`;
        const response = await puter.ai.chat(optimizationPrompt);
        document.getElementById('optimize-output').innerText = response;
        await finalizeOutput(response);
    } catch (error) {
        document.getElementById('optimize-output').innerText = "Error: " + error.message;
        console.error("Error optimizing code:", error);
    }
}

function finalizeOutput(input) {
    // Parse the input to determine if it contains multiple files
    let files;
    try {
        files = JSON.parse(input);
    } catch (e) {
        files = [{
            name: 'HACF_Project.txt',
            content: input
        }];
    }

    // Save files to localStorage
    localStorage.setItem('projectFiles', JSON.stringify(files));
    document.getElementById('final-output').innerText = "Project ready for download.";
}

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
