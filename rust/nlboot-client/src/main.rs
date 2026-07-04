use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use clap::{Parser, Subcommand};
use rsa::pkcs8::DecodePublicKey;
use rsa::pss::{Signature, VerifyingKey};
use rsa::signature::Verifier;
use rsa::RsaPublicKey;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command as ProcessCommand;

const FIPS_READY_ALGORITHM: &str = "rsa-pss-sha256";
const FIPS_READY_PROFILE: &str = "fips-140-3-compatible";

#[derive(Parser, Debug)]
#[command(name = "nlboot-client")]
#[command(about = "NLBoot Rust safe boot/recovery client", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Build a safe, non-executing boot plan from manifest and token inputs.
    Plan {
        #[arg(long)]
        manifest: PathBuf,
        #[arg(long)]
        token: PathBuf,
        #[arg(long = "trusted-keys")]
        trusted_keys: PathBuf,
        #[arg(long = "require-fips", default_value_t = false)]
        require_fips: bool,
        #[arg(long)]
        now: Option<String>,
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Fetch and hash-verify planned artifacts into a content-addressed NLBoot cache.
    Fetch {
        #[arg(long)]
        plan: PathBuf,
        #[arg(long = "artifact-map")]
        artifact_map: PathBuf,
        #[arg(long)]
        cache: PathBuf,
        #[arg(long)]
        evidence: PathBuf,
    },
    /// Execute a gated platform handoff.
    Execute {
        #[arg(long)]
        plan: PathBuf,
        #[arg(long)]
        cache: PathBuf,
        #[arg(long)]
        adapter: String,
        #[arg(long = "load-only", default_value_t = false)]
        load_only: bool,
        #[arg(long = "exec", default_value_t = false)]
        exec_now: bool,
        #[arg(long)]
        evidence: PathBuf,
        #[arg(long = "i-understand-this-mutates-host", default_value_t = false)]
        mutation_ack: bool,
        #[arg(long = "i-understand-this-reboots-host", default_value_t = false)]
        reboot_ack: bool,
        #[arg(long = "dry-run", default_value_t = false)]
        dry_run: bool,
    },
}

#[derive(Debug, Deserialize)]
struct SignedBootManifest {
    manifest_id: String,
    boot_release_set_id: String,
    base_release_set_ref: String,
    boot_mode: String,
    artifacts: BTreeMap<String, String>,
    signature_ref: String,
    signer_ref: String,
    signature_algorithm: String,
    crypto_profile: String,
    signature_hex: String,
}

#[derive(Debug, Deserialize)]
struct EnrollmentToken {
    token_id: String,
    purpose: String,
    audience: Audience,
    release_set_ref: Option<String>,
    boot_release_set_ref: Option<String>,
    one_time_use: bool,
    issued_at: DateTime<Utc>,
    expires_at: DateTime<Utc>,
    status: String,
}

#[derive(Debug, Deserialize)]
struct Audience {
    subject_kind: String,
    subject_id: Option<String>,
}

#[derive(Debug, Deserialize)]
struct TrustedKeyDocument {
    keys: Vec<TrustedKey>,
}

#[derive(Debug, Deserialize)]
struct TrustedKey {
    key_ref: String,
    algorithm: String,
    public_key_pem: String,
    #[serde(default = "default_active_status")]
    status: String,
    not_before: Option<DateTime<Utc>>,
    not_after: Option<DateTime<Utc>>,
    revoked_at: Option<DateTime<Utc>>,
    revocation_reason: Option<String>,
}

