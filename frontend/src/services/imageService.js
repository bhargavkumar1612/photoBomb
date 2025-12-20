// Service to handle authenticated image requests with blob URLs
import api from './api'

const blobCache = new Map()

export const getImageUrl = async (photoId, type = 'thumbnail', size = 512) => {
  const cacheKey = `${photoId}-${type}-${size}`

  // Return cached blob URL if available
  if (blobCache.has(cacheKey)) {
    return blobCache.get(cacheKey)
  }

  try {
    const endpoint = type === 'thumbnail'
      ? `/photos/${photoId}/thumbnail/${size}`
      : `/photos/${photoId}/download`

    const response = await api.get(endpoint, {
      responseType: 'blob'
    })

    // Create a blob URL for the image
    const imageBlob = response.data
    const imageUrl = URL.createObjectURL(imageBlob)

    // Cache the blob URL
    blobCache.set(cacheKey, imageUrl)

    return imageUrl
  } catch (error) {
    console.error('Failed to load image:', error)
    return null
  }
}

// Cleanup blob URLs
export const revokeImageUrl = (url) => {
  if (url && url.startsWith('blob:')) {
    URL.revokeObjectURL(url)
  }
}

// Clear all cached blobs
export const clearBlobCache = () => {
  blobCache.forEach((url) => URL.revokeObjectURL(url))
  blobCache.clear()
}
