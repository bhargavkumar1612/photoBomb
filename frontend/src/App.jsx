import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { SearchProvider } from './context/SearchContext'
import AppLayout from './layouts/AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Timeline from './pages/Timeline'
import Upload from './pages/Upload'
import Settings from './pages/Settings'
import Albums from './pages/Albums'
import AlbumDetail from './pages/AlbumDetail'
import SharedAlbumView from './pages/SharedAlbumView'
import Trash from './pages/Trash'
import PlaceholderPage from './pages/PlaceholderPage'
import UploadProgressWidget from './components/UploadProgressWidget'
import './App.css'

function ProtectedRoute({ children }) {
    const { user, loading } = useAuth()

    if (loading) {
        return <div className="loading">Loading...</div>
    }

    return user ? children : <Navigate to="/login" />
}

function PublicOnlyRoute({ children }) {
    const { user, loading } = useAuth()
    const navigate = useNavigate()

    useEffect(() => {
        if (!loading && user) {
            navigate('/', { replace: true })
        }
    }, [user, loading, navigate])

    if (loading) {
        return <div className="loading">Loading...</div>
    }

    // While redirecting, return null to avoid flash
    if (user) return null

    return children
}

function App() {
    return (
        <AuthProvider>
            <SearchProvider>
                <div className="app-container">
                    <Routes>
                        <Route path="/login" element={
                            <PublicOnlyRoute>
                                <Login />
                            </PublicOnlyRoute>
                        } />
                        <Route path="/register" element={
                            <PublicOnlyRoute>
                                <Register />
                            </PublicOnlyRoute>
                        } />
                        <Route path="/shared/:token" element={<SharedAlbumView />} />

                        <Route element={
                            <ProtectedRoute>
                                <AppLayout />
                            </ProtectedRoute>
                        }>
                            <Route path="/" element={<Timeline />} />
                            <Route path="/explore" element={<PlaceholderPage title="Explore" />} />
                            <Route path="/sharing" element={<PlaceholderPage title="Sharing" />} />
                            <Route path="/albums" element={<Albums />} />
                            <Route path="/albums/:albumId" element={<AlbumDetail />} />
                            <Route path="/people" element={<PlaceholderPage title="People" />} />
                            <Route path="/places" element={<PlaceholderPage title="Places" />} />
                            <Route path="/favorites" element={<Timeline favoritesOnly={true} />} />
                            <Route path="/trash" element={<Trash />} />
                            <Route path="/settings" element={<Settings />} />
                            <Route path="/upload" element={<Upload />} />
                        </Route>

                        {/* Catch all - redirect to home (which is protected, so will redirect to login if needed) */}
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>

                    <UploadProgressWidget />
                </div>
            </SearchProvider>
        </AuthProvider>
    )
}

export default App
