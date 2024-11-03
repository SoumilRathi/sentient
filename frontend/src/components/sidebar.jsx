import { Link } from 'react-router-dom';
import './styles/sidebar.css';
import logo from './sentient.png';
import Popup from 'reactjs-popup';
import * as FaIcons from 'react-icons/fa';
import { useState, useRef, useEffect } from 'react';

export const Sidebar = ({ 
    agents,
    currentAgent,
    selectedActions, 
    setSelectedActions, 
    behaviorText, 
    setBehaviorText,
    onCreateAgent,
    onUpdateAgent,
    onDeleteAgent,
    onSwitchAgent
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [editingName, setEditingName] = useState(null);
    const nameInputRef = useRef(null);

    useEffect(() => {
        if (editingName && nameInputRef.current) {
            nameInputRef.current.focus();
        }
    }, [editingName]);

    const toggleAction = (action) => {
        if (action === 'reply') {
            alert("Umm...you can't disable replying!");
            return;
        }
        const newActions = selectedActions.includes(action)
            ? selectedActions.filter(a => a !== action)
            : [...selectedActions, action];
        
        setSelectedActions(newActions);
        if (currentAgent) {
            onUpdateAgent(currentAgent.id, { selectedActions: newActions });
        }
    };

    const handleSave = () => {
        if (currentAgent) {
            onUpdateAgent(currentAgent.id, { 
                selectedActions,
                behaviorText
            });
        }
        setIsOpen(false);
    };

    const handleNameChange = (agentId, newName) => {
        onUpdateAgent(agentId, { name: newName });
        setEditingName(null);
    };

    const handleNameKeyPress = (e, agentId, newName) => {
        if (e.key === 'Enter') {
            handleNameChange(agentId, newName);
        }
    };

    return (
        <div className="sidebar">

            <div className='sidebar_top'>
                <img src={logo} alt="logo" />
                <div className="agents">
                    <button className="new_agent_button" onClick={onCreateAgent}>
                        <FaIcons.FaPlus /> New Agent
                    </button>

                    <div className="agents_list">
                        {agents?.map(agent => (
                            <div 
                                key={agent.id} 
                                className={`agent_item ${currentAgent?.id === agent.id ? 'active' : ''}`}
                                onClick={() => onSwitchAgent(agent.id)}
                            >
                                {editingName === agent.id ? (
                                    <input
                                        ref={nameInputRef}
                                        type="text"
                                        defaultValue={agent.name}
                                        onBlur={(e) => handleNameChange(agent.id, e.target.value)}
                                        onKeyPress={(e) => handleNameKeyPress(e, agent.id, e.target.value)}
                                    />
                                ) : (
                                    <>
                                        <span className='agent_name'>{agent.name}</span>
                                        <div className="agent_actions">
                                            <FaIcons.FaPen 
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setEditingName(agent.id);
                                                }}
                                            />
                                            <FaIcons.FaTrash 
                                                className='delete_icon'
                                                onClick={(e) => {
                                                    e.stopPropagation();

                                                    if (window.confirm('Are you sure you want to delete this agent?')) {
                                                        onDeleteAgent(agent.id);
                                                    }
                                                }}
                                            />
                                        </div>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
            

            

            <Popup 
                trigger={
                    <div className='settings'>
                        <FaIcons.FaCog />
                        <span>Settings</span>
                    </div>
                }
                open={isOpen}
                onOpen={() => setIsOpen(true)}
                onClose={() => setIsOpen(false)}
                modal
                nested
                position="center center"
            >
                <div className='popup_holder'>
                    <div className='popup'>
                        <h1>Settings</h1>

                        <div className='popup_body'>
                            <div className='settings_section actions_section'>
                                <h2>Actions: </h2>

                                <div 
                                    className={`action_item ${selectedActions.includes('reply') ? 'selected' : ''}`}
                                    onClick={() => toggleAction('reply')}
                                >
                                    <FaIcons.FaComment />
                                </div>
                                <div 
                                    className={`action_item ${selectedActions.includes('email') ? 'selected' : ''}`}
                                    onClick={() => toggleAction('email')}
                                >
                                    <FaIcons.FaEnvelope />
                                </div>
                                <div 
                                    className={`action_item ${selectedActions.includes('search') ? 'selected' : ''}`}
                                    onClick={() => toggleAction('search')}
                                >
                                    <FaIcons.FaSearch />
                                </div>
                                <div 
                                    className={`action_item ${selectedActions.includes('code') ? 'selected' : ''}`}
                                    onClick={() => toggleAction('code')}
                                >
                                    <FaIcons.FaCode />
                                </div>
                            </div>

                            <div className='settings_section behavior_section'>
                                <h2 className='behavior_header'>Behavior: </h2>

                                <textarea
                                    value={behaviorText}
                                    onChange={(e) => setBehaviorText(e.target.value)}
                                    placeholder='Enter any custom behavior or instructions here...'
                                    className='behavior_textarea'
                                />
                            </div>
                        </div>
                        <button 
                            className='save_button'
                            onClick={handleSave}
                        >
                            Save Changes
                        </button>
                    </div>
                </div>
            </Popup>
        </div>
    );
}; 