import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../services/api'
import './Upload.css'

export default function Upload() {
    const [selectedFiles, setSelectedFiles] = useState([])
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState({})
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const handleFileSelect = (e) => {
        const files = Array.from(e.target.files)
        setSelectedFiles(files)
    }

    const handleUpload = async () => {
        if (selectedFiles.length === 0) return

        setUploading(true)

        for (const file of selectedFiles) {
            try {
                // Upload directly through backend (bypasses CORS)
                const formData = new FormData()
                formData.append('file', file)

                const response = await api.post('/upload/direct', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    },
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                        setProgress((prev) => ({ ...prev, [file.name]: percentCompleted }))
                    }
                })

                setProgress((prev) => ({ ...prev, [file.name]: 100 }))
            } catch (error) {
                console.error('Upload failed:', error)
                const errorMessage = error.response?.data?.detail || error.message
                alert(`Upload failed for ${file.name}: ${errorMessage}`)
                setProgress((prev) => ({ ...prev, [file.name]: -1 }))
            }
        }

        setUploading(false)

        // Invalidate photos cache to refresh timeline
        queryClient.invalidateQueries({ queryKey: ['photos'] })

        // Navigate back to timeline
        setTimeout(() => navigate('/'), 500)
    }

    return (
        <div className="upload-container">
            <header className="upload-header">
                <h1>Upload Photos</h1>
                <button onClick={() => navigate('/')} className="btn-secondary">
                    Back to Timeline
                </button>
            </header>

            <main className="upload-content">
                <div className="upload-zone">
                    <input
                        type="file"
                        id="file-input"
                        multiple
                        accept="image/*"
                        onChange={handleFileSelect}
                        style={{ display: 'none' }}
                    />
                    <label htmlFor="file-input" className="upload-label">
                        <div className="upload-icon">📸</div>
                        <p>Click to select photos</p>
                        <small>or drag and drop</small>
                    </label>
                </div>

                {selectedFiles.length > 0 && (
                    <div className="selected-files">
                        <h3>Selected Files ({selectedFiles.length})</h3>
                        <ul>
                            {selectedFiles.map((file, index) => (
                                <li key={index}>
                                    <span>{file.name}</span>
                                    {progress[file.name] !== undefined && (
                                        <div className="progress-bar">
                                            <div
                                                className="progress-fill"
                                                style={{ width: `${Math.max(0, progress[file.name])}%` }}
                                            />
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                        <button
                            onClick={handleUpload}
                            disabled={uploading}
                            className="btn-primary"
                        >
                            {uploading ? 'Uploading...' : 'Upload All'}
                        </button>
                    </div>
                )}
            </main>
        </div>
    )
}
