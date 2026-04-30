use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "nlboot-client")]
#[command(about = "NLBoot Rust safe planner scaffold", long_about = None)]
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

#[derive(Debug, Serialize)]
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

#[derive(Debug, Serialize)]
struct OfflineFallback {
    enabled: bool,
    strategy: String,
    requires_signature_verification: bool,
    allows_unsigned_artifacts: bool,
}

#[derive(Debug, Serialize)]
struct Output {
    ok: bool,
    plan: BootPlan,
    implementation_note: String,
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

fn validate_manifest(manifest: &SignedBootManifest, require_fips: bool, trusted_keys: &Value) -> Result<()> {
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
        if manifest.signature_algorithm != "rsa-pss-sha256" || manifest.crypto_profile != "fips-140-3-compatible" {
            anyhow::bail!("require-fips requires rsa-pss-sha256 and fips-140-3-compatible profile");
        }
    }
    if manifest.signer_ref.trim().is_empty() || manifest.signature_hex.trim().is_empty() {
        anyhow::bail!("manifest signer_ref and signature_hex must be non-empty");
    }
    if trusted_keys.get("trusted_keys").is_none() && trusted_keys.get("keys").is_none() {
        anyhow::bail!("trusted key document must contain trusted_keys or keys");
    }
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

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Plan { manifest, token, trusted_keys, require_fips, now } => {
            let manifest_doc: SignedBootManifest = read_json(&manifest)?;
            let token_doc: EnrollmentToken = read_json(&token)?;
            let trusted_keys_doc = read_value(&trusted_keys)?;
            let now = parse_now(now)?;
            validate_manifest(&manifest_doc, require_fips, &trusted_keys_doc)?;
            validate_token(&token_doc, &manifest_doc, now)?;
            let plan = build_plan(manifest_doc, token_doc);
            let output = Output {
                ok: true,
                plan,
                implementation_note: "Rust scaffold validates manifest shape and token binding; RSA-PSS signature verification parity is required before production use.".to_string(),
            };
            println!("{}", serde_json::to_string_pretty(&output)?);
        }
    }
    Ok(())
}