fn default_active_status() -> String {
    "active".to_string()
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct BootPlan {
    action: String,
    manifest_id: String,
    boot_release_set_id: String,
    release_set_ref: String,
    artifacts: BTreeMap<String, String>,
    authorized_by: String,
    signature_algorithm: String,
    crypto_profile: String,
    policy_ref: String,
    allowed_operations: Vec<String>,
    proof_requirements: Vec<String>,
    offline_fallback: OfflineFallback,
    execute: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct OfflineFallback {
    enabled: bool,
    strategy: String,
    requires_signature_verification: bool,
    allows_unsigned_artifacts: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct PlanOutput {
    ok: bool,
    plan: BootPlan,
    implementation_note: String,
}

#[derive(Debug, Deserialize)]
struct ArtifactMap {
    artifact_map_id: String,
    artifacts: Vec<ArtifactDescriptor>,
}

#[derive(Debug, Deserialize, Clone)]
struct ArtifactDescriptor {
    artifact_ref: String,
    kind: String,
    source: String,
    sha256: String,
    size_bytes: Option<u64>,
    content_type: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct CachedArtifactRecord {
    artifact_ref: String,
    kind: String,
    sha256: String,
    size_bytes: u64,
    content_type: String,
    source: String,
    cache_path: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ArtifactCacheRecord {
    ok: bool,
    plan_manifest_id: String,
    boot_release_set_id: String,
    release_set_ref: String,
    artifact_map_id: String,
    created_at: DateTime<Utc>,
    artifacts: Vec<CachedArtifactRecord>,
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &PathBuf) -> Result<T> {
    let raw = fs::read_to_string(path).with_context(|| format!("failed to read {}", path.display()))?;
    let parsed = serde_json::from_str(&raw).with_context(|| format!("failed to parse JSON in {}", path.display()))?;
    Ok(parsed)
}

fn read_value(path: &PathBuf) -> Result<Value> {
    let raw = fs::read_to_string(path).with_context(|| format!("failed to read {}", path.display()))?;
    let parsed = serde_json::from_str(&raw).with_context(|| format!("failed to parse JSON in {}", path.display()))?;
    Ok(parsed)
}

fn write_json(path: &Path, value: &impl Serialize) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).with_context(|| format!("failed to create {}", parent.display()))?;
    }
    fs::write(path, serde_json::to_string_pretty(value)? + "\n")
        .with_context(|| format!("failed to write {}", path.display()))?;
    Ok(())
}

fn sort_value_keys(value: Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut entries: Vec<(String, Value)> = map
                .into_iter()
                .map(|(k, v)| (k, sort_value_keys(v)))
                .collect();
            entries.sort_by(|a, b| a.0.cmp(&b.0));
            Value::Object(entries.into_iter().collect())
        }
        Value::Array(arr) => Value::Array(arr.into_iter().map(sort_value_keys).collect()),
        other => other,
    }
}

fn canonical_manifest_payload(manifest_value: &Value) -> Result<Vec<u8>> {
    let mut unsigned = manifest_value
        .as_object()
        .cloned()
        .context("manifest must be a JSON object")?;
    unsigned.remove("signature_hex");
    let sorted = sort_value_keys(Value::Object(unsigned));
    Ok(serde_json::to_vec(&sorted)?)
}

fn validate_manifest_shape(manifest: &SignedBootManifest, require_fips: bool) -> Result<()> {
    if manifest.manifest_id.trim().is_empty() {
        anyhow::bail!("manifest_id must be non-empty");
    }
    if manifest.boot_release_set_id.trim().is_empty() {
        anyhow::bail!("boot_release_set_id must be non-empty");
    }
    if manifest.base_release_set_ref.trim().is_empty() {
        anyhow::bail!("base_release_set_ref must be non-empty");
    }
    if !matches!(manifest.boot_mode.as_str(), "installer" | "recovery" | "ephemeral" | "bootstrap") {
        anyhow::bail!("unsupported boot_mode={}", manifest.boot_mode);
    }
    for required in ["kernel_ref", "initrd_ref", "rootfs_ref"] {
        match manifest.artifacts.get(required) {
            Some(value) if !value.trim().is_empty() => {}
            _ => anyhow::bail!("artifacts missing required ref: {}", required),
        }
    }
    if !manifest.signature_ref.starts_with("urn:srcos:signature:") {
        anyhow::bail!("signature_ref must be a SourceOS signature URN");
    }
    if require_fips {
        if manifest.signature_algorithm != FIPS_READY_ALGORITHM || manifest.crypto_profile != FIPS_READY_PROFILE {
            anyhow::bail!("require-fips requires rsa-pss-sha256 and fips-140-3-compatible profile");
        }
    }
    if manifest.signer_ref.trim().is_empty() || manifest.signature_hex.trim().is_empty() {
        anyhow::bail!("manifest signer_ref and signature_hex must be non-empty");
    }
    Ok(())
}

