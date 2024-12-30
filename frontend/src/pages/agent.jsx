import { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";
import * as FaIcons from "react-icons/fa";
import { FiRefreshCcw, FiMaximize2 } from "react-icons/fi";
import { IoClose } from "react-icons/io5";
import "./styles/agent.css"
import { motion, AnimatePresence } from "framer-motion";
import Markdown from 'react-markdown'

export const Agent = ({ selectedActions, behaviorText }) => {
    const [socket, setSocket] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState("");
    const [attachedImages, setAttachedImages] = useState([]);
    const [isWaiting, setIsWaiting] = useState(false);
    const messagesContainerRef = useRef(null);
    const fileInputRef = useRef(null);
    const [browsingURL, setBrowsingURL] = useState(null);
    const [isPopupMinimized, setIsPopupMinimized] = useState(false);
    const [popupPosition, setPopupPosition] = useState({ x: 100, y: 100 });

    const [isSearching, setIsSearching] = useState(false);
    const [searchingLogos, setSearchingLogos] = useState([]);

    const inputRef = useRef(null);

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
            setIsWaiting(false);
            setMessages(prev => [...prev, {
                text: data.message,
                type: 'agent'
            }]);
        });        

        newSocket.on('reply_stream', (data) => {
            setIsWaiting(false);
            setMessages(prev => {
                const newMessages = [...prev];
                if (newMessages.length > 0 && newMessages[newMessages.length - 1].type === 'agent') {
                    newMessages[newMessages.length - 1] = {
                        text: data.message,
                        type: 'agent'
                    };
                } else {
                    newMessages.push({
                        text: data.message,
                        type: 'agent'
                    });
                }
                return newMessages;
            });
        });  

        newSocket.on('browsing_url', (data) => {
            setBrowsingURL(data.url);
        });     

        newSocket.on('searching', (data) => {
            console.log("SEARCHING: ", data);
            setIsSearching(data);
        });

        newSocket.on('searching_logo', (data) => {
            console.log("SEARCHING LOGO: ", data);
            setSearchingLogos(prev => [...prev, data.url]);
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
    }, [messages, isWaiting]);

    useEffect(() => {
        const handleKeyPress = (e) => {
            if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault();
                inputRef.current?.focus();
            }
        };

        document.addEventListener('keydown', handleKeyPress);
        return () => document.removeEventListener('keydown', handleKeyPress);
    }, []);

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
                selectedActions,
                behaviorText
            };

            setMessages(prev => [...prev, newMessage]);
            setIsWaiting(true);
            
            socket.emit('user_message', newMessage);

            setInputMessage("");
            setIsSearching(false);
            setSearchingLogos([]);
            setAttachedImages([]);
        }
    };

    const resetMessages = () => {
        socket.emit('reset');
        setMessages([]);
        setIsWaiting(false);
        setBrowsingURL(null);
    };

    const handleKeyPress = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className='agent_container'>
            <AnimatePresence>
                {browsingURL && (
                    isPopupMinimized ? (
                        <motion.div
                            className="browsing-tab"
                            initial={{ y: -100 }}
                            animate={{ y: 0 }}
                            exit={{ y: -100 }}
                            style={{
                                position: "fixed",
                                top: 0,
                                right: "20px",
                                background: "white",
                                borderRadius: "0 0 8px 8px",
                                boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                                padding: "8px 16px",
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                cursor: "pointer",
                                zIndex: 1000,
                            }}
                            onClick={() => setIsPopupMinimized(false)}
                        >
                            <span>Browsing...</span>
                            <FiMaximize2 />
                        </motion.div>
                    ) : (
                        <motion.div
                            className="browsing-popup"
                            initial={{ scale: 0 }}
                            animate={{
                                scale: 1,
                                x: popupPosition.x,
                                y: popupPosition.y
                            }}
                            exit={{ scale: 0 }}
                            drag
                            dragMomentum={false}
                            onDragEnd={(_, info) => {
                                setPopupPosition({
                                    x: popupPosition.x + info.offset.x,
                                    y: popupPosition.y + info.offset.y
                                });
                            }}
                            style={{
                                aspectRatio: "16/9",
                                width: "600px",
                                position: "fixed",
                                zIndex: 1000,
                                background: "white",
                                borderRadius: "8px",
                                boxShadow: "0 4px 6px rgba(0,0,0,0.1)"
                            }}
                        >
                            <div className="popup-header" style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                                <button onClick={() => setIsPopupMinimized(true)}>
                                    Minimize
                                </button>
                            </div>
                            <div className="popup-content" style={{ height: "calc(100% - 40px)" }}>
                                <iframe
                                    src={browsingURL}
                                    sandbox="allow-same-origin allow-scripts allow-forms"
                                    allow="clipboard-read; clipboard-write"
                                    style={{ pointerEvents: "none", width: "100%", height: "100%" }}
                                />
                            </div>
                        </motion.div>
                    )
                )}
            </AnimatePresence>

            <div className="chat_holder">

                <div className="chat_header">

                    <div className="logo">
                        <img src="/logo.png" alt="logo" className="logo_image" />
                    </div>

                    <div className="reset_button">
                        <FiRefreshCcw onClick={resetMessages} style={{ cursor: 'pointer' }} />
                    </div>
                </div>

                <div className="chat_messages" ref={messagesContainerRef}>
                    {messages.map((message, index) => (
                        <div key={index} className={`chat_message ${message.type === 'agent' ? 'received' : 'sent'}`}>
                            <div className="message">
                                <pre style={{whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0}}>
                                    <Markdown>{message.text?.trim().replace(/^['"]|['"]$/g, '')}</Markdown>
                                </pre>
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
                    {isWaiting && (
                        isSearching ? (
                            <div className="searching_message_holder">
                                {searchingLogos.length > 0 && (
                                    <div className="searching_logos" style={{ marginRight: '0.5rem' }}>
                                        {searchingLogos.map((logo, index) => (
                                            <motion.img 
                                                key={index} 
                                                src={logo} 
                                                alt="searching"
                                                className="searching_logo"
                                                initial={{ scale: 0, opacity: 0 }}
                                                animate={{ scale: 1, opacity: 1 }}
                                                transition={{ duration: 0.3, delay: index * 0.1 }}
                                                style={{
                                                    width: '24px',
                                                    height: '24px',
                                                    borderRadius: '50%',
                                                    objectFit: 'cover',
                                                    marginLeft: index !== 0 ? '-8px' : '0',
                                                    border: '2px solid white',
                                                    backgroundColor: 'white',
                                                }}
                                            />
                                        ))}
                                    </div>
                                )}
                                <div className="working-message">
                                    Searching...
                                </div>
                            </div>
                        ) : (
                            <div className="working-message">
                                Working...
                            </div>
                        )                        
                    )}
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
                            ref={inputRef}
                            className="chat_input_field"
                            placeholder="Talk to your assistant!"
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
    );
};