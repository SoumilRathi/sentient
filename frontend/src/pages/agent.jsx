import { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";
import * as FaIcons from "react-icons/fa";
import { FiRefreshCcw } from "react-icons/fi";
import { IoClose } from "react-icons/io5";
import { BsFileEarmarkText } from "react-icons/bs";
import "./styles/agent.css"

export const Agent = () => {
    const [socket, setSocket] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState("");
    const [attachments, setAttachments] = useState([]);
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

    const handleFileUpload = (e) => {
        const files = Array.from(e.target.files);
        const newAttachments = files.map(file => ({
            file,
            preview: file.type.startsWith('image/') 
                ? URL.createObjectURL(file) 
                : null,
            type: file.type.startsWith('image/') ? 'image' : 'document',
            name: file.name
        }));
        
        setAttachments(prev => [...prev, ...newAttachments]);
    };

    const removeAttachment = (index) => {
        setAttachments(prev => {
            const newAttachments = [...prev];
            if (newAttachments[index].preview) {
                URL.revokeObjectURL(newAttachments[index].preview);
            }
            newAttachments.splice(index, 1);
            return newAttachments;
        });
    };

    const sendMessage = () => {
        if ((inputMessage.trim() !== "" || attachments.length > 0) && socket) {
            // Create FormData for files
            const formData = new FormData();
            attachments.forEach((attachment, index) => {
                formData.append('files', attachment.file);
            });
            formData.append('message', inputMessage.trim());

            // Add message to chat
            setMessages(prev => [...prev, {
                text: inputMessage.trim(),
                type: 'user',
                attachments: attachments.map(att => ({
                    type: att.type,
                    preview: att.preview,
                    name: att.name
                }))
            }]);
            
            // Send message and files to server
            socket.emit('message', { 
                message: inputMessage.trim(),
                files: formData
            });

            // Clear input and attachments
            setInputMessage("");
            setAttachments([]);
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

    console.log(messages);

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
                                {message.attachments && message.attachments.length > 0 && (
                                    <div className="attachments_preview">
                                        {message.attachments.map((att, attIndex) => (
                                            <div key={attIndex} className="attachment">
                                                {att.type === 'image' ? (
                                                    <img src={att.preview} alt="attachment" />
                                                ) : (
                                                    <div className="document_preview">
                                                        <BsFileEarmarkText />
                                                        <span>{att.name}</span>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="chat_input_holder">
                    {attachments.length > 0 && (
                        <div className="attachments_preview">
                            {attachments.map((attachment, index) => (
                                <div key={index} className="attachment">
                                    {attachment.type === 'image' ? (
                                        <div className="image_preview">
                                            <img src={attachment.preview} alt="preview" />
                                            <button 
                                                className="remove_attachment"
                                                onClick={() => removeAttachment(index)}
                                            >
                                                <IoClose />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="document_preview">
                                            <BsFileEarmarkText />
                                            <span>{attachment.name}</span>
                                            <button 
                                                className="remove_attachment"
                                                onClick={() => removeAttachment(index)}
                                            >
                                                <IoClose />
                                            </button>
                                        </div>
                                    )}
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
                            accept="image/*,.pdf,.doc,.docx,.txt,.js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.cs,.html,.css,.json,.xml,.yaml,.yml,.md"
                        />
                        <FaIcons.FaPaperPlane onClick={sendMessage} style={{ cursor: 'pointer' }} />
                    </div>
                </div>
            </div>
        </div>
    )
}