fn validate_trusted_key_lifecycle(key: &TrustedKey, now: DateTime<Utc>) -> Result<()> {
    if key.key_ref.trim().is_empty() {
        anyhow::bail!("trusted key requires key_ref");
    }
    if key.algorithm != FIPS_READY_ALGORITHM {
        anyhow::bail!("trusted key must use rsa-pss-sha256");
    }
    if !key.public_key_pem.contains("BEGIN PUBLIC KEY") {
        anyhow::bail!("trusted key requires PEM public key");
    }
    if !matches!(key.status.as_str(), "active" | "retired" | "revoked") {
        anyhow::bail!("trusted key status must be active, retired, or revoked");
    }
    if key.status == "revoked" || key.revoked_at.is_some() {
        anyhow::bail!("trusted key {:?} is revoked", key.key_ref);
    }
    if key.status != "active" {
        anyhow::bail!("trusted key {:?} is not active", key.key_ref);
    }
    if let Some(not_before) = key.not_before {
        if now < not_before {
            anyhow::bail!("trusted key {:?} is not active yet", key.key_ref);
        }
    }
    if let Some(not_after) = key.not_after {
        if now >= not_after {
            anyhow::bail!("trusted key {:?} is expired", key.key_ref);
        }
    }
    if let Some(reason) = &key.revocation_reason {
        if reason.trim().is_empty() {
            anyhow::bail!("revocation_reason must be non-empty when present");
        }
    }
    Ok(())
}

fn trusted_key_for<'a>(trusted_keys: &'a TrustedKeyDocument, signer_ref: &str, now: DateTime<Utc>) -> Result<&'a TrustedKey> {
    for key in &trusted_keys.keys {
        if key.key_ref == signer_ref {
            validate_trusted_key_lifecycle(key, now)?;
            return Ok(key);
        }
    }
    anyhow::bail!("no trusted key for signer_ref={:?}", signer_ref);
}

fn verify_rsa_pss_sha256(payload: &[u8], signature_hex: &str, key: &TrustedKey) -> Result<()> {
    let signature_bytes = hex::decode(signature_hex).context("signature_hex must be hex")?;
    let public_key = RsaPublicKey::from_public_key_pem(&key.public_key_pem)
        .context("failed to parse trusted key PEM")?;
    let verifying_key = VerifyingKey::<Sha256>::new(public_key);
    let sig = Signature::try_from(signature_bytes.as_slice())
        .map_err(|e| anyhow::anyhow!("invalid signature bytes: {}", e))?;
    verifying_key
        .verify(payload, &sig)
        .map_err(|_| anyhow::anyhow!("signature verification failed"))?;
    Ok(())
}

fn validate_manifest(
    manifest: &SignedBootManifest,
    manifest_value: &Value,
    require_fips: bool,
    trusted_keys: &TrustedKeyDocument,
    now: DateTime<Utc>,
) -> Result<()> {
    validate_manifest_shape(manifest, require_fips)?;
    let trusted_key = trusted_key_for(trusted_keys, &manifest.signer_ref, now)?;
    if trusted_key.algorithm != manifest.signature_algorithm {
        anyhow::bail!("trusted key algorithm does not match manifest");
    }
    let payload = canonical_manifest_payload(manifest_value)?;
    verify_rsa_pss_sha256(&payload, &manifest.signature_hex, trusted_key)?;
    Ok(())
}

