/**
 * Lokální servírování production buildu s proxy /api -> backend.
 * API_PROXY=http://127.0.0.1:8000  -> lokální Django (run-local.ps1)
 * bez API_PROXY               -> produkce https://mobilmajak.com
 */
const express = require('express');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const PORT = process.env.PORT || 8001;
const API_TARGET = process.env.API_PROXY || 'https://mobilmajak.com';
const IS_LOCAL_API = /^https?:\/\/(localhost|127\.0\.0\.1)/i.test(API_TARGET);
const BUILD_DIR = path.join(__dirname, '..', 'build');

const app = express();

app.use(
    '/api',
    createProxyMiddleware({
        target: API_TARGET,
        changeOrigin: true,
        cookieDomainRewrite: 'localhost',
        onProxyRes(proxyRes) {
            if (IS_LOCAL_API) return;
            const cookies = proxyRes.headers['set-cookie'];
            if (!cookies) return;
            proxyRes.headers['set-cookie'] = cookies.map((c) =>
                c
                    .replace(/;\s*Secure/gi, '')
                    .replace(/;\s*Domain=[^;]*/gi, '')
            );
        },
    })
);

app.use(express.static(BUILD_DIR));

app.get('*', (req, res) => {
    res.sendFile(path.join(BUILD_DIR, 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Frontend build: http://localhost:${PORT}`);
    console.log(`API proxy:      ${API_TARGET}`);
});
