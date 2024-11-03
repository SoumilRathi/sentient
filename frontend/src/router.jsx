import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { Agent } from './pages/agent';
import { Sidebar } from './components/sidebar';
import { useState, useEffect } from 'react';

const ResetPage = () => {
    useEffect(() => {
        localStorage.clear();
        window.location.href = '/';
    }, []);

    return <div>Resetting...</div>;
};

const AgentWrapper = ({ agents, currentAgent, selectedActions, behaviorText, onUpdateAgent }) => {
    const { agentId } = useParams();
    
    useEffect(() => {
        if (agentId && (!currentAgent || currentAgent.id !== agentId)) {
            const agent = agents.find(a => a.id === agentId);
            if (agent) {
                localStorage.setItem('lastUsedAgent', agent.id);
                window.location.reload();
            }
        }
    }, [agentId, currentAgent, agents]);

    if (!currentAgent) return null;

    return (
        <Agent 
            key={currentAgent.id}
            agentId={currentAgent.id}
            selectedActions={selectedActions} 
            behaviorText={behaviorText}
            onUpdateAgent={onUpdateAgent}
        />
    );
};

export const Router = () => {
    const [agents, setAgents] = useState([]);
    const [currentAgent, setCurrentAgent] = useState(null);
    const [selectedActions, setSelectedActions] = useState(['reply', 'email', 'search', 'code']);
    const [behaviorText, setBehaviorText] = useState('');

    useEffect(() => {
        const savedAgents = localStorage.getItem('agents');
        if (savedAgents) {
            const parsedAgents = JSON.parse(savedAgents);
            setAgents(parsedAgents);
            const lastUsedId = localStorage.getItem('lastUsedAgent');
            const initialAgent = parsedAgents.find(a => a.id === lastUsedId) || parsedAgents[0];
            if (initialAgent) {
                setCurrentAgent(initialAgent);
                setSelectedActions(initialAgent.selectedActions || ['reply', 'email', 'search', 'code']);
                setBehaviorText(initialAgent.behaviorText || '');
                if (window.location.pathname === '/') {
                    window.history.replaceState({}, '', `/agent/${initialAgent.id}`);
                }
            }
        } else {
            const defaultAgent = {
                id: 'agent-' + Date.now(),
                name: 'New Agent',
                selectedActions: ['reply', 'email', 'search', 'code'],
                behaviorText: '',
                messages: []
            };
            setAgents([defaultAgent]);
            setCurrentAgent(defaultAgent);
            localStorage.setItem('agents', JSON.stringify([defaultAgent]));
            localStorage.setItem('lastUsedAgent', defaultAgent.id);
            window.history.replaceState({}, '', `/agent/${defaultAgent.id}`);
        }
    }, []);

    const createNewAgent = () => {
        const newAgent = {
            id: Date.now(),
            name: 'New Agent',
            selectedActions: ['reply', 'email', 'search', 'code'],
            behaviorText: '',
            messages: []
        };
        
        setAgents(prevAgents => {
            const updatedAgents = [...prevAgents, newAgent];
            localStorage.setItem('agents', JSON.stringify(updatedAgents));
            return updatedAgents;
        });
        
        setCurrentAgent(newAgent);
        setSelectedActions(newAgent.selectedActions);
        setBehaviorText(newAgent.behaviorText);
        localStorage.setItem('lastUsedAgent', newAgent.id);
        window.history.pushState({}, '', `/agent/${newAgent.id}`);
    };

    const switchAgent = (agentId) => {
        const agent = agents.find(a => a.id === agentId);
        if (agent) {
            setCurrentAgent(agent);
            setSelectedActions(agent.selectedActions);
            setBehaviorText(agent.behaviorText);
            localStorage.setItem('lastUsedAgent', agent.id);
            window.history.pushState({}, '', `/agent/${agent.id}`);
        }
    };

    const updateAgent = (agentId, updates) => {
        setAgents(prevAgents => {
            const updatedAgents = prevAgents.map(agent => 
                agent.id === agentId ? { ...agent, ...updates } : agent
            );
            localStorage.setItem('agents', JSON.stringify(updatedAgents));
            return updatedAgents;
        });
        
        if (currentAgent?.id === agentId) {
            setCurrentAgent(prev => ({ ...prev, ...updates }));
            if (updates.selectedActions) setSelectedActions(updates.selectedActions);
            if (updates.behaviorText) setBehaviorText(updates.behaviorText);
        }
    };

    const deleteAgent = (agentId) => {
        setAgents(prevAgents => {
            const updatedAgents = prevAgents.filter(agent => agent.id !== agentId);
            localStorage.setItem('agents', JSON.stringify(updatedAgents));
            
            if (currentAgent?.id === agentId) {
                const newCurrentAgent = updatedAgents[0];
                setCurrentAgent(newCurrentAgent);
                if (newCurrentAgent) {
                    setSelectedActions(newCurrentAgent.selectedActions);
                    setBehaviorText(newCurrentAgent.behaviorText);
                    localStorage.setItem('lastUsedAgent', newCurrentAgent.id);
                }
            }
            
            return updatedAgents;
        });
    };

    return (
        <BrowserRouter>
            <div className="website_container">
                <Sidebar 
                    agents={agents}
                    currentAgent={currentAgent}
                    selectedActions={selectedActions} 
                    setSelectedActions={setSelectedActions} 
                    behaviorText={behaviorText} 
                    setBehaviorText={setBehaviorText}
                    onCreateAgent={createNewAgent}
                    onUpdateAgent={updateAgent}
                    onDeleteAgent={deleteAgent}
                    onSwitchAgent={switchAgent}
                />
                <div className="main_content">
                    <Routes>
                        <Route path="/" element={<Navigate to={`/agent/${currentAgent?.id || ''}`} replace />} />
                        <Route path="/agent/:agentId" element={
                            <AgentWrapper 
                                agents={agents}
                                currentAgent={currentAgent}
                                selectedActions={selectedActions}
                                behaviorText={behaviorText}
                                onUpdateAgent={updateAgent}
                            />
                        } />
                        <Route path="/reset" element={<ResetPage />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </div>
            </div>
        </BrowserRouter>
    );
}; 