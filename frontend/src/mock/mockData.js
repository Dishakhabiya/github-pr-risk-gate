/**
 * Mock Data for GitHub PR Risk Gate & Understanding System.
 * Standardized data structures for Person 1 (Risk ML), Person 2 (RAG/Questions), and Person 3 (LLM Decision).
 */

export const MOCK_PRS = {
  "kubernetes/kubernetes#142645": {
    pr_id: 142645,
    repository: "kubernetes/kubernetes",
    title: "Refactor API server auth token validation & config cache",
    body: "Fixes #99881. Optimizes token check speed by introducing a localized cache in config.go and adding unit tests for token validation.",
    state: "open",
    author: "dev_kubernetes_lead",
    base_branch: "main",
    head_branch: "auth-token-cache",
    created_at: "2026-10-03T04:42:42Z",
    features: {
      files_changed: 3,
      lines_added: 417,
      lines_deleted: 9,
      total_lines_changed: 426,
      commits_count: 1,
      additions_to_deletions_ratio: 46.33,
      source_files_changed: 1,
      test_files_changed: 2,
      documentation_files_changed: 0,
      config_files_changed: 0,
      average_changes_per_file: 142.0,
      binary_files_changed: 0,
      renamed_files: 0,
      deleted_files: 0,
      added_files: 2,
      file_type_counts: { go: 3 },
      title_length: 57,
      body_length: 142,
      has_linked_issue: 1
    },
    risk_analysis: {
      pr_id: 142645,
      repository: "kubernetes/kubernetes",
      title: "Refactor API server auth token validation & config cache",
      risk_score: 0.1636,
      risk_level: "LOW",
      threshold: 0.5,
      model_name: "Logistic Regression (Class-Weighted)"
    },
    changed_files_list: [
      { filename: "pkg/kubeapiserver/authenticator/config.go", status: "modified", additions: 45, deletions: 9, changes: 54 },
      { filename: "pkg/kubeapiserver/authenticator/token_cache.go", status: "added", additions: 210, deletions: 0, changes: 210 },
      { filename: "test/integration/auth/token_test.go", status: "added", additions: 162, deletions: 0, changes: 162 }
    ],
    repository_context: [
      {
        file: "pkg/kubeapiserver/authenticator/config.go",
        lines: "L45-L60",
        snippet: `// Config validates request bearer tokens against configured identity providers.
type Config struct {
    TokenCache      *TokenCache
    TTL             time.Duration
    MaxBatchSize    int
}`
      },
      {
        file: "pkg/kubeapiserver/authenticator/authenticator.go",
        lines: "L120-L135",
        snippet: `// AuthenticateRequest validates incoming HTTP requests.
func (c *Config) AuthenticateRequest(req *http.Request) (*User, bool, error) {
    token := retrieveBearerToken(req)
    if user, ok := c.TokenCache.Get(token); ok {
        return user, true, nil
    }
    return c.verifyTokenRemote(req.Context(), token)
}`
      }
    ],
    questions: [
      {
        id: "q1",
        question: "Why was the localized token cache added to config.go instead of calling verifyTokenRemote on every request?",
        placeholder: "Explain the performance rationale and latency reduction..."
      },
      {
        id: "q2",
        question: "How does this change handle cache invalidation or expired bearer tokens?",
        placeholder: "Describe the TTL expiration mechanism and eviction strategy..."
      },
      {
        id: "q3",
        question: "What race conditions or concurrent access edge cases were considered for the token cache map?",
        placeholder: "Explain mutex locking or sync.RWMutex usage..."
      }
    ],
    sample_answers: {
      q1: "Calling verifyTokenRemote for every incoming API server HTTP request adds 30-50ms network latency per RPC. Adding the localized sync.RWMutex token cache reduces lookup latency to under 1ms for cached active session tokens.",
      q2: "The cache entry stores an absolute expiration timestamp. When Get(token) is invoked, it checks if time.Now() exceeds the TTL (default 5 minutes). Expired entries return cache miss and trigger background eviction.",
      q3: "We wrapped the underlying map with sync.RWMutex, allowing concurrent RLock() for reads during token validation and exclusive Lock() during eviction or cache writes."
    },
    final_result: {
      pr_id: 142645,
      repository: "kubernetes/kubernetes",
      risk_score: 0.1636,
      risk_level: "LOW",
      understanding_score: 0.92,
      decision: "PASS",
      reasons: [
        "Developer clearly articulated latency benefits and performance metrics for the API server token cache.",
        "Correctly described the TTL expiration mechanism and thread-safe sync.RWMutex concurrency pattern.",
        "Relevant repository context snippets (pkg/kubeapiserver/authenticator) were properly understood and integrated."
      ],
      github_pr_url: "https://github.com/kubernetes/kubernetes/pull/142645"
    }
  },
  "tensorflow/tensorflow#128355": {
    pr_id: 128355,
    repository: "tensorflow/tensorflow",
    title: "Modify CUDA memory allocator pointers & kernel launch configuration",
    body: "Fixes #54321. Changes raw memory pointer offsets in GPU kernel launcher.",
    state: "open",
    author: "cuda_dev",
    base_branch: "main",
    head_branch: "fix-cuda-alloc",
    created_at: "2026-10-01T01:04:33Z",
    features: {
      files_changed: 8,
      lines_added: 850,
      lines_deleted: 420,
      total_lines_changed: 1270,
      commits_count: 5,
      additions_to_deletions_ratio: 2.02,
      source_files_changed: 6,
      test_files_changed: 1,
      documentation_files_changed: 0,
      config_files_changed: 1,
      average_changes_per_file: 158.75,
      binary_files_changed: 0,
      renamed_files: 0,
      deleted_files: 1,
      added_files: 2,
      file_type_counts: { cc: 4, h: 2, py: 2 },
      title_length: 68,
      body_length: 85,
      has_linked_issue: 1
    },
    risk_analysis: {
      pr_id: 128355,
      repository: "tensorflow/tensorflow",
      title: "Modify CUDA memory allocator pointers & kernel launch configuration",
      risk_score: 0.8420,
      risk_level: "HIGH",
      threshold: 0.5,
      model_name: "Logistic Regression (Class-Weighted)"
    },
    changed_files_list: [
      { filename: "tensorflow/core/common_runtime/gpu/gpu_device.cc", status: "modified", additions: 320, deletions: 180, changes: 500 },
      { filename: "tensorflow/core/common_runtime/gpu/gpu_allocator.h", status: "modified", additions: 140, deletions: 90, changes: 230 },
      { filename: "tensorflow/core/kernels/cuda_kernel_helper.h", status: "modified", additions: 210, deletions: 150, changes: 360 }
    ],
    repository_context: [
      {
        file: "tensorflow/core/common_runtime/gpu/gpu_device.cc",
        lines: "L210-L240",
        snippet: `// GpuDevice manages CUDA streams and asynchronous memory allocation.
void GpuDevice::Compute(OpKernel* op_kernel, OpKernelContext* context) {
    auto stream = context->op_device_context()->stream();
    // Raw GPU device pointer calculation
    void* gpu_ptr = allocator_->AllocateRaw(alignment, num_bytes);
}`
      }
    ],
    questions: [
      {
        id: "q1",
        question: "How does this pointer calculation handle GPU device out-of-memory errors?",
        placeholder: "Explain memory allocation fallback..."
      },
      {
        id: "q2",
        question: "What synchronization mechanism ensures CUDA stream safety during asynchronous kernel launches?",
        placeholder: "Describe stream synchronization..."
      }
    ],
    sample_answers: {
      q1: "If AllocateRaw returns nullptr, the runtime falls back to BFC allocator retry before signaling OOM context error.",
      q2: "CUDA streams use cudaStreamSynchronize or event tracking to prevent race conditions during async launches."
    },
    final_result: {
      pr_id: 128355,
      repository: "tensorflow/tensorflow",
      risk_score: 0.8420,
      risk_level: "HIGH",
      understanding_score: 0.88,
      decision: "PASS",
      reasons: [
        "High ML risk score due to deep C++/CUDA kernel changes.",
        "Developer demonstrated complete understanding of asynchronous GPU memory synchronization.",
        "Safety verification confirmed stream event boundaries."
      ],
      github_pr_url: "https://github.com/tensorflow/tensorflow/pull/128355"
    }
  },
  "microsoft/vscode#339476": {
    pr_id: 339476,
    repository: "microsoft/vscode",
    title: "Update editor statusbar theme tokens & layout spacing",
    body: "Updates UI theme tokens for statusbar items.",
    state: "open",
    author: "ui_dev",
    base_branch: "main",
    head_branch: "statusbar-theme",
    created_at: "2026-10-03T13:51:19Z",
    features: {
      files_changed: 2,
      lines_added: 12,
      lines_deleted: 8,
      total_lines_changed: 20,
      commits_count: 1,
      additions_to_deletions_ratio: 1.5,
      source_files_changed: 1,
      test_files_changed: 0,
      documentation_files_changed: 0,
      config_files_changed: 1,
      average_changes_per_file: 10.0,
      binary_files_changed: 0,
      renamed_files: 0,
      deleted_files: 0,
      added_files: 0,
      file_type_counts: { ts: 1, json: 1 },
      title_length: 54,
      body_length: 46,
      has_linked_issue: 0
    },
    risk_analysis: {
      pr_id: 339476,
      repository: "microsoft/vscode",
      title: "Update editor statusbar theme tokens & layout spacing",
      risk_score: 0.0450,
      risk_level: "LOW",
      threshold: 0.5,
      model_name: "Logistic Regression (Class-Weighted)"
    },
    changed_files_list: [
      { filename: "src/vs/workbench/browser/parts/statusbar/statusbarPart.ts", status: "modified", additions: 8, deletions: 6, changes: 14 },
      { filename: "src/vs/workbench/browser/parts/statusbar/statusbar.css", status: "modified", additions: 4, deletions: 2, changes: 6 }
    ],
    repository_context: [
      {
        file: "src/vs/workbench/browser/parts/statusbar/statusbarPart.ts",
        lines: "L80-L95",
        snippet: `// StatusbarPart manages bottom status bar items
export class StatusbarPart extends Part {
    protected updateStyles(): void {
        super.updateStyles();
        const container = assertIsDefined(this.getContainer());
        container.style.backgroundColor = this.getColor(STATUS_BAR_BACKGROUND) || '';
    }
}`
      }
    ],
    questions: [
      {
        id: "q1",
        question: "Does this statusbar CSS token update affect custom user themes or high contrast mode?",
        placeholder: "Describe high contrast theme overrides..."
      }
    ],
    sample_answers: {
      q1: "No, high contrast theme definitions override these base statusbar tokens via themeService.isHighContrast()."
    },
    final_result: {
      pr_id: 339476,
      repository: "microsoft/vscode",
      risk_score: 0.0450,
      risk_level: "LOW",
      understanding_score: 0.95,
      decision: "PASS",
      reasons: [
        "Low ML risk score for minor UI theme token updates.",
        "Developer confirmed high-contrast accessibility overrides remain intact."
      ],
      github_pr_url: "https://github.com/microsoft/vscode/pull/339476"
    }
  }
};

export const DEFAULT_PR_KEY = "kubernetes/kubernetes#142645";
