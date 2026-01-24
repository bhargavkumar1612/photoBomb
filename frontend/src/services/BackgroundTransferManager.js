import { get, set, update } from 'idb-keyval'

class BackgroundTransferManager {
    constructor() {
        this.SW_TAG = 'photobomb-upload'
        this.listeners = new Set()
        this.init()
    }

    async init() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', this.handleMessage.bind(this))
            // Check for existing transfers on load
            this.syncState()
        }
    }

    async syncState() {
        // Sync with Service Worker and IDB
        if ('BackgroundFetchManager' in self) {
            const registration = await navigator.serviceWorker.ready
            const fetches = await registration.backgroundFetch.getIds()
            // Update UI with these IDs...
        }
    }

    handleMessage(event) {
        if (event.data && event.data.type) {
            this.notifyListeners(event.data)
        }
    }

    subscribe(callback) {
        this.listeners.add(callback)
        return () => this.listeners.delete(callback)
    }

    notifyListeners(data) {
        this.listeners.forEach(cb => cb(data))
    }

    async uploadFiles(files) {
        // Get the API base URL from environment (critical for production where frontend/backend are on different domains)
        const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'

        // Check if cross-origin (dev testing scenario: localhost -> production)
        const isCrossOrigin = apiBaseUrl.startsWith('http') && !apiBaseUrl.includes(window.location.origin)

        // Fallback to regular fetch for cross-origin (Background Fetch has restrictions)
        if (isCrossOrigin) {
            console.log('Using regular fetch for cross-origin upload')
            return this.uploadWithFetch(files, apiBaseUrl)
        }

        // Use Background Fetch for same-origin
        // Safety check for Service Worker (it might be missing in non-secure contexts like LAN IP)
        if (!('serviceWorker' in navigator)) {
            return this.uploadWithFetch(files, apiBaseUrl)
        }

        // Forcing fallback to regular fetch to debug R2 upload issues
        // const registration = await navigator.serviceWorker.ready
        // if (!registration.backgroundFetch) {
        //     return this.uploadWithFetch(files, apiBaseUrl)
        // }
        return this.uploadWithFetch(files, apiBaseUrl)

        const uploadId = `upload-${Date.now()}`
        const requests = files.map(file => {
            const formData = new FormData()
            formData.append('file', file)
            // Use absolute URL for cross-origin uploads in production
            const url = `${apiBaseUrl}/upload/direct?filename=${encodeURIComponent(file.name)}`
            return new Request(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: formData
            })
        })

        try {
            const bgFetch = await registration.backgroundFetch.fetch(uploadId, requests, {
                title: `Uploading ${files.length} photos`,
                icons: [{
                    src: '/icons/icon-192x192.png',
                    sizes: '192x192',
                    type: 'image/png',
                }],
                downloadTotal: files.reduce((acc, f) => acc + f.size, 0)
            })

            return bgFetch
        } catch (err) {
            console.error('Background Fetch failed, falling back to regular fetch', err)
            return this.uploadWithFetch(files, apiBaseUrl)
        }
    }

    async uploadWithFetch(files, apiBaseUrl) {
        const uploadId = `fetch-upload-${Date.now()}`

        // Start processing in background (without awaiting) to unblock UI
        this._processFetchUploads(uploadId, files, apiBaseUrl).catch(err => {
            console.error('Background upload process failed:', err)
        })

        return { id: uploadId, results: [] }
    }

    async _processFetchUploads(uploadId, files, apiBaseUrl) {
        const token = localStorage.getItem('access_token')
        const results = []

        // Emit start event
        window.dispatchEvent(new CustomEvent('upload-start', {
            detail: { uploadId, total: files.length }
        }))

        for (let i = 0; i < files.length; i++) {
            const file = files[i]
            const formData = new FormData()
            formData.append('file', file)

            // Emit progress event
            window.dispatchEvent(new CustomEvent('upload-progress', {
                detail: {
                    uploadId,
                    current: i + 1,
                    total: files.length,
                    filename: file.name,
                    progress: Math.round(((i + 1) / files.length) * 100)
                }
            }))

            try {
                const response = await fetch(`${apiBaseUrl}/upload/direct?filename=${encodeURIComponent(file.name)}`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                })

                if (!response.ok) {
                    throw new Error(`Upload failed: ${response.statusText}`)
                }

                const data = await response.json()
                results.push(data)
            } catch (err) {
                console.error(`Failed to upload ${file.name}:`, err)

                // Emit error event
                window.dispatchEvent(new CustomEvent('upload-error', {
                    detail: { uploadId, filename: file.name, error: err.message }
                }))

                // Continue to next file instead of crashing entire batch
            }
        }

        // Emit completion event
        window.dispatchEvent(new CustomEvent('upload-complete', {
            detail: { uploadId, total: files.length, results }
        }))

        return { id: uploadId, results }
    }
}

export const backgroundTransferManager = new BackgroundTransferManager()
