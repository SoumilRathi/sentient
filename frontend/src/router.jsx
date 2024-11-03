import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Agent } from './pages/agent';
import { Sidebar } from './components/sidebar';

export const Router = () => {

    const [selectedActions, setSelectedActions] = useState(['reply', 'email', 'search']);
    const [behaviorText, setBehaviorText] = useState('');

    return (
        <BrowserRouter>
            <div className="website_container">
                <Sidebar 
                    selectedActions={selectedActions} 
                    setSelectedActions={setSelectedActions} 
                    behaviorText={behaviorText} 
                    setBehaviorText={setBehaviorText} 
                />
                <div className="main_content">
                    <Routes>
                        <Route path="/" element={<Agent 
                            selectedActions={selectedActions} 
                            behaviorText={behaviorText} 
                        />} />
                    </Routes>
                </div>
            </div>
        </BrowserRouter>
    );
}; 