fn validate_token(token: &EnrollmentToken, manifest: &SignedBootManifest, now: DateTime<Utc>) -> Result<()> {
    if token.token_id.trim().is_empty() {
        anyhow::bail!("token_id must be non-empty");
    }
    if !matches!(token.purpose.as_str(), "enroll" | "boot" | "repair" | "recovery") {
        anyhow::bail!("unsupported purpose={}", token.purpose);
    }
    if token.status != "issued" {
        anyhow::bail!("token status must be issued, got {}", token.status);
    }
    if now >= token.expires_at {
        anyhow::bail!("token is expired");
    }
    if token.issued_at >= token.expires_at {
        anyhow::bail!("issued_at must be before expires_at");
    }
    if !token.one_time_use {
        anyhow::bail!("token must be one-time use");
    }
    if token.boot_release_set_ref.as_deref() != Some(manifest.boot_release_set_id.as_str()) {
        anyhow::bail!("token boot_release_set_ref does not match manifest");
    }
    if token.release_set_ref.as_deref() != Some(manifest.base_release_set_ref.as_str()) {
        anyhow::bail!("token release_set_ref does not match manifest base release");
    }
    let valid = match manifest.boot_mode.as_str() {
        "recovery" => matches!(token.purpose.as_str(), "recovery" | "repair"),
        "installer" => matches!(token.purpose.as_str(), "enroll" | "boot"),
        "ephemeral" => token.purpose == "boot",
        "bootstrap" => matches!(token.purpose.as_str(), "enroll" | "boot"),
        _ => false,
    };
    if !valid {
        anyhow::bail!("token purpose {} is not valid for boot_mode {}", token.purpose, manifest.boot_mode);
    }
    if token.audience.subject_kind.trim().is_empty() {
        anyhow::bail!("audience.subject_kind must be non-empty");
    }
    if let Some(subject_id) = &token.audience.subject_id {
        if subject_id.trim().is_empty() {
            anyhow::bail!("audience.subject_id must be non-empty when present");
        }
    }
    Ok(())
}

fn action_for_mode(mode: &str) -> &'static str {
    match mode {
        "recovery" => "boot-recovery",
        "installer" => "boot-installer",
        "ephemeral" => "boot-ephemeral",
        "bootstrap" => "bootstrap-only",
        _ => "present-menu",
    }
}

fn operations_for_mode(mode: &str) -> Vec<String> {
    let ops: &[&str] = match mode {
        "recovery" => &["present-menu", "verify-artifacts", "plan-recovery", "plan-rollback"],
        "installer" => &["present-menu", "verify-artifacts", "plan-install"],
        "ephemeral" => &["present-menu", "verify-artifacts", "plan-ephemeral-boot"],
        "bootstrap" => &["present-menu", "verify-artifacts", "plan-bootstrap"],
        _ => &["present-menu"],
    };
    ops.iter().map(|s| s.to_string()).collect()
}

fn proof_requirements_for_mode(mode: &str) -> Vec<String> {
    let mut reqs = vec![
        "verified_manifest_signature".to_string(),
        "validated_one_time_token".to_string(),
        "artifact_ref_manifest".to_string(),
        "boot_plan_record".to_string(),
    ];
    if matches!(mode, "recovery" | "installer") {
        reqs.push("device_claim_record".to_string());
        reqs.push("post_action_fingerprint".to_string());
    } else {
        reqs.push("session_fingerprint".to_string());
    }
    reqs
}

fn fallback_for_mode(mode: &str) -> OfflineFallback {
    let enabled = matches!(mode, "recovery" | "ephemeral");
    OfflineFallback {
        enabled,
        strategy: if enabled { "last-known-good-signed-boot-release-set" } else { "none" }.to_string(),
        requires_signature_verification: true,
        allows_unsigned_artifacts: false,
    }
}

fn build_plan(manifest: SignedBootManifest, token: EnrollmentToken) -> BootPlan {
    BootPlan {
        action: action_for_mode(&manifest.boot_mode).to_string(),
        manifest_id: manifest.manifest_id,
        boot_release_set_id: manifest.boot_release_set_id,
        release_set_ref: manifest.base_release_set_ref,
        artifacts: manifest.artifacts,
        authorized_by: token.token_id,
        signature_algorithm: manifest.signature_algorithm,
        crypto_profile: manifest.crypto_profile,
        policy_ref: format!("policy://sourceos/nlboot/{}/safe-plan-v1", manifest.boot_mode),
        allowed_operations: operations_for_mode(&manifest.boot_mode),
        proof_requirements: proof_requirements_for_mode(&manifest.boot_mode),
        offline_fallback: fallback_for_mode(&manifest.boot_mode),
        execute: false,
    }
}

