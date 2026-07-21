# PyVault — Security Model & Threat Model

> Draft. Expanded alongside the Phase 1 crypto core and finalized in Phase 5.

## Design goals

- Confidentiality and integrity of the vault **at rest**.
- No plaintext secrets or keys written to disk.
- Safe to store the vault file in an untrusted-sync location (Dropbox/iCloud/Drive),
  i.e. an attacker who obtains the file cannot read or silently tamper with it
  without the master password.

## Cryptography

- **Key derivation:** Argon2id (memory-hard) from the master password with a
  random per-vault 16-byte salt. Parameters tuned per machine; stored (non-secret)
  in the vault header so the file is portable.
- **Encryption:** AES-256-GCM. The GCM authentication tag provides tamper
  detection — a modified or corrupted file fails to decrypt rather than returning
  garbage. A wrong master password is indistinguishable from a tampered file
  (both fail authentication), which is the desired behavior.
- **Randomness:** Python's `secrets` / OS CSPRNG for salts, nonces, and generated
  passwords. A fresh random nonce is used for every save.

## File handling

- **Atomic writes:** write to a temp file, `fsync`, then `os.replace` over the
  target so a crash or sync mid-write cannot corrupt the vault.
- **Backups:** keep a rolling `.bak` of the previous good vault.
- **Sync-conflict awareness:** detect and warn on conflicted copies created by
  cloud sync clients.

## In-use defenses

- Auto-lock (zeroize the in-memory key) after an inactivity timeout.
- Clipboard auto-clear a short time after copying a secret.

## Breach checking (Have I Been Pwned)

The optional online audit checks passwords against the HIBP Pwned Passwords
dataset using **k-anonymity**:

- The password is SHA-1 hashed **locally**; only the first 5 hex characters of
  that hash are sent to the API. Hundreds of thousands of passwords share any
  given prefix, so the service cannot determine which password was checked, or
  for which entry.
- The `Add-Padding` header randomizes the response size to defeat traffic
  analysis.
- SHA-1 is used only because it is the HIBP dataset's index; it protects nothing.
- It is strictly **opt-in** (a button / `--online` flag), never automatic, and
  makes an outbound HTTPS request to a third party only when invoked.

Offline audit checks (weak, reused) send nothing over the network.

## Explicit non-goals (v1)

- Defending against a **compromised host**: keyloggers, malware, or memory
  scraping while the vault is unlocked are out of scope.
- Browser autofill / integration.
- Multi-user or shared vaults.
- Hiding metadata such as the number of entries or the vault's size.
