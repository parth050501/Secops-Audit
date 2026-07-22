/** @type {import('next').NextConfig} */
module.exports = {
  // Prevent Next.js from redirecting/normalizing trailing slashes on proxied API calls.
  // Without this, '/api/tickets/' gets redirected and the browser drops auth headers + POST body.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = process.env.BACKEND_URL || 'http://backend:8000';
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }];
  },
};