fn parse_now(now: Option<String>) -> Result<DateTime<Utc>> {
    match now {
        Some(value) => Ok(DateTime::parse_from_rfc3339(&value)?.with_timezone(&Utc)),
        None => Ok(Utc::now()),
    }
}

fn load_plan(path: &PathBuf) -> Result<BootPlan> {
    let value = read_value(path)?;
    if value.get("plan").is_some() {
        let output: PlanOutput = serde_json::from_value(value).context("failed to parse plan output")?;
        return Ok(output.plan);
    }
    let plan: BootPlan = serde_json::from_value(value).context("failed to parse boot plan")?;
    Ok(plan)
}

fn sha256_hex(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hex::encode(hasher.finalize())
}

fn read_artifact_source(source: &str, artifact_map_path: &Path) -> Result<Vec<u8>> {
    if source.starts_with("https://") || source.starts_with("http://") {
        let response = reqwest::blocking::get(source).with_context(|| format!("failed to fetch {source}"))?;
        if !response.status().is_success() {
            anyhow::bail!("artifact fetch failed for {source}: HTTP {}", response.status());
        }
        return Ok(response.bytes()?.to_vec());
    }
    let base = artifact_map_path.parent().unwrap_or_else(|| Path::new("."));
    let path = base.join(source);
    fs::read(&path).with_context(|| format!("failed to read artifact source {}", path.display()))
}

fn write_refusal(evidence_dir: &Path, reason: &str) {
    let record = json!({
        "ok": false,
        "kind": "refusal-record",
        "created_at": Utc::now(),
        "reason": reason,
    });
    let _ = fs::create_dir_all(evidence_dir);
    let _ = fs::write(evidence_dir.join("refusal-record.json"), serde_json::to_string_pretty(&record).unwrap_or_else(|_| "{}".to_string()) + "\n");
}

fn plan_key_to_artifact_kind(plan_key: &str) -> Result<&str> {
    match plan_key {
        "kernel_ref" => Ok("kernel"),
        "initrd_ref" => Ok("initrd"),
        "rootfs_ref" => Ok("rootfs"),
        other => anyhow::bail!("unsupported artifact key in plan: {other}"),
    }
}

fn fetch_artifacts(plan_path: PathBuf, artifact_map_path: PathBuf, cache: PathBuf, evidence: PathBuf) -> Result<()> {
    let plan = load_plan(&plan_path)?;
    let artifact_map: ArtifactMap = read_json(&artifact_map_path)?;
    fs::create_dir_all(&cache).with_context(|| format!("failed to create cache {}", cache.display()))?;
    fs::create_dir_all(&evidence).with_context(|| format!("failed to create evidence dir {}", evidence.display()))?;

    let mut cached = Vec::new();
    for (plan_key, artifact_ref) in &plan.artifacts {
        let expected_kind = plan_key_to_artifact_kind(plan_key)?;
        let descriptor = artifact_map
            .artifacts
            .iter()
            .find(|candidate| &candidate.artifact_ref == artifact_ref)
            .with_context(|| format!("artifact ref {artifact_ref} missing from artifact map"))?;
        if descriptor.kind != expected_kind {
            anyhow::bail!("artifact kind mismatch for {artifact_ref}: plan key expects {expected_kind}, map has {}", descriptor.kind);
        }
        let bytes = read_artifact_source(&descriptor.source, &artifact_map_path)?;
        let actual_sha256 = sha256_hex(&bytes);
        if actual_sha256 != descriptor.sha256 {
            anyhow::bail!("sha256 mismatch for {artifact_ref}: expected {}, got {actual_sha256}", descriptor.sha256);
        }
        if let Some(expected_size) = descriptor.size_bytes {
            if bytes.len() as u64 != expected_size {
                anyhow::bail!("size mismatch for {artifact_ref}: expected {expected_size}, got {}", bytes.len());
            }
        }
        let cache_path = cache.join(format!("{}-{}", descriptor.kind, descriptor.sha256));
        fs::write(&cache_path, &bytes).with_context(|| format!("failed to write cache artifact {}", cache_path.display()))?;
        cached.push(CachedArtifactRecord {
            artifact_ref: descriptor.artifact_ref.clone(),
            kind: descriptor.kind.clone(),
            sha256: descriptor.sha256.clone(),
            size_bytes: bytes.len() as u64,
            content_type: descriptor.content_type.clone(),
            source: descriptor.source.clone(),
            cache_path: cache_path.display().to_string(),
        });
    }

    let record = ArtifactCacheRecord {
        ok: true,
        plan_manifest_id: plan.manifest_id.clone(),
        boot_release_set_id: plan.boot_release_set_id.clone(),
        release_set_ref: plan.release_set_ref.clone(),
        artifact_map_id: artifact_map.artifact_map_id,
        created_at: Utc::now(),
        artifacts: cached,
    };
    write_json(&evidence.join("artifact-cache-record.json"), &record)?;
    println!("{}", serde_json::to_string_pretty(&record)?);
    Ok(())
}

