import { Link } from 'react-router-dom';
import './styles/sidebar.css';
import logo from './sentient.png';
import * as FaIcons from 'react-icons/fa';

export const Sidebar = () => {
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
            <div className='settings'>
                <FaIcons.FaCog />
                <span>Settings</span>
            </div>
        </div>
    );
}; 