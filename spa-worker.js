export default {
    async fetch(request, env) {
        try {
            const url = new URL(request.url);

            // Try to serve the request as a static asset first
            // usage of env.ASSETS requires the "assets" binding in wrangler.json
            if (!env.ASSETS) {
                console.log("Environment keys:", Object.keys(env));
                throw new Error(`env.ASSETS is undefined. Available keys: ${JSON.stringify(Object.keys(env))}. Config issue?`);
            }

            let response = await env.ASSETS.fetch(request);

            // Clone response to add headers (responses are immutable)
            response = new Response(response.body, response);
            response.headers.set('X-Worker-Version', '1.0.1-debug');

            // If the asset is not found (404), and it's likely a navigation request (SPA route)

            // If the asset is not found (404), and it's likely a navigation request (SPA route)
            // we should serve index.html instead.
            if (response.status === 404) {
                const pathname = url.pathname;

                // Check if it's a request for a static asset (based on extension)
                // We explicitly exclude these from the fallback to avoid "MIME type text/html" errors
                // for missing scripts or images.
                const isStaticAsset = /\.(js|css|png|jpg|jpeg|gif|ico|json|svg|woff|woff2|ttf|map|webmanifest)$/i.test(pathname);

                // Check if the client explicitly accepts HTML (standard for browser navigation)
                const acceptsHtml = request.headers.get('Accept')?.includes('text/html');

                // Fallback to index.html ONLY for navigation requests that aren't API calls or static assets
                if (!isStaticAsset && !pathname.startsWith('/api/') && !pathname.startsWith('/assets/') && acceptsHtml) {
                    return env.ASSETS.fetch(new URL('/index.html', request.url));
                }
            }

            return response;
        } catch (e) {
            return new Response(`Worker Error: ${e.message}\n${e.stack}`, {
                status: 500,
                headers: { "content-type": "text/plain" }
            });
        }
    }
};
