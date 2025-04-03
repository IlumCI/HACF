// Chatbot functionality with Puter.js integration
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    
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
                    formatted += `<pre><code>${part}</code></pre>`;
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
            // Send message to Puter.js AI directly from the client
            const response = await puter.ai.chat(message);
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add bot response to chat
            addMessage(response);
            
            // Send the conversation to the server for logging (optional)
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
            
            // Display error message
            addMessage(`Sorry, there was an error: ${error.message}`);
            console.error('Chat error:', error);
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Focus the input field when the page loads
    userInput.focus();
});
