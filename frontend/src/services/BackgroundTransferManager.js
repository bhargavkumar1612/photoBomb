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
        const registration = await navigator.serviceWorker.ready
        if (!registration.backgroundFetch) {
            throw new Error('Background Fetch not supported')
        }

        // Get the API base URL from environment (critical for production where frontend/backend are on different domains)
        const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'

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
            console.error('Background Fetch failed', err)
            throw err
        }
    }
}

export const backgroundTransferManager = new BackgroundTransferManager()
