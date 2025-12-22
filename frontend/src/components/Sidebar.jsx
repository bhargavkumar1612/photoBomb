import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Home, Folder, Star, Trash2, Settings, Cloud } from 'lucide-react'
import api from '../services/api'
import './Sidebar.css'

export default function Sidebar({ isOpen, onClose }) {
    const location = useLocation()

    // Fetch real user data for storage
    const { data: userData } = useQuery({
        queryKey: ['user-info'],
        queryFn: async () => {
            const response = await api.get('/auth/me')
            return response.data
        }
    })

    const menuItems = [
        { path: '/', icon: <Home size={20} />, label: 'Photos' },
        { path: '/albums', icon: <Folder size={20} />, label: 'Albums' },
        { path: '/favorites', icon: <Star size={20} />, label: 'Favorites' },
        { path: '/trash', icon: <Trash2 size={20} />, label: 'Trash' },
        { path: '/settings', icon: <Settings size={20} />, label: 'Settings' },
    ]

    const formatBytes = (bytes) => {
        if (!bytes) return '0 GB'
        const gb = bytes / (1024 * 1024 * 1024)
        return gb.toFixed(1) + ' GB'
    }

    const storagePercent = userData
        ? (userData.storage_used_bytes / userData.storage_quota_bytes) * 100
        : 0

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && (
                <div className="sidebar-overlay" onClick={onClose} />
            )}

            {/* Sidebar */}
            <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
                <div className="sidebar-header">
                    <h2 className="sidebar-logo">PhotoBomb</h2>
                    <button className="sidebar-close" onClick={onClose}>×</button>
                </div>

                <nav className="sidebar-nav">
                    {menuItems.map((item) => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={`sidebar-item ${location.pathname === item.path ? 'active' : ''}`}
                            onClick={onClose}
                        >
                            <span className="sidebar-icon">{item.icon}</span>
                            <span className="sidebar-label">{item.label}</span>
                        </Link>
                    ))}
                </nav>

                <div className="sidebar-footer">
                    <div className="storage-info">
                        <div className="storage-bar">
                            <div className="storage-used" style={{ width: `${storagePercent}%` }}></div>
                        </div>
                        <p className="storage-text">
                            {formatBytes(userData?.storage_used_bytes)} of {formatBytes(userData?.storage_quota_bytes)} used
                        </p>
                    </div>
                </div>
            </aside>
        </>
    )
}
