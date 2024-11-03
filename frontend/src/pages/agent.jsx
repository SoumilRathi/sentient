import { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";
import * as FaIcons from "react-icons/fa";
import { FiRefreshCcw } from "react-icons/fi";
import { IoClose } from "react-icons/io5";
import "./styles/agent.css"
import { LiveTranscriptionEvents, createClient } from "@deepgram/sdk";


export const Agent = ({ agentId, selectedActions, behaviorText, onUpdateAgent }) => {
    const [socket, setSocket] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState("");
    const [attachedImages, setAttachedImages] = useState([]);
    const [isWaiting, setIsWaiting] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const messagesContainerRef = useRef(null);
    const fileInputRef = useRef(null);
    const deepgramSocketRef = useRef(null);
    const keepAliveRef = useRef(null);
    const messageBufferRef = useRef([]);

    let deepgramClient;
    const deepgramKey = import.meta.env.VITE_DEEPGRAM_KEY;
    deepgramClient = createClient(deepgramKey, {
        global: { fetch: { options: { proxy: { url: "http://localhost:5174" } } } },
    });
    const setupDeepgram = () => {
        let full_speech = "";
        let transcriptTimeout;
        const timeoutDuration = 2500;

        const deepgramSocket = deepgramClient.listen.live({
            language: "en",
            punctuate: true,
            smart_format: true,
            model: "nova-2",
            interim_results: true,
            utterance_end_ms: "1000",
            vad_events: true,
            endpointing: 300
        });

        deepgramSocketRef.current = deepgramSocket;
        let isDeepgramOpen = false;

        if (keepAliveRef.current) clearInterval(keepAliveRef.current);
        keepAliveRef.current = setInterval(() => {
            deepgramSocket.keepAlive();
        }, 8000);

        const resetTranscriptTimeout = () => {
            clearTimeout(transcriptTimeout);
            transcriptTimeout = setTimeout(() => {
                if (full_speech.length > 0) {
                    setInputMessage(prev => prev + full_speech);
                    full_speech = "";
                }
            }, timeoutDuration);
        };

        deepgramSocket.on("open", () => {
            isDeepgramOpen = true;
            // while (messageBufferRef.current.length > 0 && isDeepgramOpen) {
            //     console.log("SENDING MESSAGE BUFFER: ", messageBufferRef.current);
            //     const message = messageBufferRef.current.shift();
            //     deepgramSocket.send(message);
            // }
        });

        deepgramSocket.addListener(LiveTranscriptionEvents.Transcript, (data) => {
            const transcript = data.channel.alternatives[0].transcript;
            
            if (data.is_final) {
                full_speech += transcript;
                setInputMessage(prev => prev + transcript + " ");
            }
            resetTranscriptTimeout();
        });

        deepgramSocket.addListener(LiveTranscriptionEvents.UtteranceEnd, () => {
            if (full_speech.length > 0) {
                setInputMessage(prev => prev + full_speech);
                full_speech = "";
            }
        });

        deepgramSocket.addListener(LiveTranscriptionEvents.Close, async () => {
            isDeepgramOpen = false;
            clearInterval(keepAliveRef.current);
            deepgramSocketRef.current = null;
            setIsRecording(false);
        });

        deepgramSocket.addListener(LiveTranscriptionEvents.Error, async (error) => {
            console.error("Network error:", error);
            setIsRecording(false);
        });
    };

    const [microphone, setMicrophone] = useState(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setIsRecording(true);
            setupDeepgram();

            const mediaRecorder = new MediaRecorder(stream);
            setMicrophone(mediaRecorder);
            mediaRecorder.addEventListener("dataavailable", event => {
                if (deepgramSocketRef.current?.getReadyState() === 1) {
                    deepgramSocketRef.current.send(event.data);
                } else {
                    messageBufferRef.current.push(event.data);
                }
            });

            mediaRecorder.start(250);
        } catch (err) {
            console.error("Error accessing microphone:", err);
        }
    };

    const stopRecording = () => {
        setIsRecording(false);
        if (microphone) {
            microphone.stop();
        }
        if (deepgramSocketRef.current) {
            deepgramSocketRef.current.finish();
        }
    };

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
            console.log("RECEIVED MESSAGE: ", data.message);
            setMessages(prevMessages => [...prevMessages, {
                text: data.message,
                type: 'agent'
            }]);
            localStorage.setItem(`messages-${agentId}`, JSON.stringify([...messages, {
                text: data.message,
                type: 'agent'
            }]));
        });        
    
        setSocket(newSocket);
    
        return () => {
            newSocket.close();
        };
    }, [agentId]);

    useEffect(() => {
        if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
    }, [messages, isWaiting]);

    useEffect(() => {
        // Load messages from localStorage
        const savedMessages = localStorage.getItem(`messages-${agentId}`);
        if (savedMessages) {
            setMessages(JSON.parse(savedMessages));
        }
    }, [agentId]);

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

            setMessages(prevMessages => [...prevMessages, newMessage]);
            localStorage.setItem(`messages-${agentId}`, JSON.stringify([...messages, newMessage]));
            setIsWaiting(true);
            
            socket.emit('user_message', newMessage);

            setInputMessage("");
            setAttachedImages([]);
        }
    };

    const resetMessages = () => {
        socket.emit('reset');
        setMessages([]);
        localStorage.setItem(`messages-${agentId}`, JSON.stringify([]));
        setIsWaiting(false);
    };

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
                                {message.text?.trim().replace(/^['"]|['"]$/g, '')}
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
                        <div className="working-message">
                            Working...
                        </div>
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
                        <FaIcons.FaMicrophone
                            onClick={isRecording ? stopRecording : startRecording}
                            style={{ 
                                cursor: 'pointer', 
                                marginRight: '0.5rem',
                                color: isRecording ? 'red' : 'inherit'
                            }}
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