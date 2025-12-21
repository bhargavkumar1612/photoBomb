import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Timeline from './pages/Timeline'
import Upload from './pages/Upload'
import Settings from './pages/Settings'
import Albums from './pages/Albums'
import AlbumDetail from './pages/AlbumDetail'
import Sidebar from './components/Sidebar'
import UploadProgressWidget from './components/UploadProgressWidget'
import './App.css'

// Protected Route wrapper
function ProtectedRoute({ children }) {
    const { user, loading } = useAuth()

    if (loading) {
        return <div className="loading">Loading...</div>
    }

    return user ? children : <Navigate to="/login" />
}

// Layout with Sidebar
function AppLayout({ children }) {
    const [sidebarOpen, setSidebarOpen] = useState(false)

    return (
        <div className="app-layout">
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
            <div className="main-content">
                <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)}>
                    ☰
                </button>
                {children}
            </div>
            <UploadProgressWidget />
        </div>
    )
}

// Placeholder components for new routes
function Favorites() {
    return (
        <div className="timeline-container">
            <header className="timeline-header">
                <h1>Favorites</h1>
            </header>
            <main className="timeline-content">
                <Timeline favoritesOnly={true} />
            </main>
        </div>
    )
}

function Trash() {
    return (
        <div className="timeline-container">
            <header className="timeline-header">
                <h1>Trash</h1>
                <p>Recently deleted items (Coming soon...)</p>
            </header>
        </div>
    )
}

function App() {
    return (
        <AuthProvider>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                <Route path="/" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <Timeline />
                        </AppLayout>
                    </ProtectedRoute>
                } />

                <Route path="/upload" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <Upload />
                        </AppLayout>
                    </ProtectedRoute>
                } />

                <Route path="/favorites" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <Timeline favoritesOnly={true} />
                        </AppLayout>
                    </ProtectedRoute>
                } />

                <Route path="/albums" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <Albums />
                        </AppLayout>
                    </ProtectedRoute>
                } />

                <Route path="/albums/:albumId" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <AlbumDetail />
                        </AppLayout>
                    </ProtectedRoute>
                } />

                <Route path="/trash" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <Trash />
                        </AppLayout>
                    </ProtectedRoute>
                } />

                <Route path="/settings" element={
                    <ProtectedRoute>
                        <AppLayout>
                            <Settings />
                        </AppLayout>
                    </ProtectedRoute>
                } />
            </Routes>
        </AuthProvider>
    )
}

export default App
