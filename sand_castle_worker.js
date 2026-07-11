// Sand Castle Crashers — thin Worker v0.7.0
// Serves static assets from ./public and stamps a deploy-version header.
const WORKER_VER = 'v0.7.0';

export default {
  async fetch(request, env) {
    const resp = await env.ASSETS.fetch(request);
    const headers = new Headers(resp.headers);
    headers.set('X-Worker-Ver', WORKER_VER);
    return new Response(resp.body, { status: resp.status, headers });
  }
};
