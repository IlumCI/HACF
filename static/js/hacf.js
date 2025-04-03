// Hierarchical AI Collaboration Framework (HACF) JavaScript
// Implements the 5-layer architecture as documented

// Project data storage
let projectData = {
    taskDefinition: null,
    refinedStructure: null,
    developmentCode: null,
    optimizedCode: null,
    finalOutput: null
};

/**
 * Layer 1: Task Definition & Planning Layer
 * Uses model emulation similar to meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo
 * Converts user requests into structured plans and well-formed prompts
 */
async function defineTask() {
    const taskDescription = document.getElementById('task-input').value;
    if (!taskDescription.trim()) {
        alert("Please enter a task description");
        return;
    }
    
    document.getElementById('task-output').innerText = "Processing with Task Definition & Planning Layer...";
    
    try {
        // Setup prompt to match the Task Definition Layer functionality
        const planningPrompt = `
        You are the Task Definition & Planning Layer of the Hierarchical AI Collaboration Framework.
        Your role is to convert user requests into structured plans and well-formed prompts.
        
        Analyze this user request and structure it into an actionable plan.
        Output a formatted JSON containing required features and project structure.
        
        User Request: ${taskDescription}
        
        Format your response as a well-structured JSON with Project, Features, and Next_Prompt fields.
        `;
        
        const response = await puter.ai.chat(planningPrompt);
        
        // Display the formatted result
        document.getElementById('task-output').innerText = formatJsonResponse(response);
        
        // Store the result for the next layer
        projectData.taskDefinition = response;
        
        // Move to the next layer in the hierarchy
        await refineStructure(response);
    } catch (error) {
        document.getElementById('task-output').innerText = "Error in Task Definition Layer: " + error.message;
        console.error("Error defining task:", error);
    }
}

/**
 * Layer 2: Refinement & Base Structure Layer
 * Uses model emulation similar to deepseek-reasoner
 * Converts the high-level plan into a technical roadmap with base code structure
 */
async function refineStructure(input) {
    document.getElementById('refine-output').innerText = "Processing with Refinement & Base Structure Layer...";
    
    try {
        // Setup prompt to match the Refinement Layer functionality
        const structurePrompt = `
        You are the Refinement & Base Structure Layer of the Hierarchical AI Collaboration Framework.
        Your role is to convert high-level plans into technical roadmaps with base code structure.
        
        Assign specific frameworks, libraries, and data models.
        Create an outline for frontend, backend, and database.
        Ensure project feasibility and consistency.
        
        Previous Layer Output: ${input}
        
        Format your response as a well-structured JSON with specific technical details for Frontend, Backend, Database, 
        and include a Next_Prompt field for the Development Layer.
        `;
        
        const response = await puter.ai.chat(structurePrompt);
        
        // Display the formatted result
        document.getElementById('refine-output').innerText = formatJsonResponse(response);
        
        // Store the result for the next layer
        projectData.refinedStructure = response;
        
        // Move to the next layer in the hierarchy
        await developCode(response);
    } catch (error) {
        document.getElementById('refine-output').innerText = "Error in Refinement Layer: " + error.message;
        console.error("Error refining structure:", error);
    }
}

/**
 * Layer 3: Development & Execution Layer
 * Uses model emulation similar to codestral-latest or claude-3-7-sonnet
 * Generates fully functional code based on structured inputs
 */
async function developCode(input) {
    document.getElementById('develop-output').innerText = "Processing with Development & Execution Layer...";
    
    try {
        // Setup prompt to match the Development Layer functionality
        const developmentPrompt = `
        You are the Development & Execution Layer of the Hierarchical AI Collaboration Framework.
        Your role is to generate fully functional code based on structured inputs.
        
        Implement frontend and backend components.
        Ensure API and database integration.
        Write clean, modular, and scalable code.
        
        Technical Roadmap: ${input}
        
        Generate the full implementation code based on this technical roadmap.
        Include both frontend and backend code as needed.
        Structure your response so the code can be used directly in a production environment.
        `;
        
        const response = await puter.ai.chat(developmentPrompt);
        
        // Display the formatted result
        document.getElementById('develop-output').innerText = formatCodeResponse(response);
        
        // Store the result for the next layer
        projectData.developmentCode = response;
        
        // Move to the next layer in the hierarchy
        await optimizeCode(response);
    } catch (error) {
        document.getElementById('develop-output').innerText = "Error in Development Layer: " + error.message;
        console.error("Error developing code:", error);
    }
}

/**
 * Layer 4: Debugging, Optimization & Security Layer
 * Uses model emulation similar to gpt-4o
 * Reviews, debugs, and optimizes generated code
 */
