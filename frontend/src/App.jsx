
import { useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { SearchProvider } from './context/SearchContext'
import { FeaturesProvider, useFeatures } from './context/FeaturesContext'
import AppLayout from './layouts/AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Timeline from './pages/Timeline'
import Upload from './pages/Upload'
import Settings from './pages/Settings'
import Albums from './pages/Albums'
import AlbumDetail from './pages/AlbumDetail'
import SharedAlbumView from './pages/SharedAlbumView'
import Sharing from './pages/Sharing'
import Trash from './pages/Trash'
import MapPage from './pages/MapPage'
import PeoplePage from './pages/PeoplePage'
import PersonDetailPage from './pages/PersonDetailPage'
import AnimalsPage from './pages/AnimalsPage'
import AnimalDetailPage from './pages/AnimalDetailPage'
import HashtagsPage from './pages/HashtagsPage'
import HashtagDetailPage from './pages/HashtagDetailPage'
import PlaceholderPage from './pages/PlaceholderPage'
import AdminDashboard from './pages/AdminDashboard'
import UploadProgressWidget from './components/UploadProgressWidget'
import './App.css'

function ProtectedRoute({ children }) {
    const { user, loading } = useAuth()
    const location = useLocation()

    if (loading) {
        return <div className="loading">Loading...</div>
    }

    return user ? children : <Navigate to="/login" state={{ from: location }} replace />
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

function AdminRoute({ children }) {
    const { user, loading } = useAuth()

    if (loading) return <div className="loading">Loading...</div>

    if (!user || !user.is_admin) {
        return <Navigate to="/" replace />
    }

    return children
}



function App() {
    useEffect(() => {
        // Keep-Alive Heartbeat for Render (every 10 mins)
        const interval = setInterval(() => {
            fetch(import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/healthz` : '/api/v1/healthz')
                .catch(err => console.debug("Heartbeat failed", err))
        }, 10 * 60 * 1000) // 10 minutes

        return () => clearInterval(interval)
    }, [])

    return (
        <AuthProvider>
            <FeaturesProvider>
                <SearchProvider>
                    <div className="app-container">
                        <AppRoutes />
                        <UploadProgressWidget />
                    </div>
                </SearchProvider>
            </FeaturesProvider>
        </AuthProvider>
    )
}

function AppRoutes() {
    const { animal_detection_enabled, loading } = useFeatures()

    return (
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

            <Route element={
                <ProtectedRoute>
                    <AppLayout />
                </ProtectedRoute>
            }>
                <Route path="/" element={<Timeline />} />
                <Route path="/explore" element={<PlaceholderPage title="Explore" />} />
                <Route path="/sharing" element={<Sharing />} />
                <Route path="/albums" element={<Albums />} />
                <Route path="/albums/:albumId" element={<AlbumDetail />} />
                <Route path="/shared/:token" element={<SharedAlbumView />} />
                <Route path="/people" element={<PeoplePage />} />
                <Route path="/people/:id" element={<PersonDetailPage />} />
                <Route path="/places" element={<MapPage />} />

                {/* Conditionally render Animal Routes */}
                {!loading && animal_detection_enabled && (
                    <>
                        <Route path="/animals" element={<AnimalsPage />} />
                        <Route path="/animals/:id" element={<AnimalDetailPage />} />
                    </>
                )}

                <Route path="/hashtags" element={<HashtagsPage />} />
                <Route path="/hashtags/tag/:tagId" element={<HashtagDetailPage />} />
                <Route path="/favorites" element={<Timeline favoritesOnly={true} />} />
                <Route path="/trash" element={<Trash />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/admin" element={
                    <AdminRoute>
                        <AdminDashboard />
                    </AdminRoute>
                } />
            </Route>

            {/* Catch all - redirect to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    )
}


export default App
