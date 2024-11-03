import { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";
import * as FaIcons from "react-icons/fa";
import { FiRefreshCcw } from "react-icons/fi";
import { IoClose } from "react-icons/io5";
import "./styles/agent.css"

export const Agent = () => {
    const [socket, setSocket] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState("");
    const [attachedImages, setAttachedImages] = useState([]);
    const messagesContainerRef = useRef(null);
    const fileInputRef = useRef(null);

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

    const handleFileUpload = (event) => {
        const files = Array.from(event.target.files);
        const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
        const validFiles = files.filter(file => allowedTypes.includes(file.type));

        if (validFiles.length !== files.length) {
            alert('Please upload only PNG, JPEG, GIF, or WebP images.');
        }

        Promise.all(validFiles.map(file => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        })).then(results => {
            setAttachedImages(prevImages => [...prevImages, ...results]);
        });
    };

    const removeAttachedImage = (index) => {
        setAttachedImages(prevImages => prevImages.filter((_, i) => i !== index));
    };

    const sendMessage = () => {
        if (inputMessage.trim() !== '' || attachedImages.length > 0) {
            const newMessage = {
                text: inputMessage.trim(),
                images: attachedImages,
                type: 'user',
                selectedActions: selectedActions,
                behaviorText: behaviorText
            };

            // Add to local messages
            setMessages(prev => [...prev, newMessage]);
            
            // Send via socket
            socket.emit('user_message', newMessage);

            // Clear inputs
            setInputMessage("");
            setAttachedImages([]);
        }
    };

    const resetMessages = () => {
        socket.emit('reset');
        setMessages([]);
    }

    const handleKeyPress = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
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
                </div>

                <div className="chat_messages" ref={messagesContainerRef}>
                    {messages.map((message, index) => (
                        <div key={index} className={`chat_message ${message.type === 'agent' ? 'received' : 'sent'}`}>
                            <div className="message">
                                {message.text?.replace(/^'|'$/g, '')}
                                {message.images && message.images.length > 0 && (
                                    <div className="images_preview">
                                        {message.images.map((image, imgIndex) => (
                                            <div key={imgIndex} className="attachment">
                                                <img src={image} alt="attachment" />
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="chat_input_holder">
                    {attachedImages.length > 0 && (
                        <div className="images_preview">
                            {attachedImages.map((image, index) => (
                                <div key={index} className="image_preview">
                                    <img src={image} alt="preview" />
                                    <button 
                                        className="remove_attachment"
                                        onClick={() => removeAttachedImage(index)}
                                    >
                                        <IoClose />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    <div className="chat_input">
                        <FaIcons.FaPaperclip 
                            onClick={() => fileInputRef.current.click()}
                            style={{ cursor: 'pointer', marginRight: '0.5rem' }}
                        />
                        <input
                            type="text"
                            className="chat_input_field"
                            placeholder="Message your agent..."
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                        />
                        <input
                            type="file"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            onChange={handleFileUpload}
                            multiple
                            accept=".png,.jpg,.jpeg,.gif,.webp"
                        />
                        <FaIcons.FaPaperPlane onClick={sendMessage} style={{ cursor: 'pointer' }} />
                    </div>
                </div>
            </div>
        </div>
    )
}