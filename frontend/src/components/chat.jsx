import { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";
import * as FaIcons from "react-icons/fa";
import { FiRefreshCcw } from "react-icons/fi";
import "./styles/chat.css";

export const Chat = ({messages, setMessages, socket, setSocket, onMessage}) => {
    const [inputMessage, setInputMessage] = useState("");
    const messagesContainerRef = useRef(null);
    

    useEffect(() => {
        if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
    }, [messages]);

    const sendMessage = () => {
        if (inputMessage.trim() !== "" && socket) {
            const newMessage = inputMessage.trim();
            
            onMessage(newMessage);
        }
    };

    const resetMessages = () => {
        socket.emit('reset');
        setMessages([]);
    }

    const handleKeyPress = (e) => {
        if (e.key === "Enter") {
            sendMessage(inputMessage);
            setInputMessage("");
        }
    };

    return (
        <div className="chat_holder">

            <div className="reset_button">
                <FiRefreshCcw onClick={resetMessages} style={{ cursor: 'pointer' }} />
            </div>

            <div className="chat_messages" ref={messagesContainerRef}>
                {messages.map((message, index) => (
                    <div key={index} className={`chat_message ${message.type === 'agent' ? 'received' : 'sent'}`}>
                        <div className="message">
                            {message.text.replace(/^['"]|['"]$/g, '')}
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
    )
}