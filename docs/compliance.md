# Compliance & Legal Checklist

## GDPR Compliance (EU General Data Protection Regulation)

### Data Subject Rights

| Right | Implementation | Status |
|-------|----------------|--------|
| **Right to Access** | `/api/v1/user/export` - User can download all their data | ✅ |
| **Right to Rectification** | Users can edit captions, metadata via UI | ✅ |
| **Right to Erasure (Right to be Forgotten)** | `/api/v1/user/delete` - Soft delete (30d grace), then hard delete | ✅ |
| **Right to Data Portability** | Export includes photos + metadata in JSON (standard format) | ✅ |
| **Right to Restrict Processing** | Face recognition is explicit opt-in (user controls) | ✅ |
| **Right to Object** | User can disable face recognition; all embeddings deleted | ✅ |

### Data Processing Principles

- [x] **Lawfulness**: Service based on user consent (ToS acceptance at signup)
- [x] **Purpose Limitation**: Data used only for photo storage/management (stated in Privacy Policy)
- [x] **Data Minimization**: Only collect email, name, photos (no excessive data)
- [x] **Accuracy**: Users can correct metadata anytime
- [x] **Storage Limitation**: Soft-deleted data purged after 30 days
- [x] **Integrity**: TLS in-transit, AES-256 at-rest (B2 SSE)
- [x] **Accountability**: Audit logs track data deletion, exports

### Consent Management

**Privacy Policy**: Must include:
- What data we collect (photos, EXIF, optional face data)
- Why we collect it (photo storage, search, face grouping)
- How long we keep it (indefinitely unless deleted, 30-day grace period)
- Third parties (Backblaze for storage, Cloudflare for CDN)
- User rights (access, deletion, portability)

**Cookie Consent**:
- Essential cookies: `refresh_token` (auth) - cannot be disabled
- Analytics cookies: None (Cloudflare Web Analytics is privacy-preserving, no consent needed)

**Face Recognition Consent** (explicit opt-in):
> **Face Grouping (Optional)**
> 
> We use artificial intelligence to detect and group faces in your photos. This helps you find pictures of people you care about.
> 
> - ✅ Face data is stored securely and never shared
> - ✅ You can turn this off anytime, and all face data will be deleted within 24 hours
> - ✅ This feature is entirely optional and disabled by default
> 
> [ ] Enable Face Grouping

### Data Breach Notification

**Timeline** (GDPR Article 33):
- Notify Data Protection Authority (DPA) within **72 hours** of breach discovery
- Notify affected users "without undue delay" if high risk to user rights

