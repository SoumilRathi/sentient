import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Agent } from './pages/agent';
import { useState } from 'react';

const ResetPage = () => {
    window.location.href = '/';
    return <div>Resetting...</div>;
};

export const Router = () => {
    const [selectedActions] = useState(['reply', 'email', 'search', 'code']);
    const [behaviorText] = useState('');

    return (
        <BrowserRouter>
            <div className="website_container">
                <div className="main_content">
                    <Routes>
                        <Route path="/" element={
                            <Agent 
                                selectedActions={selectedActions} 
                                behaviorText={behaviorText}
                            />
                        } />
                        <Route path="/reset" element={<ResetPage />} />
                    </Routes>
                </div>
            </div>
        </BrowserRouter>
    );
}; 