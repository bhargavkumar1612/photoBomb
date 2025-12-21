import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { clientsClaim } from 'workbox-core'

// self.__WB_MANIFEST is injected by Vite PWA plugin
precacheAndRoute(self.__WB_MANIFEST)

// Take control immediately
self.skipWaiting()
clientsClaim()

// Background Fetch API Support
const BG_FETCH_TAG = 'photobomb-upload'

// Handle background fetch success
self.addEventListener('backgroundfetchsuccess', (event) => {
    const bgFetch = event.registration

    event.waitUntil(
        (async () => {
            // Notify client of success
            await notifyClients({
                type: 'UPLOAD_COMPLETE',
                id: bgFetch.id
            })
        })()
    )
})

// Handle background fetch failure
self.addEventListener('backgroundfetchfail', (event) => {
    event.waitUntil(
        (async () => {
            await notifyClients({
                type: 'UPLOAD_FAILED',
                id: event.registration.id
            })
        })()
    )
})

// Click handler for notification tap
self.addEventListener('backgroundfetchclick', (event) => {
    event.waitUntil(
        clients.openWindow('/')
    )
})

async function notifyClients(message) {
    const clientList = await clients.matchAll({ includeUncontrolled: true, type: 'window' })
    for (const client of clientList) {
        client.postMessage(message)
    }
}
