import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/TopBar';
import './AppLayout.css';

export default function AppLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="app-layout">
            <Sidebar
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
            />

            <div className={`main-content ${sidebarOpen ? 'sidebar-open' : ''}`}>
                <TopBar onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

                <main className="content-scrollable">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