async function optimizeCode(input) {
    document.getElementById('optimize-output').innerText = "Processing with Debugging, Optimization & Security Layer...";
    
    try {
        // Setup prompt to match the Optimization Layer functionality
        const optimizationPrompt = `
        You are the Debugging, Optimization & Security Layer of the Hierarchical AI Collaboration Framework.
        Your role is to review, debug, and optimize generated code.
        
        Identify syntax errors and logical inconsistencies.
        Add security features (e.g., input validation, authentication enforcement).
        Refactor inefficient code for performance improvements.
        
        Generated Code: ${input}
        
        Review and improve this code with a focus on:
        1. Security (authentication, validation, protection against common attacks)
        2. Performance optimization
        3. Code quality and maintainability
        4. Error handling and edge cases
        
        Provide the improved code in a format that can be directly implemented.
        `;
        
        const response = await puter.ai.chat(optimizationPrompt);
        
        // Display the formatted result
        document.getElementById('optimize-output').innerText = formatCodeResponse(response);
        
        // Store the result for the next layer
        projectData.optimizedCode = response;
        
        // Finalize the output
        await finalizeOutput(response);
    } catch (error) {
        document.getElementById('optimize-output').innerText = "Error in Optimization Layer: " + error.message;
        console.error("Error optimizing code:", error);
    }
}

/**
 * Layer 5: Final Output to User
 * Processes, formats, and prepares the final code for download
 */
async function finalizeOutput(input) {
    document.getElementById('final-output').innerText = "Preparing final output...";
    
    try {
        // Parse the code into structured files
        let files = extractFilesFromCode(input);
        
        // Store files for download
        localStorage.setItem('projectFiles', JSON.stringify(files));
        
        // Store in project data
        projectData.finalOutput = files;
        
        // Display success message
        document.getElementById('final-output').innerText = 
            `Project ready for download!\n${files.length} file(s) generated.\nUse the 'Download Project' button to save the full implementation.`;
    } catch (error) {
        document.getElementById('final-output').innerText = "Error in Final Output Generation: " + error.message;
        console.error("Error finalizing output:", error);
    }
}

/**
 * Generates download for project files
 * Handles both single file and multi-file (zip) downloads
 */
function generateDownload() {
    const files = JSON.parse(localStorage.getItem('projectFiles'));
    if (!files || files.length === 0) {
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

/**
 * Helper function to format JSON responses for better display
 */
function formatJsonResponse(response) {
    try {
        // Try to parse as JSON first
        const jsonObj = JSON.parse(response);
        return JSON.stringify(jsonObj, null, 2);
    } catch (e) {
        // If not valid JSON, try to extract JSON from text
        const jsonMatch = response.match(/```json\s*([\s\S]*?)\s*```/);
        if (jsonMatch && jsonMatch[1]) {
            try {
                const extractedJson = JSON.parse(jsonMatch[1]);
                return JSON.stringify(extractedJson, null, 2);
            } catch (err) {
                // Return original text if extraction fails
                return response;
            }
        }
        // Return original text if no JSON extraction was possible
        return response;
    }
}

/**
 * Helper function to format code responses for better display
 */
function formatCodeResponse(response) {
    // Return the original text with its formatting
    return response;
}

/**
 * Helper function to extract files from code response
 */
function extractFilesFromCode(response) {
    try {
        // First try to parse as JSON directly
        const jsonObj = JSON.parse(response);
        if (Array.isArray(jsonObj) || (jsonObj.files && Array.isArray(jsonObj.files))) {
            return Array.isArray(jsonObj) ? jsonObj : jsonObj.files;
        }
    } catch (e) {
        // Not a JSON, try to extract file information from markdown code blocks
        const files = [];
        const codeBlockRegex = /```(?:(\w+)\n)?([\s\S]*?)```/g;
        const filenameRegex = /(?:^|\n)(?:File|Filename):\s*([^\n]+)/i;
        
        let wholeText = response;
        let filenameMatch = filenameRegex.exec(wholeText);
        
        let match;
        while ((match = codeBlockRegex.exec(response)) !== null) {
            const lang = match[1] || '';
            const content = match[2];
            
            // Check if there's a filename comment before this code block
            let filename = 'unknown_file';
            
            // Determine file type based on language
            if (lang === 'js' || lang === 'javascript') {
                filename = 'script.js';
            } else if (lang === 'html') {
                filename = 'index.html';
            } else if (lang === 'css') {
                filename = 'style.css';
            } else if (lang === 'py' || lang === 'python') {
                filename = 'script.py';
            } else if (lang === 'json') {
                filename = 'data.json';
            }
            
            // Look for filename in proximity to this code block
            const prevText = response.substring(0, match.index);
            const prevLines = prevText.split('\n').slice(-5).join('\n');
            const filenameInProximity = /(?:file|filename):\s*([^\n]+)/i.exec(prevLines);
            
            if (filenameInProximity) {
                filename = filenameInProximity[1].trim();
            }
            
            files.push({
                name: filename,
                content: content
            });
        }
        
        // If no files were extracted, create a single file with the entire response
        if (files.length === 0) {
            files.push({
                name: 'HACF_Project.txt',
                content: response
            });
        }
        
        return files;
    }
    
    // Default fallback if parsing fails
    return [{
        name: 'HACF_Project.txt',
        content: response
    }];
}
