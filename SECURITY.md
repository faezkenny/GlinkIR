# Security & Privacy Considerations

## Current Security Measures

### ✅ Implemented
1. **OAuth State Validation** - CSRF protection via state parameter
2. **Secure Cookies** - HttpOnly, SameSite=Lax to prevent XSS/CSRF
3. **Job Ownership** - Jobs are tied to session IDs, preventing unauthorized access
4. **Input Validation** - URL format validation, file size limits
5. **Error Handling** - Generic error messages prevent information leakage
6. **Environment Variables** - Secrets stored in .env (gitignored)

## ⚠️ Security Issues Fixed

### 1. CORS Configuration
- **Before**: `allow_origins=["*"]` with credentials (CRITICAL)
- **After**: Only allows configured `FRONTEND_ORIGIN`
- **Impact**: Prevents unauthorized cross-origin requests

### 2. Job Authorization
- **Before**: Anyone with jobId could access results
- **After**: Jobs require session ownership verification
- **Impact**: Prevents unauthorized access to search results

### 3. Error Message Leakage
- **Before**: Internal errors exposed to clients
- **After**: Generic error messages only
- **Impact**: Prevents information disclosure

### 4. File Upload Limits
- **Before**: No size validation
- **After**: 10MB limit on face images
- **Impact**: Prevents DoS via large uploads

### 5. Cache Security
- **Before**: MD5 hashing (weak)
- **After**: SHA256 hashing
- **Impact**: Better cryptographic security

## 🔒 Privacy Considerations

### Data Storage
- **Face Encodings**: Cached in `cache/` directory as JSON files
- **OCR Results**: Cached in `cache/` directory as JSON files
- **OAuth Tokens**: Stored in-memory (lost on restart)

### Recommendations
1. **Encrypt cached data** - Face encodings contain biometric data
2. **Add TTL to sessions** - Auto-expire sessions after inactivity
3. **Add TTL to OAuth states** - Clean up unused states
4. **Add rate limiting** - Prevent abuse of endpoints
5. **Use secure storage** - Replace in-memory stores with Redis/DB + encryption
6. **Add audit logging** - Track who accessed what data

## 🚨 Production Checklist

Before deploying to production:

- [ ] Set `secure=True` on cookies (requires HTTPS)
- [ ] Use Redis/DB for sessions (not in-memory)
- [ ] Encrypt stored tokens and face encodings
- [ ] Add rate limiting (e.g., slowapi)
- [ ] Enable HTTPS only
- [ ] Add request logging (without sensitive data)
- [ ] Set up proper CORS origins (no wildcards)
- [ ] Add session expiration/TTL
- [ ] Implement token refresh for OAuth
- [ ] Add input sanitization for all user inputs
- [ ] Set up monitoring/alerting
- [ ] Regular security audits

## Privacy Policy Considerations

Users should be informed:
- Face images are processed but not stored permanently
- Face encodings are cached for performance
- OCR text is cached for performance
- OAuth tokens are stored server-side
- Search results are visible only to the user who created the job
