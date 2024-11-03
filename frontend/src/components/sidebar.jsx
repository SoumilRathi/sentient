import { Link } from 'react-router-dom';
import './styles/sidebar.css';
import logo from './sentient.png';

export const Sidebar = () => {
    return (
        <div className="sidebar">
            <div className="sidebar_content">
                <img src={logo} alt="logo" />
                <nav>
                    <ul>
                        <li>
                            <Link to="/">Chat</Link>
                        </li>
                        {/* Add more navigation items here */}
                    </ul>
                </nav>
            </div>
        </div>
    );
}; 