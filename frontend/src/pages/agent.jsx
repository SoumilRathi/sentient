import { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";
import * as FaIcons from "react-icons/fa";
import { FiRefreshCcw } from "react-icons/fi";
import "./styles/agent.css"
// import "../components/styles/chat.css"
import { marked } from 'marked';

export const Agent = () => {
    const [socket, setSocket] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState("");
    const messagesContainerRef = useRef(null);

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

    useEffect(() => {
        if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
    }, [messages]);

    const sendMessage = () => {
        if (inputMessage.trim() !== "" && socket) {
            // Add user message to chat
            setMessages(prev => [...prev, {
                text: inputMessage.trim(),
                type: 'user'
            }]);
            
            // Send message to server
            socket.emit('message', { 
                message: inputMessage.trim(),
            });

            // Clear input
            setInputMessage("");
        }
    };

    const resetMessages = () => {
        socket.emit('reset');
        setMessages([]);
    }

    const handleKeyPress = (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    };

    return (
        <div className='agent_container'>
            <div className="chat_holder">

                <div className="chat_header">
                    <div className="reset_button">
                        <FiRefreshCcw onClick={resetMessages} style={{ cursor: 'pointer' }} />
                    </div>

                    {/* <div className="settings_button">
                        <FaIcons.FaCog style={{ cursor: 'pointer' }} />
                    </div> */}
                </div>
               

                <div className="chat_messages" ref={messagesContainerRef}>
                    {messages.map((message, index) => (
                        <div key={index} className={`chat_message ${message.type === 'agent' ? 'received' : 'sent'}`}>
                            <div className="message">
                                {message.type === 'agent' ? (
                                    <div dangerouslySetInnerHTML={{
                                        __html: marked.parse(message.text.replace(/^['"]|['"]$/g, ''))
                                    }} />
                                ) : (
                                    message.text.replace(/^['"]|['"]$/g, '')
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="chat_input_holder">
                    <div className="chat_input">
                        <input
                            type="text"
                            className="chat_input_field"
                            placeholder="Message your agent..."
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                        />
                        <FaIcons.FaPaperPlane onClick={sendMessage} style={{ cursor: 'pointer' }} />
                    </div>
                </div>
            </div>
        </div>
    )
} 