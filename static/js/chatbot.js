// Chatbot functionality with Puter.js integration
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Load previous conversation if it exists
    loadPreviousConversation();
    
    // Function to load the previous conversation from the server
    async function loadPreviousConversation() {
        try {
            const response = await fetch('/get_conversation');
            const data = await response.json();
            
            if (data.conversation && data.conversation.length > 0) {
                data.conversation.forEach(msg => {
                    const isUser = msg.role === 'user';
                    addMessage(msg.content, isUser);
                });
            }
        } catch (error) {
            console.error('Error loading previous conversation:', error);
        }
    }
    
    // Function to add a message to the chat container
    function addMessage(message, isUser = false) {
        const messageRow = document.createElement('div');
        messageRow.className = 'message-row';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'message user-message' : 'message bot-message';
        
        // If the message contains code blocks, format them
        const formattedMessage = formatMessage(message);
        messageDiv.innerHTML = formattedMessage;
        
        messageRow.appendChild(messageDiv);
        chatContainer.appendChild(messageRow);
        
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
                    let code = part;
                    // Check if the part starts with a language identifier (e.g., 'javascript')
                    const languageMatch = part.match(/^([a-zA-Z0-9]+)\n/);
                    if (languageMatch) {
                        // Remove the language identifier from the code
                        code = part.substring(languageMatch[0].length);
                    }
                    formatted += `<pre><code>${code}</code></pre>`;
                }
            });
            
            return formatted;
        }
        
        // If no code blocks, just replace new lines with <br>
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
    
    // Function to send message to the chatbot
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
            // Check for special commands
            let response;
            
            if (message.toLowerCase() === '/clear') {
                // Clear the conversation
                await fetch('/clear_conversation', { method: 'POST' });
                chatContainer.innerHTML = '';
                addMessage("Conversation cleared. How can I help you today?");
                hideTypingIndicator();
                return;
            } else if (message.toLowerCase().startsWith('/hacf')) {
                // Parse command to use in HACF workflow
                const hacfCommand = message.substring(6).trim();
                
                // Add message to chat about using HACF
                response = "I'll process this in the HACF framework. Please check the project builder panel on the right.";
                
                // Fill in the task input and trigger the HACF process
                document.getElementById('task-input').value = hacfCommand;
                
                // Use setTimeout to allow the UI to update before starting the HACF process
                setTimeout(() => {
                    try {
                        defineTask(); // Call the HACF function
                    } catch (err) {
                        console.error("Error in HACF process:", err);
                    }
                }, 100);
                
            } else {
                // Regular message - send to Puter.js AI
                if (typeof puter !== 'undefined' && typeof puter.ai !== 'undefined' && typeof puter.ai.chat === 'function') {
                    response = await puter.ai.chat(message);
                } else {
                    // Fallback if Puter.js is not available
                    response = "I'm sorry, but I can't access the AI service right now. Please check that you've authenticated with Puter.js by clicking the button in the navbar.";
                }
            }
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add bot response to chat
            addMessage(response);
            
            // Send the conversation to the server for logging
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message, response: response }),
            });
        } catch (error) {
            // Hide typing indicator
            hideTypingIndicator();
            
            if (error.code === 'auth_canceled') {
                // Handle authentication cancellation gracefully
                addMessage("Authentication was canceled. Please try again when you're ready to authenticate with Puter.js.");
            } else {
                // Display other error messages
                addMessage(`Sorry, there was an error: ${error.message}`);
            }
            console.error('Chat error:', error);
        }
    }
    
    // Add a clear button to the chat
    const clearButton = document.createElement('button');
    clearButton.textContent = 'Clear Chat';
    clearButton.className = 'btn btn-sm btn-outline-danger mt-2';
    clearButton.onclick = async function() {
        await fetch('/clear_conversation', { method: 'POST' });
        chatContainer.innerHTML = '';
        addMessage("Conversation cleared. How can I help you today?");
    };
    
    // Add the clear button below the chat container
    chatContainer.parentNode.insertBefore(clearButton, chatContainer.nextSibling);
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Add help button
    const helpButton = document.createElement('button');
    helpButton.textContent = 'Chat Help';
    helpButton.className = 'btn btn-sm btn-outline-info mt-2 ms-2';
    helpButton.onclick = function() {
        addMessage(`
**Chat Commands**:
- Type normally to chat with the AI
- Use \`/clear\` to clear the conversation
- Use \`/hacf [your task]\` to run a task through the HACF framework

**About HACF**:
The Hierarchical AI Collaboration Framework processes your task through 4 stages:
1. Task Definition & Planning
2. Refinement & Base Structure
3. Development & Execution  
4. Optimization & Security
        `, false);
    };
    
    // Add the help button next to the clear button
    clearButton.parentNode.insertBefore(helpButton, clearButton.nextSibling);
    
    // Focus the input field when the page loads
    userInput.focus();
});
