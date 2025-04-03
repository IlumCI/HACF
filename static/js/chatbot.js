// Enhanced Chatbot functionality with Puter.js integration
// Implements the HACF (Hierarchical AI Collaboration Framework) principles
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Conversation history storage
    let conversationHistory = [];
    
    // Function to add a message to the chat container
    function addMessage(message, isUser = false, metadata = {}) {
        const messageRow = document.createElement('div');
        messageRow.className = 'message-row';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'message user-message' : 'message bot-message';
        
        // If the message contains code blocks, format them
        const formattedMessage = formatMessage(message);
        messageDiv.innerHTML = formattedMessage;
        
        // If there's a layer metadata, add a subtle indicator
        if (metadata.layer) {
            const layerBadge = document.createElement('small');
            layerBadge.className = 'layer-badge';
            layerBadge.textContent = `HACF Layer: ${metadata.layer}`;
            layerBadge.style.display = 'block';
            layerBadge.style.fontSize = '0.75em';
            layerBadge.style.opacity = '0.7';
            layerBadge.style.marginTop = '5px';
            layerBadge.style.textAlign = isUser ? 'right' : 'left';
            messageDiv.appendChild(layerBadge);
        }
        
        messageRow.appendChild(messageDiv);
        chatContainer.appendChild(messageRow);
        
        // Store in conversation history
        conversationHistory.push({
            role: isUser ? 'user' : 'assistant',
            content: message,
            metadata: metadata
        });
        
        // Scroll to the bottom of the chat container
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Function to format messages with code blocks
    function formatMessage(message) {
        // Check if message contains code blocks (```code```)
        if (message.includes('```')) {
            let formatted = '';
            let inCodeBlock = false;
            
            // Split by code block markers
            const parts = message.split('```');
            
            parts.forEach((part, index) => {
                if (index % 2 === 0) {
                    // Regular text - replace new lines with <br>
                    formatted += part.replace(/\n/g, '<br>');
                } else {
                    // Code block - wrap in pre and code tags
                    formatted += `<pre><code>${part}</code></pre>`;
                }
            });
            
            return formatted;
        }
        
        // Handle JSON objects by pretty-printing them
        try {
            const jsonObj = JSON.parse(message);
            return `<pre>${JSON.stringify(jsonObj, null, 2)}</pre>`;
        } catch (e) {
            // Not valid JSON, continue with normal formatting
        }
        
        // If no code blocks or JSON, just replace new lines with <br>
        return message.replace(/\n/g, '<br>');
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        typingIndicator.style.display = 'flex';
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Function to hide typing indicator
    function hideTypingIndicator() {
        typingIndicator.style.display = 'none';
    }
    
    /**
     * HACF-enhanced chat processing
     * Routes messages through the appropriate HACF layer based on content
     */
    async function processThroughHACF(message) {
        // Detect if the message is a command for a specific HACF layer
        const layerCommands = {
            '/task': 1,
            '/refine': 2,
            '/develop': 3,
            '/optimize': 4
        };
        
        // Check for layer command at start of message
        const commandMatch = message.match(/^(\/\w+)\s+(.*)/);
        if (commandMatch) {
            const command = commandMatch[1];
            const actualMessage = commandMatch[2];
            
            const layer = layerCommands[command];
            if (layer) {
                // Process through specific HACF layer
                return await processLayerRequest(actualMessage, layer);
            }
        }
        
        // Default: process as a standard chat message
        return await puter.ai.chat(message);
    }
    
    /**
     * Process a message through a specific HACF layer
     */
    async function processLayerRequest(message, layer) {
        let prompt = '';
        let layerName = '';
        
        switch(layer) {
            case 1:
                layerName = "Task Definition & Planning";
                prompt = `
                You are the Task Definition & Planning Layer of the Hierarchical AI Collaboration Framework.
                Your role is to convert user requests into structured plans and well-formed prompts.
                
                Analyze this user request and structure it into an actionable plan.
                Output a formatted JSON containing required features and project structure.
                
                User Request: ${message}
                
                Format your response as a well-structured JSON with Project, Features, and Next_Prompt fields.
                `;
                break;
                
            case 2:
                layerName = "Refinement & Base Structure";
                prompt = `
                You are the Refinement & Base Structure Layer of the Hierarchical AI Collaboration Framework.
                Your role is to convert high-level plans into technical roadmaps with base code structure.
                
                Assign specific frameworks, libraries, and data models.
                Create an outline for frontend, backend, and database.
                Ensure project feasibility and consistency.
                
                User Input: ${message}
                
                Format your response as a well-structured JSON with specific technical details for Frontend, Backend, Database, 
                and include a Next_Prompt field for the Development Layer.
                `;
                break;
                
            case 3:
                layerName = "Development & Execution";
                prompt = `
                You are the Development & Execution Layer of the Hierarchical AI Collaboration Framework.
                Your role is to generate fully functional code based on structured inputs.
                
                Implement frontend and backend components.
                Ensure API and database integration.
                Write clean, modular, and scalable code.
                
                Technical Specification: ${message}
                
                Generate the full implementation code based on this specification.
                Include both frontend and backend code as needed.
                Structure your response so the code can be used directly in a production environment.
                `;
                break;
                
            case 4:
                layerName = "Debugging, Optimization & Security";
                prompt = `
                You are the Debugging, Optimization & Security Layer of the Hierarchical AI Collaboration Framework.
                Your role is to review, debug, and optimize generated code.
                
                Identify syntax errors and logical inconsistencies.
                Add security features (e.g., input validation, authentication enforcement).
                Refactor inefficient code for performance improvements.
                
                Code to Improve: ${message}
                
                Review and improve this code with a focus on:
                1. Security (authentication, validation, protection against common attacks)
                2. Performance optimization
                3. Code quality and maintainability
                4. Error handling and edge cases
                
                Provide the improved code in a format that can be directly implemented.
                `;
                break;
                
            default:
                // Should not get here, but just in case
                return await puter.ai.chat(message);
        }
        
        // Process through Puter.js AI with the layer-specific prompt
        const response = await puter.ai.chat(prompt);
        
        // Add layer metadata to response
        return {
            text: response,
            metadata: {
                layer: layerName,
                layerNumber: layer
            }
        };
    }
    
    // Main function to send message to the chatbot
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input field
        userInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        try {
            // Process through HACF framework
            const result = await processThroughHACF(message);
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Check if the response includes metadata (from HACF layers)
            if (result && typeof result === 'object' && result.text) {
                // Response from HACF layer
                addMessage(result.text, false, result.metadata);
            } else {
                // Standard response
                addMessage(result);
            }
            
            // Send the conversation to the server for logging
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message, 
                    response: typeof result === 'object' ? result.text : result,
                    metadata: typeof result === 'object' ? result.metadata : null
                }),
            });
        } catch (error) {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Display error message
            addMessage(`Sorry, there was an error: ${error.message}`);
            console.error('Chat error:', error);
        }
    }
    
    // Function to clear the chat history
    function clearChat() {
        // Clear the chat container
        while (chatContainer.firstChild) {
            chatContainer.removeChild(chatContainer.firstChild);
        }
        
        // Reset the conversation history
        conversationHistory = [];
        
        // Add welcome message
        addMessage("Hello! I'm your AI assistant powered by the Hierarchical AI Collaboration Framework. You can chat with me normally, or use these special commands:\n\n/task [description] - Define a task through the Planning Layer\n/refine [input] - Refine a structure through the Refinement Layer\n/develop [spec] - Generate code through the Development Layer\n/optimize [code] - Improve code through the Optimization Layer");
        
        // Clear from server
        fetch('/clear_conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
    }
    
    // Add welcome message
    addMessage("Hello! I'm your AI assistant powered by the Hierarchical AI Collaboration Framework. You can chat with me normally, or use these special commands:\n\n/task [description] - Define a task through the Planning Layer\n/refine [input] - Refine a structure through the Refinement Layer\n/develop [spec] - Generate code through the Development Layer\n/optimize [code] - Improve code through the Optimization Layer");
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Add clear button
    const chatHeader = document.querySelector('.card-header');
    if (chatHeader) {
        const clearButton = document.createElement('button');
        clearButton.className = 'btn btn-sm btn-outline-danger ms-2';
        clearButton.textContent = 'Clear Chat';
        clearButton.addEventListener('click', clearChat);
        
        // Find the h4 and append the button after it
        const headerTitle = chatHeader.querySelector('h4');
        if (headerTitle) {
            headerTitle.style.display = 'inline';
            headerTitle.after(clearButton);
        } else {
            chatHeader.appendChild(clearButton);
        }
    }
    
    // Focus the input field when the page loads
    userInput.focus();
});
