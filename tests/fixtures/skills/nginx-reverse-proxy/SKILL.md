---
name: nginx-reverse-proxy
description: Configure nginx as a reverse proxy in front of an app. Upstream blocks, TLS certificates, websocket headers and fixing 502 Bad Gateway errors.
---

# nginx reverse proxy

## Basic proxy
Define an `upstream`, then `proxy_pass` to it from a `location` block. Forward `Host`,
`X-Real-IP` and `X-Forwarded-Proto`.

## TLS
Terminate TLS in nginx with certbot certificates and redirect port 80 to 443.

## 502 errors
A 502 means nginx reached no healthy upstream. Check that the app listens on the port nginx
expects, read `error.log`, and confirm the process was not killed.
