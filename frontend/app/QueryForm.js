//components/QueryForm.js

"use client"; 

import React, { useState, useRef, useEffect } from 'react';
import './QueryForm.css'; 


function QueryForm() {
    //track getter and setter states
    const[query, setQuery] = useState('');
    const[response, setResponse] = useState('');
    const[loading, setLoading] = useState(false);
    const[messages, setMessages] = useState([]);
    const chatContainerRef = useRef(null);

    //Wait for response before continuing
    const handleSubmit = async (e) => {
        //Cancel event
        e.preventDefault();
        if(!query) return; 

        //Add user's query to the chat
        setMessages(prev => [...prev, {text: query, type: 'user'}]);
        setQuery(''); 
        setLoading(true); 

        try
        {  
            //Send asynch HTTP requests to REST endpoint
            const response = await fetch('http://localhost:5000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({query})
            }); 
           
            if (!response.body || !response.body.getReader) {
                const data = await response.json();
                setMessages(prev => [...prev, { text: data.response, type: 'bot' }]);
                return;
            }
    
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
    
            let done = false;
            let fullResponse = '';
    
            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                let chunk = decoder.decode(value);

                chunk = chunk.replace(/data:/g,''); 

                fullResponse += chunk;
            }

            //Add the full response in singular bubble
            setMessages(prev => [...prev, {text: fullResponse.replaceAll("\\s{2,}", " ").trim(), type: 'bot'}]);
        } catch(error)
        {
            console.error('Error fetching the response:', error.response ? error.response.data : error.message);
            setResponse('There was an error processing your request.');
        } finally 
        {
            setLoading(false);
        }
    }; 

    useEffect(() => 
        {
        if(chatContainerRef.current)
        {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
        }, [messages,loading]); 

    return(
        <div className="chatbot-ui">
            <div className = 'chatbot-container' ref={chatContainerRef}>
                    {messages.map((msg, index) => (
                        <div key={index} className={`message ${msg.type}`}>
                            {msg.text}
                        </div>
                    ))}
                    {loading && (
                            <div className="chatbot-loading">
                                <div className="loading-dot"></div>
                                <div className="loading-dot"></div>
                                <div className="loading-dot"></div>
                            </div> 
                    )}
                <div className='chatbot-content'>
                    <form onSubmit={handleSubmit} className='chatbot-form'>
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Type your message..."
                            required
                        />
                        <button type="submit">Send</button>
                    </form>
                </div>
            </div>
        </div>

        
    ); 
}

export default QueryForm; 