import { Link } from 'react-router-dom';
import './styles/sidebar.css';
import logo from './sentient.png';
import Popup from 'reactjs-popup';
import * as FaIcons from 'react-icons/fa';
import { useState } from 'react';

export const Sidebar = ({ selectedActions, setSelectedActions, behaviorText, setBehaviorText }) => {
    const [isOpen, setIsOpen] = useState(false);

    const toggleAction = (action) => {
        if (action == 'reply') {
            alert("Umm...you can't disable replying!");
            return;
        }
        if (selectedActions.includes(action)) {
            setSelectedActions(selectedActions.filter(a => a !== action));
        } else {
            setSelectedActions([...selectedActions, action]);
        }
    };

    const handleSave = () => {
        // Save settings logic here
        setIsOpen(false);
    };

    return (
        <div className="sidebar">
            <img src={logo} alt="logo" />
            {/* <nav>
                <ul>
                    <li>
                        <Link to="/">Chat</Link>
                    </li>
                </ul>
            </nav> */}
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