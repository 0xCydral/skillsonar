---
name: oauth-login-flow
description: Implement sign-in with OAuth 2.0 and OpenID Connect using the authorization code flow with PKCE, token storage, refresh and logout.
---

# OAuth login flow

## Authorization code with PKCE
Generate a code verifier, send its hash as the challenge, and exchange the returned code for
tokens on the server. Validate the `state` parameter on return.

## Tokens
Keep access tokens short lived. Store refresh tokens in an httpOnly cookie, never in
localStorage.

## Logout
Revoke the refresh token and clear the session cookie.
