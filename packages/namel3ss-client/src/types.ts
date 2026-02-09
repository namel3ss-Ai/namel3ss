export const CONTRACT_VERSION = "runtime-ui@1" as const;
export const HEADLESS_API_VERSION = "v1" as const;

export type ContractVersion = typeof CONTRACT_VERSION;
export type HeadlessApiVersion = typeof HEADLESS_API_VERSION;

export interface RuntimeError {
  category: string;
  message: string;
  hint: string;
  origin: string;
  stable_code: string;
}

export interface ContractWarning {
  code: string;
  path: string;
  message: string;
  expected?: string;
  actual?: string;
}

export interface CapabilityPack {
  name: string;
  version: string;
  provided_actions?: string[];
  required_permissions?: string[];
  runtime_bindings?: Record<string, unknown>;
  effect_capabilities?: string[];
  contract_version: string;
  purity: string;
  replay_mode: string;
}

export interface CapabilityUsage {
  pack_name: string;
  pack_version: string;
  action: string;
  capability: string;
  status: string;
  reason?: string;
  purity: string;
  replay_mode: string;
  required_permissions?: string[];
}

export interface AuditPolicyStatus {
  mode: "required" | "optional" | "forbidden";
  required: boolean;
  forbidden: boolean;
  attempted: boolean;
  written: boolean;
  error?: string;
}

export interface PersistenceBackend {
  target: string;
  kind: string;
  enabled: boolean;
  durable: boolean;
  deterministic_ordering: boolean;
  descriptor?: string;
  requires_network?: boolean;
  replicas?: string[];
  [key: string]: unknown;
}

export interface MigrationStatus {
  schema_version: string;
  state_schema_version: string;
  plan_id: string;
  last_plan_id: string;
  applied_plan_id: string;
  pending: boolean;
  breaking: boolean;
  reversible: boolean;
  plan_changed: boolean;
  change_count: number;
  error?: string;
  [key: string]: unknown;
}

export interface AuditBundle {
  schema_version: string;
  run_id: string;
  integrity_hash: string;
  run_artifact_path: string;
  bundle_path: string;
  [key: string]: unknown;
}

export interface RunArtifact {
  schema_version: string;
  run_id: string;
  program?: Record<string, unknown>;
  inputs?: Record<string, unknown>;
  ingestion_artifacts?: Record<string, unknown>;
  retrieval_plan?: RetrievalPlan;
  retrieval_trace?: RetrievalTraceEntry[];
  trust_score_details?: TrustScoreDetails;
  prompt?: Record<string, unknown>;
  model_config?: Record<string, unknown>;
  capabilities_enabled?: CapabilityPack[];
  capability_versions?: Record<string, string>;
  capability_usage?: CapabilityUsage[];
  output?: unknown;
  runtime_errors?: RuntimeError[];
  checksums?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface IngestionReasonDetail {
  code: string;
  message: string;
  remediation: string;
}

export interface IngestionStatus {
  status: "pass" | "warn" | "block";
  reasons: string[];
  details?: IngestionReasonDetail[];
  fallback_used?: "ocr" | null;
}

export interface RetrievalTraceEntry {
  chunk_id: string;
  document_id: string;
  page_number: number;
  score: number;
  rank: number;
  reason: string;
  upload_id?: string;
  ingestion_phase?: string;
  quality?: string;
  [key: string]: unknown;
}

export interface RetrievalPlan {
  query: string;
  scope?: Record<string, unknown>;
  tier?: Record<string, unknown>;
  filters?: Record<string, unknown>[];
  cutoffs?: Record<string, unknown>;
  ordering?: string;
  selected_chunk_ids?: string[];
  selected_scores?: Record<string, unknown>[];
  [key: string]: unknown;
}

export interface TrustScoreDetails {
  formula_version: string;
  score: number;
  level: string;
  inputs?: Record<string, unknown>;
  components?: Record<string, unknown>[];
  penalties?: Record<string, unknown>[];
  [key: string]: unknown;
}

export interface RetrievalState {
  retrieval_plan?: RetrievalPlan;
  retrieval_trace?: RetrievalTraceEntry[];
  trust_score_details?: TrustScoreDetails;
  [key: string]: unknown;
}

export interface UploadRecord {
  id?: string;
  name?: string;
  type?: string;
  size?: number;
  checksum?: string;
  [key: string]: unknown;
}

export interface RagStateValues {
  uploads?: Record<string, Record<string, UploadRecord>>;
  ingestion?: Record<string, IngestionStatus>;
  retrieval?: RetrievalState;
  chat?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface UiState {
  current_page?: string;
  values: RagStateValues;
  errors: Record<string, unknown>[];
}

export interface ManifestPage {
  name?: string;
  slug?: string;
  elements?: Record<string, unknown>[];
  layout?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface UiManifest {
  ok?: boolean;
  pages: ManifestPage[];
  actions?: Record<string, unknown>;
  upload_requests?: Record<string, unknown>[];
  warnings?: Record<string, unknown>[];
  mode?: string;
  theme?: Record<string, unknown>;
  runtime_error?: RuntimeError;
  runtime_errors?: RuntimeError[];
  capabilities_enabled?: CapabilityPack[];
  capability_versions?: Record<string, string>;
  persistence_backend?: PersistenceBackend;
  state_schema_version?: string;
  migration_status?: MigrationStatus;
  run_artifact?: RunArtifact;
  audit_bundle?: AuditBundle;
  audit_policy_status?: AuditPolicyStatus;
  [key: string]: unknown;
}

export interface HeadlessUiResponse {
  ok: boolean;
  api_version: HeadlessApiVersion;
  contract_version: ContractVersion;
  manifest?: UiManifest;
  hash?: string;
  revision?: string;
  state?: UiState;
  actions?: Record<string, unknown>;
  error?: Record<string, unknown>;
  runtime_error?: RuntimeError;
  runtime_errors?: RuntimeError[];
  capabilities_enabled?: CapabilityPack[];
  capability_versions?: Record<string, string>;
  persistence_backend?: PersistenceBackend;
  state_schema_version?: string;
  migration_status?: MigrationStatus;
  run_artifact?: RunArtifact;
  audit_bundle?: AuditBundle;
  audit_policy_status?: AuditPolicyStatus;
  contract_warnings?: ContractWarning[];
  [key: string]: unknown;
}

export interface HeadlessActionResponse {
  ok: boolean;
  api_version: HeadlessApiVersion;
  contract_version: ContractVersion;
  action_id: string;
  state?: RagStateValues;
  manifest?: UiManifest;
  hash?: string;
  messages?: Record<string, unknown>[];
  result?: unknown;
  error?: Record<string, unknown>;
  runtime_error?: RuntimeError;
  runtime_errors?: RuntimeError[];
  capabilities_enabled?: CapabilityPack[];
  capability_versions?: Record<string, string>;
  persistence_backend?: PersistenceBackend;
  state_schema_version?: string;
  migration_status?: MigrationStatus;
  run_artifact?: RunArtifact;
  audit_bundle?: AuditBundle;
  audit_policy_status?: AuditPolicyStatus;
  contract_warnings?: ContractWarning[];
  [key: string]: unknown;
}

export interface ClientOptions {
  fetchImpl?: typeof fetch;
  apiToken?: string;
}
