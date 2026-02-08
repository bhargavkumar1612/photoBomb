// spa-worker.js
// Cloudflare Worker script for Single Page Application routing
// This ensures that all routes (like /login, /albums/123) are served the index.html
// so that React Router can handle them client-side.

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const { pathname } = url;

        // Is it a request for a file (like .js, .css, .png)?
        // If so, verify if it exists in assets. If yes, serve it.
        // If not, fall back to index.html ONLY for navigation routes.

        // Attempt to fetch from ASSETS binding (Cloudflare Pages automatically binds this)
        if (env.ASSETS) {
            try {
                const response = await env.ASSETS.fetch(request);
                if (response.status !== 404) {
                    return response;
                }
            } catch (e) {
                // Fall through to index.html logic
            }
        }

        // If we're here, it's a 404 or a navigation request.
        // Serve index.html for SPA routing.
        // Verify ASSETS binding exists first
        if (env.ASSETS) {
            const indexResponse = await env.ASSETS.fetch(new Request(new URL("/index.html", url), request));
            return indexResponse;
        }

        return new Response("Not Found", { status: 404 });
    }
};