fn artifact_record_by_kind<'a>(record: &'a ArtifactCacheRecord, kind: &str) -> Result<&'a CachedArtifactRecord> {
    record
        .artifacts
        .iter()
        .find(|artifact| artifact.kind == kind)
        .with_context(|| format!("cached {kind} artifact missing"))
}

fn is_root() -> bool {
    unsafe { libc::geteuid() == 0 }
}

fn load_cache_record(evidence: &Path) -> Result<ArtifactCacheRecord> {
    let cache_record_path = evidence.join("artifact-cache-record.json");
    read_json(&cache_record_path)
        .with_context(|| format!("missing artifact cache evidence at {}", cache_record_path.display()))
}

fn verify_cached_kernel_initrd(cache: &Path, evidence: &Path) -> Result<(CachedArtifactRecord, CachedArtifactRecord)> {
    let cache_record = load_cache_record(evidence)?;
    let kernel = artifact_record_by_kind(&cache_record, "kernel")?.clone();
    let initrd = artifact_record_by_kind(&cache_record, "initrd")?.clone();
    let kernel_path = PathBuf::from(&kernel.cache_path);
    let initrd_path = PathBuf::from(&initrd.cache_path);
    if !kernel_path.starts_with(cache) || !initrd_path.starts_with(cache) {
        anyhow::bail!("cached artifact path is outside provided cache directory");
    }
    for artifact in [&kernel, &initrd] {
        let bytes = fs::read(&artifact.cache_path).with_context(|| format!("failed to read cached artifact {}", artifact.cache_path))?;
        let actual = sha256_hex(&bytes);
        if actual != artifact.sha256 {
            anyhow::bail!("cached artifact hash mismatch for {}", artifact.artifact_ref);
        }
    }
    Ok((kernel, initrd))
}

fn require_mutation_ack(evidence: &Path, mutation_ack: bool) -> Result<()> {
    if !mutation_ack {
        write_refusal(evidence, "missing explicit host-mutation acknowledgement");
        anyhow::bail!("refusing host mutation without --i-understand-this-mutates-host");
    }
    Ok(())
}

fn require_root_or_dry_run(evidence: &Path, dry_run: bool, operation: &str) -> Result<()> {
    if !dry_run && !is_root() {
        write_refusal(evidence, &format!("{operation} requires root or equivalent capability"));
        anyhow::bail!("{operation} requires root or equivalent capability");
    }
    Ok(())
}

