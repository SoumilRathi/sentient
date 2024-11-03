import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Agent } from './pages/agent';
import { Sidebar } from './components/sidebar';

export const Router = () => {
    return (
        <BrowserRouter>
            <div className="website_container">
                <Sidebar />
                <div className="main_content">
                    <Routes>
                        <Route path="/" element={<Agent />} />
                    </Routes>
                </div>
            </div>
        </BrowserRouter>
    );
}; 