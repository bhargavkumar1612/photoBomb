# PWA Specification & UX

## Progressive Web App Requirements

### Manifest.json

```json
{
  "name": "PhotoBomb - Your Photo Library",
  "short_name": "PhotoBomb",
  "description": "Secure, private photo storage and sharing service",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "theme_color": "#4F46E5",
  "background_color": "#FFFFFF",
  "icons": [
    {
      "src": "/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshots/desktop-1.png",
      "sizes": "1280x720",
      "type": "image/png",
      "form_factor": "wide"
    },
    {
      "src": "/screenshots/mobile-1.png",
      "sizes": "750x1334",
      "type": "image/png",
      "form_factor": "narrow"
    }
  ],
  "categories": ["photo", "productivity"],
  "shortcuts": [
    {
      "name": "Upload Photos",
      "short_name": "Upload",
      "description": "Upload new photos",
      "url": "/upload",
      "icons": [{ "src": "/icons/upload-96x96.png", "sizes": "96x96" }]
    },
    {
      "name": "Recent Photos",
      "short_name": "Recent",
      "url": "/",
      "icons": [{ "src": "/icons/recent-96x96.png", "sizes": "96x96" }]
    }
  ],
  "share_target": {
    "action": "/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "text",
      "url": "url",
      "files": [
        {
          "name": "photos",
          "accept": ["image/jpeg", "image/png", "image/webp", "image/heic"]
        }
      ]
    }
  },
  "related_applications": [],
  "prefer_related_applications": false
}
```

### Service Worker Strategy