fn execute_linux_kexec_load_only(plan_path: PathBuf, cache: PathBuf, evidence: PathBuf, mutation_ack: bool, dry_run: bool) -> Result<()> {
    require_mutation_ack(&evidence, mutation_ack)?;
    require_root_or_dry_run(&evidence, dry_run, "linux-kexec load-only")?;
    let plan = load_plan(&plan_path)?;
    let (kernel, initrd) = verify_cached_kernel_initrd(&cache, &evidence)?;

    let command = vec![
        "kexec".to_string(),
        "--load".to_string(),
        kernel.cache_path.clone(),
        "--initrd".to_string(),
        initrd.cache_path.clone(),
    ];
    let proof = json!({
        "ok": true,
        "kind": "pre-exec-proof",
        "created_at": Utc::now(),
        "adapter": "linux-kexec",
        "mode": "load-only",
        "dry_run": dry_run,
        "plan_manifest_id": plan.manifest_id,
        "boot_release_set_id": plan.boot_release_set_id,
        "release_set_ref": plan.release_set_ref,
        "command": command,
        "execute_exec": false
    });
    write_json(&evidence.join("pre-exec-proof.json"), &proof)?;

    if dry_run {
        println!("{}", serde_json::to_string_pretty(&proof)?);
        return Ok(());
    }

    let status = ProcessCommand::new("kexec")
        .arg("--load")
        .arg(&kernel.cache_path)
        .arg("--initrd")
        .arg(&initrd.cache_path)
        .status()
        .context("failed to invoke kexec --load")?;
    if !status.success() {
        anyhow::bail!("kexec --load failed with status {status}");
    }
    println!("{}", serde_json::to_string_pretty(&proof)?);
    Ok(())
}

fn execute_linux_kexec_exec(plan_path: PathBuf, cache: PathBuf, evidence: PathBuf, mutation_ack: bool, reboot_ack: bool, dry_run: bool) -> Result<()> {
    require_mutation_ack(&evidence, mutation_ack)?;
    if !reboot_ack {
        write_refusal(&evidence, "missing explicit reboot acknowledgement");
        anyhow::bail!("refusing kexec --exec without --i-understand-this-reboots-host");
    }
    require_root_or_dry_run(&evidence, dry_run, "linux-kexec exec")?;
    let plan = load_plan(&plan_path)?;
    let _ = verify_cached_kernel_initrd(&cache, &evidence)?;
    let pre_exec_path = evidence.join("pre-exec-proof.json");
    if !pre_exec_path.exists() {
        write_refusal(&evidence, "missing pre-exec-proof.json from prior load-only phase");
        anyhow::bail!("missing pre-exec-proof.json from prior load-only phase");
    }

    let command = vec!["kexec".to_string(), "--exec".to_string()];
    let proof = json!({
        "ok": true,
        "kind": "exec-proof",
        "created_at": Utc::now(),
        "adapter": "linux-kexec",
        "mode": "exec",
        "dry_run": dry_run,
        "plan_manifest_id": plan.manifest_id,
        "boot_release_set_id": plan.boot_release_set_id,
        "release_set_ref": plan.release_set_ref,
        "command": command,
        "execute_exec": true
    });
    write_json(&evidence.join("exec-proof.json"), &proof)?;

    if dry_run {
        println!("{}", serde_json::to_string_pretty(&proof)?);
        return Ok(());
    }

    let status = ProcessCommand::new("kexec")
        .arg("--exec")
        .status()
        .context("failed to invoke kexec --exec")?;
    if !status.success() {
        anyhow::bail!("kexec --exec failed with status {status}");
    }
    Ok(())
}

