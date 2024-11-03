import { useState } from "react";
import { Chat } from "../components/chat"
import "./styles/agent.css"
import { useEffect } from "react";
import { io } from "socket.io-client";


export const Agent = () => {
    const [selectedActions, setSelectedActions] = useState(['reply']);
    const [behavior, setBehavior] = useState('');
    const [socket, setSocket] = useState(null);
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        const newSocket = io('http://localhost:7777');
    
        newSocket.on('connect', () => {
            console.log('Connected to server');
        });
    
        newSocket.on('disconnect', () => {
            console.log('Disconnected from server');
        });
    
        newSocket.on('connect_error', (error) => {
            console.error('Connection error:', error);
        });

        newSocket.on('message', (data) => {
            console.log("Received agent message:", data);  // Debug print to verify
            setMessages(prev => [...prev, {
                text: data.message,
                type: 'agent'
            }]);
        });        
    
        setSocket(newSocket);
    
        return () => {
            newSocket.close();
        };
    }, []);


    const startAgent = () => {
        socket.emit('start', {
            selectedActions: selectedActions,
            behavior: behavior
        });
        setMessages([]);
    }

    const handleSendMessage = (message) => {
        // Add user message to chat
        setMessages(prev => [...prev, {
            text: message,
            type: 'user'
        }]);
        
        // Send message to server
        socket.emit('message', { 
            message: message,
        });
    }

    const resetAgent = () => {
        socket.emit('reset');
        setMessages([]);
    }

    const handleActionChange = (action) => {
        if (action === 'reply') {
            alert("You can't disable replying");
            return;
        }

        setSelectedActions(prev => {
            if (prev.includes(action)) {
                return prev.filter(a => a !== action);
            } else {
                return [...prev, action];
            }
        });
    };

    return (
        <div className='website_container'>
            <div className='config'>
                <div className='config_item actions'>
                    <h1 className="config_item_title actions_title">Actions</h1>

                    <div className="config_item_content actions_area">
                        <div className="action">
                            <input 
                                type="checkbox" 
                                id="reply"
                                checked={true}
                                onChange={() => handleActionChange('reply')}
                            />
                            <label htmlFor="reply">Reply</label>
                        </div>
                        <div className="action">
                            <input 
                                type="checkbox" 
                                id="email"
                                checked={selectedActions.includes('email')}
                                onChange={() => handleActionChange('email')}
                            />
                            <label htmlFor="email">Email</label>
                        </div>
                        <div className="action">
                            <input 
                                type="checkbox" 
                                id="search"
                                checked={selectedActions.includes('search')}
                                onChange={() => handleActionChange('search')}
                            />
                            <label htmlFor="search">Search</label>
                        </div>
                        <div className="action">
                            <input 
                                type="checkbox" 
                                id="browse"
                                checked={selectedActions.includes('browse')}
                                onChange={() => handleActionChange('browse')}
                            />
                            <label htmlFor="browse">Browse</label>
                        </div>
                       
                    </div>
                </div>
                <div className='config_item behavior'>
                    <h1 className="config_item_title behavior_title">Behavior</h1>

                    <textarea 
                        className="config_item_content behavior_area" 
                        value={behavior}
                        onChange={(e) => setBehavior(e.target.value)}
                    />
                </div>

                <div className="start_agent_container">
                    <button className="start_agent" onClick={startAgent}>
                        Start Agent
                    </button>
                </div>
            </div>
            <div className="chat">
                <Chat messages={messages} setMessages={setMessages} socket={socket} onMessage={handleSendMessage} />
            </div>
        </div>
    )
}