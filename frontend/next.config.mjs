/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // The browser suite drives 127.0.0.1 rather than localhost. Declared so the dev server
  // stops warning about it — and because the warning says it becomes an error in a future
  // major, which would break the E2E gate on an upgrade rather than on a change.
  allowedDevOrigins: ['127.0.0.1'],

  // The browser talks only to this origin, and this origin forwards to the FastAPI
  // service. Two processes (ADR-008) without a cross-origin boundary in the browser:
  // no CORS to configure, and the session cookie stays same-origin and SameSite=Strict.
  async rewrites() {
    const backend = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }]
  },
}

export default nextConfig
