import { useState } from "react";
import { Chat } from "../components/chat"
import "./styles/agent.css"


export const Agent = () => {
    const [selectedActions, setSelectedActions] = useState(['reply']);

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
                                id="websearch"
                                checked={selectedActions.includes('websearch')}
                                onChange={() => handleActionChange('websearch')}
                            />
                            <label htmlFor="websearch">Websearch</label>
                        </div>
                        <div className="action">
                            <input 
                                type="checkbox" 
                                id="browser"
                                checked={selectedActions.includes('browser')}
                                onChange={() => handleActionChange('browser')}
                            />
                            <label htmlFor="browser">Use browser</label>
                        </div>
                    </div>
                </div>
                <div className='config_item behavior'>
                    <h1 className="config_item_title behavior_title">Behavior</h1>

                    <textarea className="config_item_content behavior_area" />
                </div>
            </div>
            <div className="chat">
                <Chat />
            </div>
        </div>
    )
}