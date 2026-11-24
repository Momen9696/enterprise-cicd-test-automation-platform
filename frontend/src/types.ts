export type Summary = {
  total_runs: number;
  passed_runs: number;
  failed_runs: number;
  error_runs: number;
  running_runs: number;
  cancelled_runs: number;
  average_duration_ms: number;
  success_rate: number;
  test_pass_rate: number;
  demo_seed_runs: number;
  source: string;
};

export type TrendPoint = { date: string; passed: number; failed: number; error: number };

export type ProjectStat = {
  project_id: number;
  project_name: string;
  runs: number;
  passed: number;
  failed: number;
  average_duration_ms: number;
  success_rate: number;
};

export type FailureStat = {
  name: string;
  suite_name: string;
  failures: number;
  last_message: string;
  last_seen: string;
  project_name: string;
};

export type Environment = {
  id: number;
  name: string;
  description: string;
  variables: Record<string, string>;
  is_demo_seed: boolean;
};

export type Project = {
  id: number;
  name: string;
  slug: string;
  description: string;
  repository_url: string | null;
  default_branch: string;
  is_demo_seed: boolean;
  environments: Environment[];
};

export type Pipeline = {
  id: number;
  project_id: number;
  project_name: string;
  environment_name: string | null;
  name: string;
  provider: string;
  template_key: string;
  suite_id: string;
  adapter: string;
  classification: string;
  branch_pattern: string;
  run_mode: string;
  enabled: boolean;
  is_demo_seed: boolean;
  latest_status: string | null;
};

export type Execution = {
  id: number;
  project_id: number;
  project_name: string;
  pipeline_id: number;
  pipeline_name: string;
  environment_name: string;
  status: string;
  trigger: string;
  branch: string;
  commit_sha: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  error_message: string | null;
  triggered_by: string;
  is_demo_seed: boolean;
  provider: string;
  classification: string;
};

export type TestResult = {
  id: number;
  suite_name: string;
  name: string;
  status: string;
  duration_ms: number;
  message: string;
  classification: string;
};

export type TemplateItem = {
  provider: string;
  filename: string;
  template_key: string;
  valid: boolean;
  errors: string[];
};

export type Filters = {
  project_id: string;
  pipeline_id: string;
  branch: string;
  environment: string;
  status: string;
  date_from: string;
  date_to: string;
  include_demo: boolean;
};

export const emptyFilters: Filters = {
  project_id: "",
  pipeline_id: "",
  branch: "",
  environment: "",
  status: "",
  date_from: "",
  date_to: "",
  include_demo: true,
};