fn execute_m2_adapter_dry_run(plan_path: PathBuf, evidence: PathBuf, mutation_ack: bool, dry_run: bool) -> Result<()> {
    require_mutation_ack(&evidence, mutation_ack)?;
    if !dry_run {
        write_refusal(&evidence, "m2 adapter proof currently requires dry-run mode");
        anyhow::bail!("m2 adapter proof currently requires dry-run mode");
    }
    let plan = load_plan(&plan_path)?;
    fs::create_dir_all(&evidence).with_context(|| format!("failed to create evidence dir {}", evidence.display()))?;
    let adapter_record = json!({
        "ok": true,
        "kind": "adapter-plan-record",
        "created_at": Utc::now(),
        "adapter": "apple-silicon-m2",
        "mode": "recovery-entry-dry-run",
        "dry_run": true,
        "plan_manifest_id": plan.manifest_id,
        "boot_release_set_id": plan.boot_release_set_id,
        "release_set_ref": plan.release_set_ref,
        "mutation_performed": false,
        "portable_core_preserved": true
    });
    let entry_record = json!({
        "ok": true,
        "kind": "boot-entry-record",
        "created_at": Utc::now(),
        "adapter": "apple-silicon-m2",
        "entries": [
            {
                "id": "sourceos-normal",
                "label": "SourceOS",
                "role": "normal",
                "boot_release_set_id": plan.boot_release_set_id,
                "release_set_ref": plan.release_set_ref,
                "mutation_performed": false
            },
            {
                "id": "sourceos-recovery-installer",
                "label": "SourceOS Recovery/Installer",
                "role": "recovery-installer",
                "boot_release_set_id": plan.boot_release_set_id,
                "release_set_ref": plan.release_set_ref,
                "mutation_performed": false
            }
        ]
    });
    write_json(&evidence.join("adapter-plan-record.json"), &adapter_record)?;
    write_json(&evidence.join("boot-entry-record.json"), &entry_record)?;
    println!("{}", serde_json::to_string_pretty(&adapter_record)?);
    Ok(())
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Plan { manifest, token, trusted_keys, require_fips, now, out } => {
            let manifest_value = read_value(&manifest)?;
            let manifest_doc: SignedBootManifest = serde_json::from_value(manifest_value.clone())
                .with_context(|| format!("failed to parse manifest object in {}", manifest.display()))?;
            let token_doc: EnrollmentToken = read_json(&token)?;
            let trusted_keys_doc: TrustedKeyDocument = read_json(&trusted_keys)?;
            let now = parse_now(now)?;
            validate_manifest(&manifest_doc, &manifest_value, require_fips, &trusted_keys_doc, now)?;
            validate_token(&token_doc, &manifest_doc, now)?;
            let plan = build_plan(manifest_doc, token_doc);
            let output = PlanOutput {
                ok: true,
                plan,
                implementation_note: "Rust planner verifies RSA-PSS/SHA-256 manifest signatures and remains non-mutating with execute=false.".to_string(),
            };
            if let Some(out_path) = out {
                write_json(&out_path, &output)?;
            }
            println!("{}", serde_json::to_string_pretty(&output)?);
        }
        Commands::Fetch { plan, artifact_map, cache, evidence } => {
            fetch_artifacts(plan, artifact_map, cache, evidence)?;
        }
        Commands::Execute { plan, cache, adapter, load_only, exec_now, evidence, mutation_ack, reboot_ack, dry_run } => {
            if load_only && exec_now {
                write_refusal(&evidence, "choose either --load-only or --exec, not both");
                anyhow::bail!("choose either --load-only or --exec, not both");
            }
            if adapter == "apple-silicon-m2" {
                if exec_now {
                    write_refusal(&evidence, "apple-silicon-m2 adapter does not support --exec in this proof lane");
                    anyhow::bail!("apple-silicon-m2 adapter does not support --exec in this proof lane");
                }
                if !load_only {
                    write_refusal(&evidence, "apple-silicon-m2 adapter requires --load-only dry-run proof mode");
                    anyhow::bail!("apple-silicon-m2 adapter requires --load-only dry-run proof mode");
                }
                execute_m2_adapter_dry_run(plan, evidence, mutation_ack, dry_run)?;
            } else if adapter == "linux-kexec" {
                if load_only {
                    execute_linux_kexec_load_only(plan, cache, evidence, mutation_ack, dry_run)?;
                } else if exec_now {
                    execute_linux_kexec_exec(plan, cache, evidence, mutation_ack, reboot_ack, dry_run)?;
                } else {
                    write_refusal(&evidence, "execute requires --load-only or --exec");
                    anyhow::bail!("execute requires --load-only or --exec");
                }
            } else {
                write_refusal(&evidence, "unsupported platform adapter");
                anyhow::bail!("unsupported adapter {adapter:?}; supported: linux-kexec, apple-silicon-m2");
            }
        }
    }
    Ok(())
}
