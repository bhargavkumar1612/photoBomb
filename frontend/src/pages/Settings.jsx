import { useAuth } from '../context/AuthContext'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import './Settings.css'

export default function Settings() {
    const { user, logout } = useAuth()

    const { data: userData } = useQuery({
        queryKey: ['user-info'],
        queryFn: async () => {
            const response = await api.get('/auth/me')
            return response.data
        }
    })

    const formatBytes = (bytes) => {
        if (!bytes) return '0 B'
        const gb = bytes / (1024 * 1024 * 1024)
        return gb.toFixed(2) + ' GB'
    }

    const storagePercent = userData
        ? (userData.storage_used_bytes / userData.storage_quota_bytes) * 100
        : 0

    return (
        <div className="settings-container">
            <header className="settings-header">
                <h1>Settings</h1>
            </header>

            <div className="settings-content">
                {/* Account Section */}
                <section className="settings-section">
                    <h2>Account</h2>
                    <div className="settings-card">
                        <div className="setting-row">
                            <label>Email</label>
                            <span>{user?.email}</span>
                        </div>
                        <div className="setting-row">
                            <label>User ID</label>
                            <span className="mono">{user?.user_id}</span>
                        </div>
                        <div className="setting-row">
                            <label>Face Recognition</label>
                            <span>{user?.face_enabled ? 'Enabled' : 'Disabled'}</span>
                        </div>
                    </div>
                </section>

                {/* Storage Section */}
                <section className="settings-section">
                    <h2>Storage</h2>
                    <div className="settings-card">
                        <div className="storage-visual">
                            <div className="storage-bar-large">
                                <div
                                    className="storage-used-large"
                                    style={{ width: `${storagePercent}%` }}
                                ></div>
                            </div>
                            <div className="storage-stats">
                                <div>
                                    <label>Used</label>
                                    <strong>{formatBytes(userData?.storage_used_bytes)}</strong>
                                </div>
                                <div>
                                    <label>Total</label>
                                    <strong>{formatBytes(userData?.storage_quota_bytes)}</strong>
                                </div>
                                <div>
                                    <label>Available</label>
                                    <strong>{formatBytes(userData?.storage_quota_bytes - userData?.storage_used_bytes)}</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Preferences Section */}
                <section className="settings-section">
                    <h2>Preferences</h2>
                    <div className="settings-card">
                        <div className="setting-row">
                            <label>Theme</label>
                            <select disabled>
                                <option>Light (default)</option>
                                <option>Dark (coming soon)</option>
                            </select>
                        </div>
                        <div className="setting-row">
                            <label>Default Grid Size</label>
                            <span>{localStorage.getItem('gridSize') || 'comfortable'}</span>
                        </div>
                    </div>
                </section>

                {/* Danger Zone */}
                <section className="settings-section">
                    <h2>Danger Zone</h2>
                    <div className="settings-card danger-zone">
                        <button className="btn-danger" onClick={logout}>
                            🚪 Logout
                        </button>
                        <button className="btn-danger" onClick={() => alert('Delete account feature coming soon')} disabled>
                            ⚠️ Delete Account (Coming Soon)
                        </button>
                    </div>
                </section>
            </div>
        </div>
    )
}