**Procedure**:
1. Detect breach (e.g., unauthorized B2 access, DB dump leak)
2. Contain breach (rotate keys, revoke access)
3. Assess scope: How many users? What data?
4. Notify DPA: Email to [your country's DPA]
5. Notify users: Email template (see below)
6. Post-mortem: Fix vulnerability, update security

**Email Template**:
> Subject: Important Security Notice - PhotoBomb Data Breach
> 
> Dear [User],
> 
> We are writing to inform you of a security incident that may have affected your account.
> 
> **What Happened**: On [Date], we discovered unauthorized access to [system]. 
> **What Data Was Affected**: [e.g., email addresses, photo thumbnails (not originals)].
> **What We're Doing**: [e.g., We have rotated all credentials, notified authorities, and implemented additional security measures].
> **What You Should Do**: [e.g., Change your password immediately, enable 2FA].
> 
> We sincerely apologize for this incident and take full responsibility. If you have questions, please contact security@photobomb.app.

---

## CCPA Compliance (California Consumer Privacy Act)

### Consumer Rights

| Right | Implementation |
|-------|----------------|
| **Right to Know** | Privacy Policy discloses data collection practices |
| **Right to Delete** | Same as GDPR (30-day soft delete, then purge) |
| **Right to Opt-Out** | No data selling (N/A - we don't sell data) |
| **Right to Non-Discrimination** | No premium features locked behind data consent |

### "Do Not Sell My Personal Information"

**Verdict**: Not applicable - PhotoBomb does not sell user data.

**Privacy Policy Statement**:
> We do not sell your personal information to third parties. Your photos and metadata are stored solely for the purpose of providing our service.

---

## Terms of Service

### Required Clauses

- [x] **Acceptable Use**: No illegal content (CSAM, pirated media, hate speech)
- [x] **Content Ownership**: User retains copyright to photos; PhotoBomb has license to display
- [x] **Storage Quota**: 100 GB default, upgrades available
- [x] **Termination**: User can delete account anytime; PhotoBomb can terminate for ToS violations
- [x] **Liability Limitation**: Not liable for data loss (though backups are best-effort)
- [x] **Dispute Resolution**: Arbitration clause (optional, consult lawyer)

**Storage Quota Clause**:
> You are allocated 100 GB of storage. If you exceed this limit, you will be prompted to upgrade or delete photos. We reserve the right to suspend uploads if usage exceeds 120% of quota.

**Content License Clause**:
> You retain all ownership rights to your photos. By uploading, you grant PhotoBomb a non-exclusive, worldwide license to store, display, and share your photos as necessary to provide the service (e.g., generating thumbnails, serving shared links).

---

## Face Recognition Policy

### Transparency Requirements (Illinois BIPA, other states)

**Disclosure** (required before collection):
> **Biometric Data Notice**
> 
> If you enable Face Grouping, PhotoBomb will collect and store biometric data (face embeddings) from your photos. This data is used solely to group photos by person and is not shared with third parties.
> 
> - **Retention**: Face embeddings are stored indefinitely while the feature is enabled
> - **Deletion**: If you disable Face Grouping, all face embeddings are deleted within 24 hours
> - **Purpose**: Grouping photos by person to improve your search experience
> 
> By enabling this feature, you consent to the collection and storage of biometric data.

**Illinois BIPA Requirements**:
1. **Written consent**: User must check"I consent" box
2. **Retention policy**: "Data deleted within 3 years or when no longer needed (whichever is sooner)"
3. **Data destruction**: Must have written destruction policy

**Our Policy**:
> Face embeddings are retained as long as Face Grouping is enabled. Upon disabling, all embeddings are deleted within 24 hours. Users may also delete their account, triggering full data deletion within 30 days.

---

## Content Moderation

### Illegal Content (CSAM, etc.)

**Detection**: Use PhotoDNA or similar hash-based detection

**Procedure**:
1. Detected CSAM → immediate account suspension
2. Report to NCMEC (National Center for Missing & Exploited Children)
3. Preserve evidence (do not delete)
4. Coordinate with law enforcement

**Legal Requirement (US)**: § 2258A mandates reporting CSAM

### DMCA (Copyright Infringement)

**Procedure**:
1. Receive DMCA takedown notice at dmca@photobomb.app
2. Verify notice is valid (signature, good-faith statement)
3. Remove infringing content within 24 hours
4. Notify user (give chance to file counter-notice)
5. If no counter-notice within 10 days, content stays down

**Copyright Clause in ToS**:
> If you believe content on PhotoBomb infringes your copyright, please send a DMCA notice to dmca@photobomb.app with:
> - Your contact information
> - Description of copyrighted work
> - URL of infringing content
> - Statement of good faith belief

---

## Data Retention Policy

| Data Type | Retention Period | Reason |
|-----------|------------------|--------|
| **Active Photos** | Indefinite | User wants to keep |
| **Deleted Photos** | 30 days (soft delete) | Grace period to recover |
| **Account After Deletion** | 30 days | Grace period to recover |
| **Audit Logs** | 1 year (hot), then archive | Compliance, debugging |
| **Share Links (expired)** | 90 days | Analytics, abuse detection |
| **Failed Upload Sessions** | 7 days | Cleanup, reduce DB size |

**User-Facing Policy**:
> When you delete a photo, it moves to Trash and is kept for 30 days. After 30 days, it is permanently deleted and cannot be recovered. When you delete your account, all your data is permanently deleted after 30 days.

---

## International Compliance

### Brazil (LGPD - Lei Geral de Proteção de Dados)

**Similar to GDPR**:
- User rights (access, deletion, portability) - ✅ covered
- Consent-based processing - ✅ ToS acceptance
- Data Protection Officer (DPO) - Required if processing large volumes (assign if >100k users)

### Canada (PIPEDA)

**Requirements**:
- Consent for collection - ✅ ToS
- Access to personal info - ✅ Export feature
- Safeguard data - ✅ Encryption

### Japan (APPI - Act on the Protection of Personal Information)

**Requirements**:
- Notify users of data collection purpose - ✅ Privacy Policy
- Obtain consent for third-party sharing - N/A (we don't share)

---

## Checklist for Legal Review

**Before Launch**:
- [ ] Privacy Policy reviewed by lawyer (GDPR/CCPA compliance)
- [ ] Terms of Service reviewed by lawyer
- [ ] DMCA agent registered with US Copyright Office
- [ ] Data Processing Agreement (DPA) with Backblaze (if processing EU data)
- [ ] Cookie consent banner implemented (if targeting EU)
- [ ] Face recognition consent UI tested
- [ ] Data export feature tested (GDPR Article 20)
- [ ] Data deletion procedure tested (GDPR Article 17)

**Recurring** (Quarterly):
- [ ] Review audit logs for unusual activity
- [ ] Update Privacy Policy if new data processing (e.g., add ML features)
- [ ] Test data export (ensure format hasn't broken)
- [ ] Review user deletion requests (respond within 30 days)

---

## Implementation Notes

**Why 30-day soft delete?**
- Industry standard (Google Photos, iCloud, Dropbox)
- Balances user convenience (accidental deletion recovery) vs. compliance (timely deletion)

**Why explicit opt-in for face recognition?**
- Legal requirement in Illinois (BIPA) and other states
- Builds user trust (privacy-first approach)
- Reduces liability if biometric laws change

**Tradeoff: Data localization (Brazil, China, Russia)**
- Some countries require data stored locally
- **Our approach**: Start with US/EU storage (B2 US region)
- If expanding to Brazil/China: Use regional buckets (B2 supports EU/US/Asia)

**Alternative: Hire DPO**
- Required if processing > 100k EU users at scale
- Part-time consultant ($50k-100k/year) vs. full-time employee
- **Verdict**: Defer until 50k users; use legal counsel for now
