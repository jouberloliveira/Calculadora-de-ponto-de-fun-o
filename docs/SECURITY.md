# Security Threat Model — FPA API

**Last updated:** 2026-05-18  
**Scope:** `apps/api` (FastAPI + Ollama) and `apps/web` (Next.js)  
**Owner:** Security Reviewer

---

## STRIDE Threat Model

| ID | Threat | Attack Vector | STRIDE | Mitigação | Status | Owner |
|----|--------|---------------|--------|-----------|--------|-------|
| T-01 | Oversized upload causes OOM before size check fires | POST /analyze with multi-GB body | DoS | Stream upload in 1 MB chunks via `_read_upload_capped`; 50 MB hard cap | ✅ Fixed (`fix/security-hardening-prompt-and-upload-size`) | API |
| T-02 | ZIP slip / path traversal via crafted archive member names | `.zip` upload with `../../etc/passwd` member | Tampering | Resolve real path under temp root; reject absolute/traversal paths | ✅ Fixed (`feat/api-fpa-ollama`) | API |
| T-03 | ZIP bomb — decompression amplification | `.zip` with high compression ratio | DoS | Member count cap (1 000); decompressed bytes cap (100 MB); pre-read projection check | ✅ Fixed (`feat/api-fpa-ollama`) | API |
| T-04 | PDF with malicious JavaScript | `.pdf` upload | Execution | `pdfminer.six` — pure Python, no JS engine | ✅ Fixed (library choice) | API |
| T-05 | PDF DoS via huge page count | `.pdf` with 100 000+ pages | DoS | `maxpages=500` cap on `pdf_extract_text` | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | API |
| T-06 | MIME spoofing — rename binary as `.py` or `.pdf` | Upload `.exe` renamed to `.py` | Tampering | Magic-byte check for `.pdf` (`%PDF`) and `.zip` (`PK\x03\x04`) before processing | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | API |
| T-07 | Prompt injection via file content | Uploaded file contains `Ignore previous instructions` | Spoofing | Regex-strip `ignore/disregard previous`, `system:`, `assistant:`, `you are now` patterns | ✅ Partial (`feat/api-fpa-ollama`) — see gap T-07a | API |
| T-07a | Prompt injection via filename (control chars / newlines) | Archive member named `\nSYSTEM: you are now…` | Spoofing | Strip Unicode control categories (Cc/Cf/Cn/Co/Cs) from filename before embedding in prompt | ✅ Fixed (`fix/security-hardening-prompt-and-upload-size`) | API |
| T-08 | DoS via concurrent Ollama analysis jobs | Flood POST /analyze from single IP | DoS | Rate limit 10 req/min per IP via `slowapi` | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | API |
| T-09 | CORS wildcard — cross-origin credential theft | JS from arbitrary origin calls API | Info Disclosure | `cors_origins` env var; default `http://localhost:3000`; `allow_credentials=False` | ✅ Fixed (`feat/api-fpa-ollama`) | API |
| T-10 | HTTP header information leak (`Server`, MIME sniffing) | Any HTTP response | Info Disclosure | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, remove `Server` | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | API |
| T-11 | Clickjacking on frontend | Embed app in malicious iframe | Spoofing | `Content-Security-Policy: frame-ancestors 'none'` + `X-Frame-Options` in Next.js headers | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | Web |
| T-12 | XSS in frontend via injected results | LLM response with `<script>` echoed | XSS | React escapes by default; `Content-Security-Policy: script-src 'self'` blocks inline scripts | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | Web |
| T-13 | Internal exception message leak to client | Unexpected exception exposes stack trace | Info Disclosure | Replace `str(exc)` with generic `"internal error"` for non-domain exceptions | ✅ Fixed (`fix/security-headers-ratelimit-mime`) | API |
| T-14 | No transport-layer body size cap (Uvicorn not configured) | Bypass app-level check via ASGI trick | DoS | Start Uvicorn with `--limit-max-request-body-size 52428800` | ⚠️ **Pending** — deployment config | DevOps |
| T-15 | Job result accessible without auth (UUID enumeration) | Brute-force UUID space | Info Disclosure | Job IDs are UUIDv4 (122 bits entropy); acceptable for local/intranet use | ✅ Accepted risk (MVP scope) | API |
| T-16 | Prompt injection via Unicode homoglyphs | `Ιgnore` (Greek Iota) bypasses regex | Spoofing | Current regex covers common patterns; homoglyph stripping is future hardening | ⚠️ Residual risk — low | API |
| T-17 | SSRF via Ollama URL misconfiguration | `OLLAMA_URL=http://169.254.169.254/` | SSRF | `ollama_url` is server-side env var only; no user-controlled input | ✅ Accepted risk (env-only config) | API |

---

## Security Controls Summary

### Implemented

| Control | Location | Notes |
|---------|----------|-------|
| Upload size limit (50 MB) | `app/main.py` | Streamed, not buffered |
| ZIP slip guard | `app/ingest/extractor.py` | Path resolve + root containment |
| ZIP bomb guard | `app/ingest/extractor.py` | Member count + decompressed bytes caps |
| Magic-byte file validation | `app/ingest/extractor.py` | PDF (`%PDF`) + ZIP (`PK\x03\x04`) signatures checked before processing |
| PDF page cap (500 pages) | `app/ingest/extractor.py` | `maxpages=500` passed to pdfminer |
| Prompt injection sanitization | `app/llm/prompt.py` | Regex strip + filename control-char sanitization |
| Ollama timeout (300 s default) | `app/llm/ollama.py` | Configurable via `OLLAMA_TIMEOUT_SECONDS` |
| Ollama schema validation | `app/llm/ollama.py` | Pydantic + retry loop |
| Rate limiting (10/min per IP) | `app/main.py` | `slowapi` on `POST /analyze` |
| CORS allowlist | `app/main.py` | Env-configured, no wildcard |
| HTTP security headers | `app/main.py` | nosniff, no-frame, referrer-policy, no-store, removes Server header |
| Frontend CSP + frame headers | `apps/web/next.config.mjs` | `script-src 'self'`, `frame-ancestors 'none'`, nosniff, X-Frame-Options |
| Generic error messages | `app/main.py` | Unexpected exceptions return `"internal error"` only; detail logged server-side |
| No PII in logs | `app/main.py`, `app/jobs/store.py` | job_id only |
| Temp file cleanup | `app/ingest/extractor.py` | `TemporaryDirectory()` context manager |

### Pending / Recommended

| Action | Severity | Owner |
|--------|----------|-------|
| Add `--limit-max-request-body-size 52428800` to Uvicorn startup command | High | DevOps |
| Consider `OLLAMA_URL` network policy (isolate LLM from internet) | Medium | DevOps |
| Periodic audit of `pdfminer.six` for CVEs | Low | Maintainer |

---

## Secrets Management

- No secrets in code.
- All sensitive config (`OLLAMA_URL`, `CORS_ORIGINS`) via env vars / `.env` (gitignored).
- No credentials in logs.

## Residual Risks

1. **T-14** — Uvicorn body size limit not set at transport layer. App-level guard fires first in practice, but ASGI layer is unprotected if app startup fails.  
2. **T-16** — Homoglyph-based prompt injection not blocked. Pydantic schema validation is the last line of defense.