**Architecture**: Workbox 7.0+ (Google's service worker library)

**Caching Strategies**:

| Resource Type | Strategy | Cache Name | Max Age | Max Entries |
|---------------|----------|------------|---------|-------------|
| App shell (HTML, CSS, JS) | CacheFirst | app-shell-v1 | 30 days | N/A |
| Static assets (fonts, icons) | CacheFirst | static-assets-v1 | 1 year | 100 |
| Thumbnails (images) | CacheFirst | thumbnails-v1 | 7 days | 500 |
| API responses (metadata) | NetworkFirst | api-cache-v1 | 5 minutes | 200 |
| User uploads (queued) | NetworkOnly | N/A | N/A | N/A |

**Service Worker Registration**:
```javascript
// src/registerServiceWorker.js
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then(registration => {
        console.log('SW registered:', registration);
        
        // Check for updates every 24 hours
        setInterval(() => {
          registration.update();
        }, 24 * 60 * 60 * 1000);
      })
      .catch(err => console.error('SW registration failed:', err));
  });
}
```

**Service Worker Code** (src/service-worker.js):
```javascript
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, NetworkFirst, NetworkOnly } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { BackgroundSyncPlugin } from 'workbox-background-sync';

// Precache app shell (injected at build time by Workbox CLI)
precacheAndRoute(self.__WB_MANIFEST);

// Cache thumbnails (CacheFirst for performance)
registerRoute(
  ({ url }) => url.pathname.startsWith('/thumb/'),
  new CacheFirst({
    cacheName: 'thumbnails-v1',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 500,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
        purgeOnQuotaError: true,
      }),
      new CacheableResponsePlugin({
        statuses: [0, 200], // Cache opaque responses from CDN
      }),
    ],
  })
);

// Cache API metadata (NetworkFirst for freshness)
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/v1/photos'),
  new NetworkFirst({
    cacheName: 'api-cache-v1',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 200,
        maxAgeSeconds: 5 * 60, // 5 minutes
      }),
    ],
  })
);

// Background sync for offline uploads
const uploadSyncPlugin = new BackgroundSyncPlugin('upload-queue', {
  maxRetentionTime: 7 * 24 * 60, // 7 days in minutes
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftRequest())) {
      try {
        await fetch(entry.request.clone());
        console.log('Upload synced:', entry.request.url);
      } catch (error) {
        console.error('Upload sync failed:', error);
        await queue.unshiftRequest(entry);
        throw error;
      }
    }
  },
});

registerRoute(
  ({ url }) => url.pathname === '/api/v1/upload/confirm',
  new NetworkOnly({
    plugins: [uploadSyncPlugin],
  }),
  'POST'
);

// Offline fallback page
registerRoute(
  ({ request }) => request.mode === 'navigate',
  async ({ event }) => {
    try {
      return await fetch(event.request);
    } catch (error) {
      const cache = await caches.open('app-shell-v1');
      return cache.match('/offline.html');
    }
  }
);
```

### Offline Upload Queue

**IndexedDB Schema** (using Dexie.js 3.2+):
```javascript
import Dexie from 'dexie';

const db = new Dexie('PhotoBombDB');
db.version(1).stores({
  pendingUploads: '++id, status, created_at',
  photoMetadata: 'photo_id, user_id, uploaded_at',
});

// Queue upload
async function queueUpload(file, metadata) {
  const id = await db.pendingUploads.add({
    file: file, // Store File object directly
    metadata: metadata,
    status: 'queued',
    retry_count: 0,
    created_at: new Date(),
  });
  
  // Register background sync
  if ('serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype) {
    const registration = await navigator.serviceWorker.ready;
    await registration.sync.register('upload-sync');
  }
  
  return id;
}
```

**UI Feedback**:
```jsx
// React component
function UploadStatus({ uploadId }) {
  const [status, setStatus] = useState('queued');
  
  useEffect(() => {
    const subscription = db.pendingUploads
      .where('id').equals(uploadId)
      .toArray(uploads => {
        if (uploads[0]) setStatus(uploads[0].status);
      });
    
    return () => subscription.unsubscribe();
  }, [uploadId]);
  
  return (
    <div className="upload-status">
      {status === 'queued' && <Icon name="clock" />}
      {status === 'uploading' && <Spinner />}
      {status === 'completed' && <Icon name="check" />}
      {status === 'failed' && <Icon name="error" />}
      <span>{status.toUpperCase()}</span>
    </div>
  );
}
```

## Add-to-Home Behavior

### Android (Chrome, Edge, Samsung Internet)

**Requirements**:
- [x] Manifest.json with required fields
- [x] Service worker registered
- [x] HTTPS (or localhost for testing)
- [x] User engagement heuristic (30-second browsing time or 2 visits within 5 days)

**Installation Prompt**:
```javascript
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  
  // Show custom install button
  document.getElementById('installButton').style.display = 'block';
});

document.getElementById('installButton').addEventListener('click', async () => {
  if (deferredPrompt) {
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log('Install outcome:', outcome); // 'accepted' or 'dismissed'
    deferredPrompt = null;
  }
});
```

**Behavior after install**:
- App launches in standalone mode (no browser UI)
- App switcher shows PhotoBomb icon
- Share sheet includes PhotoBomb as target (via `share_target`)

### iOS (Safari)

**Requirements**:
- [x] Manifest.json (limited support as of iOS 17)
- [x] HTTPS
- [x] Apple-specific meta tags (fallback)

**iOS Meta Tags** (in index.html):
```html
<!-- iOS-specific -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="PhotoBomb">
<link rel="apple-touch-icon" href="/icons/icon-180x180.png">

<!-- iOS splash screens (generated for various device sizes) -->
<link rel="apple-touch-startup-image" href="/splash/iphone-x.png" media="(device-width: 375px) and (device-height: 812px)">
<!-- ... more sizes ... -->
```

**Installation Instructions** (since no prompt API):
```jsx
function IOSInstallPrompt() {
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const isInStandaloneMode = window.matchMedia('(display-mode: standalone)').matches;
  
  if (isIOS && !isInStandaloneMode) {
    return (
      <div className="ios-install-banner">
        <p>Install PhotoBomb for the best experience:</p>
        <ol>
          <li>Tap the Share button <Icon name="ios-share" /></li>
          <li>Scroll and tap "Add to Home Screen"</li>
          <li>Tap "Add"</li>
        </ol>
      </div>
    );
  }
  return null;
}
```

**iOS Limitations**:
1. ❌ Background Sync API not supported → uploads queue but don't auto-resume in background
2. ❌ Share Target API not fully supported → can't receive photos from share sheet
3. ⚠️ Service Worker limited to 50MB cache → must be selective with cached thumbnails
4. ⚠️ IndexedDB quota ~50MB (can request more via `storage.persist()`)

**Mitigations**:
- **Offline uploads**: Use Visibility Change event to trigger sync when app returns to foreground
- **Share target**: Provide "Upload" button prominently instead of relying on OS share sheet
- **Cache management**: Implement LRU eviction, prioritize recent photos

### Desktop (Chrome, Edge, Safari)

**Installation**:
- Chrome/Edge: Shows install icon in address bar (omnibox) + `beforeinstallprompt` event
- Safari 17+: File > Add to Dock (macOS)

**Benefits**:
- Launches in app window (no browser tabs)
- Appears in app switcher and dock
- Desktop file handlers (future): Double-click image to open in PhotoBomb

## Offline Behavior UX

### Upload Queue States

| State | UI Indicator | User Action |
|-------|-------------|-------------|
| Queued | Gray clock icon | None (auto-syncs) |
| Uploading | Blue spinner + % | Cancel button |
| Completed | Green checkmark | None |
| Failed | Red error icon | Retry button |

**Queue Management UI**:
```jsx
function UploadQueueManager() {
  const [queue, setQueue] = useState([]);
  
  useEffect(() => {
    db.pendingUploads.toArray().then(setQueue);
  }, []);
  
  return (
    <div className="upload-queue">
      <h3>Upload Queue ({queue.length})</h3>
      {queue.map(upload => (
        <div key={upload.id} className="queue-item">
          <img src={URL.createObjectURL(upload.file)} alt="" className="thumb" />
          <span>{upload.file.name}</span>
          <UploadStatus uploadId={upload.id} />
          {upload.status === 'failed' && (
            <button onClick={() => retryUpload(upload.id)}>Retry</button>
          )}
        </div>
      ))}
    </div>
  );
}
```

### Network Status Indicator

```jsx
function NetworkStatus() {
  const [online, setOnline] = useState(navigator.onLine);
  
  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  if (!online) {
    return (
      <div className="network-status offline">
        <Icon name="wifi-off" />
        <span>Offline - Uploads will resume when connected</span>
      </div>
    );
  }
  return null;
}
```

## Testing Checklist

### PWA Audit (Lighthouse)
- [ ] Manifest.json passes validation
- [ ] Service worker registered and active
- [ ] HTTPS enabled
- [ ] Icons provided in multiple sizes (192px, 512px minimum)
- [ ] Offline fallback page works
- [ ] Lighthouse PWA score > 90

### Install Testing
- [ ] Android Chrome: Install prompt appears after 30sec browsing
- [ ] iOS Safari: Add to Home Screen available, app launches standalone
- [ ] Desktop Chrome: Install icon in omnibox works
- [ ] App icon appears correctly in launcher/home screen
- [ ] App opens in standalone mode (no browser UI)

### Offline Testing
- [ ] Browsing works offline (cached pages load)
- [ ] Upload queue persists across app restarts
- [ ] Network status indicator updates correctly
- [ ] Background Sync triggers when online (Android)
- [ ] Visibility Change triggers sync (iOS workaround)
- [ ] Failed uploads show error state with retry button

### Share Target (Android Only)
- [ ] Share photo from gallery → PhotoBomb appears in share sheet
- [ ] Shared photo queues for upload
- [ ] Multiple photos can be shared at once

## Implementation Notes

**Why Workbox over manual service worker?**
- Handles cache versioning automatically
- Built-in strategies (CacheFirst, NetworkFirst) proven at scale (Google)
- Background Sync plugin simplifies offline queue
- Precaching with webpack/vite integration (auto-generates manifest)

**Tradeoff: IndexedDB vs localStorage**
- IndexedDB can store File blobs (100MB+); localStorage limited to strings (~5MB)
- IndexedDB is async (no main thread blocking); localStorage is sync
- Complexity: IndexedDB requires wrapper (Dexie); localStorage simpler

**Alternative: Persistent Storage API**
```javascript
if (navigator.storage && navigator.storage.persist) {
  const isPersisted = await navigator.storage.persist();
  console.log('Storage persisted:', isPersisted);
}
```
Request this on first upload to prevent browser from evicting upload queue.

**iOS Background Sync Workaround**:
```javascript
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    // App came to foreground, trigger sync
    processPendingUploads();
  }
});
```
Not as robust as Background Sync, but better than nothing.
