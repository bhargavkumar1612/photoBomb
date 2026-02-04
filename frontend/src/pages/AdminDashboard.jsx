import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import './AdminDashboard.css'

export default function AdminDashboard() {
    const { user } = useAuth()
    const [scopes, setScopes] = useState({
        faces: true,
        animals: false,
        hashtags: false
    })
    const [forceReset, setForceReset] = useState(false)
    const [loading, setLoading] = useState(false)
    const [users, setUsers] = useState([])
    const [selectedUserIds, setSelectedUserIds] = useState(new Set())
    const [logs, setLogs] = useState([])

    useEffect(() => {
        const fetchUsers = async () => {
            try {
                const res = await api.get('/admin/users')
                setUsers(res.data)
                // Select current user by default
                if (user) setSelectedUserIds(new Set([user.user_id]))
            } catch (err) {
                addLog(`⚠️ Failed to load users: ${err.message}`)
            }
        }
        fetchUsers()
    }, [user])

    const toggleUser = (userId) => {
        const newSet = new Set(selectedUserIds)
        if (newSet.has(userId)) newSet.delete(userId)
        else newSet.add(userId)
        setSelectedUserIds(newSet)
    }

    const toggleAll = () => {
        if (selectedUserIds.size === users.length) setSelectedUserIds(new Set())
        else setSelectedUserIds(new Set(users.map(u => u.user_id)))
    }

    const addLog = (msg) => {
        setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev])
    }

    const handleRun = async () => {
        const selectedScopes = Object.keys(scopes).filter(k => scopes[k])
        if (selectedScopes.length === 0) {
            addLog("❌ No scopes selected")
            return
        }

        if (selectedUserIds.size === 0) {
            addLog("❌ No target users selected")
            return
        }

        if (forceReset && !window.confirm("⚠️ FORCE RESET WARNING\n\nThis will DELETE all existing groups/tags for the selected scopes and re-process them. This is destructive. Are you sure?")) {
            return
        }

        setLoading(true)
        addLog(`🚀 Starting job for ${selectedUserIds.size} users: ${selectedScopes.join(', ')} (Reset: ${forceReset})...`)

        try {
            const res = await api.post('/admin/cluster', {
                target_user_ids: Array.from(selectedUserIds),
                scopes: selectedScopes,
                force_reset: forceReset
            })

            addLog(`✅ Success: ${res.data.details}`)
        } catch (err) {
            addLog(`❌ Error: ${err.response?.data?.detail || err.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="admin-dashboard">
            <header className="admin-header">
                <h1>⚡ Admin Maintenance</h1>
                <p>Advanced system controls. Use with caution.</p>
            </header>

            <div className="admin-grid">
                <div className="admin-card">
                    <h2>AI Clustering Trigger</h2>
                    <p className="card-desc">Manually trigger AI grouping or re-scanning of the library.</p>

                    <div className="user-selector-container">
                        <div className="selector-header">
                            <label>Target Users ({selectedUserIds.size} selected)</label>
                            <button className="btn-text" onClick={toggleAll}>
                                {selectedUserIds.size === users.length ? 'Deselect All' : 'Select All'}
                            </button>
                        </div>
                        <div className="user-checklist">
                            {users.map(u => (
                                <label key={u.user_id} className={`user-checkbox-row ${selectedUserIds.has(u.user_id) ? 'selected' : ''}`}>
                                    <input
                                        type="checkbox"
                                        checked={selectedUserIds.has(u.user_id)}
                                        onChange={() => toggleUser(u.user_id)}
                                    />
                                    <span className="user-info">
                                        <span className="user-name">{u.full_name} {u.is_admin ? '👑' : ''}</span>
                                        <span className="user-email">{u.email}</span>
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div className="scope-selector">
                        <label className="checkbox-row">
                            <input
                                type="checkbox"
                                checked={scopes.faces}
                                onChange={e => setScopes({ ...scopes, faces: e.target.checked })}
                            />
                            <div className="label-text">
                                <strong>Face Recognition</strong>
                                <span>Group unassigned faces into Persons</span>
                            </div>
                        </label>

                        <label className="checkbox-row">
                            <input
                                type="checkbox"
                                checked={scopes.animals}
                                onChange={e => setScopes({ ...scopes, animals: e.target.checked })}
                            />
                            <div className="label-text">
                                <strong>Animal Detection</strong>
                                <span>Group detected animals by species</span>
                            </div>
                        </label>

                        <label className="checkbox-row">
                            <input
                                type="checkbox"
                                checked={scopes.hashtags}
                                onChange={e => setScopes({ ...scopes, hashtags: e.target.checked })}
                            />
                            <div className="label-text">
                                <strong>Hashtags & OCR</strong>
                                <span>Retry failed/unprocessed photos</span>
                            </div>
                        </label>
                    </div>

                    <div className="danger-zone">
                        <label className="toggle-row">
                            <input
                                type="checkbox"
                                checked={forceReset}
                                onChange={e => setForceReset(e.target.checked)}
                            />
                            <span className="slider"></span>
                            <span className="toggle-label">
                                <strong>Force Full Reset</strong>
                                <span className="warning">⚠️ Deletes existing groups/tags and re-scans</span>
                            </span>
                        </label>
                    </div>

                    <button
                        className="btn-primary"
                        onClick={handleRun}
                        disabled={loading}
                    >
                        {loading ? 'Processing...' : 'Run Maintenance Job'}
                    </button>
                </div>

                <div className="admin-card logs-card">
                    <h2>System Logs</h2>
                    <div className="logs-window">
                        {logs.length === 0 && <span className="placeholder">Waiting for command...</span>}
                        {logs.map((log, i) => (
                            <div key={i} className="log-line">{log}</div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
