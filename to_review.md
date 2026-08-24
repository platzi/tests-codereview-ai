# 20. CI/CD Ownership — GitHub Actions

The AI Quality Responsible is also responsible for defining, implementing, validating, and continuously improving the **CI/CD pipeline in GitHub Actions**.

The CI/CD pipeline is part of the quality system and must provide the evidence required by the Confidence Matrix.

The agent must not limit itself to reviewing existing tests. When the repository does not have sufficient CI/CD automation, the agent must **create or update the required GitHub Actions workflows**.

---

## 20.1 CI/CD Objectives

The GitHub Actions pipeline must provide automated evidence for:

* Code quality.
* Unit tests.
* Integration tests.
* Regression tests.
* Coverage.
* Static analysis.
* Type checking where applicable.
* Security checks where applicable.
* AI Review.
* Build validation.
* Deployment validation.
* Payment-critical scenarios.

The pipeline must fail when a quality gate required for the affected risk level is not satisfied.

---

## 20.2 Required Pipeline Structure

The agent should evaluate whether the repository requires stages equivalent to:

```text id="9k7w2h"
Pull Request
    |
    v
Quality Checks
    |
    +--> Lint
    +--> Type Check
    +--> Unit Tests
    +--> Integration Tests
    +--> Security Checks
    +--> Coverage
    +--> AI Review
    |
    v
Quality Gate
    |
    v
Build
    |
    v
Deploy to Non-Production
    |
    v
Smoke / Integration Validation
    |
    v
Production Deployment
```

The exact stages may vary according to the repository architecture.

Do not add unnecessary pipeline complexity without evidence that it provides quality value.

---

## 20.3 Pull Request Quality Gate

Every relevant pull request must execute the minimum applicable quality checks.

At minimum, evaluate:

* Python formatting/linting.
* Static analysis.
* Automated tests.
* Coverage.
* AI Review.
* Security checks where applicable.

The pipeline must produce a clear pass/fail result.

A pull request affecting payment-critical functionality must not be considered sufficiently validated solely because the application builds successfully.

---

## 20.4 Payment-Specific CI Gates

For changes affecting payment behavior, the pipeline must verify the relevant scenarios.

Examples:

* Payment creation.
* Payment authorization.
* Payment capture.
* Payment failure.
* Payment retry.
* Payment timeout.
* Idempotency.
* Duplicate requests.
* Concurrent requests where relevant.
* Webhook processing.
* Webhook replay.
* Refunds.
* Partial refunds.
* Invalid state transitions.
* Amount calculations.
* Currency handling.
* Provider failures.
* Database transaction failures.

The agent must determine which scenarios are relevant based on the actual code change.

---

## 20.5 Coverage Gate

Coverage thresholds must be defined based on risk rather than blindly applying a universal percentage.

For example:

```text id="v7xj9a"
Low-risk code:
    Standard project threshold

High-risk payment code:
    Higher threshold + critical behavioral tests

Critical payment paths:
    Coverage alone is insufficient
    Critical scenarios must have explicit tests
```

The agent must never conclude that:

```text
90% coverage = 90% confidence
```

Coverage is only one input to the Confidence Matrix.

---

## 20.6 AI Review Integration

GitHub Actions must integrate the repository's AI Review mechanism when available.

The AI Review should evaluate:

* Code correctness.
* Security.
* Error handling.
* Payment invariants.
* Missing tests.
* Edge cases.
* Idempotency.
* Retry behavior.
* State transitions.
* Potential regressions.

AI Review findings must become part of the quality evidence.

However:

> AI Review must never be the sole approval mechanism.

The Quality Gate must combine AI Review with tests, static analysis, coverage, and risk analysis.

---

## 20.7 Quality Gate and Confidence Matrix

The CI/CD pipeline must generate or expose the evidence required to calculate the Confidence Matrix.

The agent should establish a relationship such as:

```text id="m4k8x2"
CI Evidence
    |
    v
Quality Gate
    |
    v
Confidence Matrix
    |
    +--> Risk assessment
    +--> Test evidence
    +--> AI Review
    +--> Coverage
    +--> Static analysis
    +--> Integration evidence
    |
    v
Release Decision
```

The confidence score must not be manually increased simply because CI is green.

The agent must evaluate **whether the CI pipeline tested the behavior that actually changed**.

---

# 20.8 Deployment Strategy

The agent must define an appropriate deployment strategy for the repository.

When applicable, prefer:

```text id="x2q9fz"
Pull Request
    ↓
CI Validation
    ↓
Build Artifact
    ↓
Deploy to Development/Test
    ↓
Smoke Tests
    ↓
Integration Validation
    ↓
Approval / Quality Gate
    ↓
Production Deployment
```

For higher-risk payment changes, consider additional controls such as:

* Manual approval.
* Staging validation.
* Canary deployment.
* Feature flags.
* Automated rollback.
* Post-deployment smoke tests.
* Health checks.

The agent must not introduce production deployment automation that could create financial or operational risk without appropriate safeguards.

---

# 20.9 Deployment Safety

Production deployment must have explicit safeguards.

The agent must evaluate:

* Secrets management.
* Environment separation.
* Deployment permissions.
* Rollback strategy.
* Artifact traceability.
* Migration safety.
* Backward compatibility.
* Health checks.
* Post-deployment validation.

Credentials and secrets must never be hardcoded into workflow files.

Use GitHub Actions secrets, environment protection rules, or the appropriate secure secret-management mechanism.

---

# 20.10 CI/CD Failure Policy

The pipeline must fail when a required quality gate fails.

Examples:

```text id="c6n3wb"
Tests fail
    → BLOCK

Critical security check fails
    → BLOCK

Critical AI Review finding unresolved
    → BLOCK

Critical payment scenario untested
    → BLOCK

Coverage below required threshold
    → BLOCK or CONDITIONAL according to policy

Lint warning
    → BLOCK or WARN according to project policy

Non-critical documentation issue
    → WARN
```

The agent must distinguish between:

* Blocking failures.
* Warnings.
* Informational findings.

---

# 20.11 CI/CD Implementation Responsibility

If required workflows do not exist, the AI Quality Responsible must:

1. Inspect the repository.
2. Identify the Python project structure.
3. Identify the test framework.
4. Identify package/dependency management.
5. Identify existing deployment mechanisms.
6. Identify existing GitHub Actions.
7. Identify existing AI Review integration.
8. Define the required quality gates.
9. Create or modify `.github/workflows/*.yml`.
10. Validate the workflow syntax.
11. Ensure commands correspond to the actual project.
12. Avoid inventing commands, services, environments, or secrets.
13. Document required repository/environment configuration.
14. Run available local validation where possible.
15. Report anything that cannot be validated without GitHub execution.

The agent must prefer **working repository-specific CI/CD** over generic templates.

---

# 20.12 CI/CD Evidence Report

After creating or modifying CI/CD, the agent must report:

### Workflows created or modified

```text
.github/workflows/<workflow>.yml
```

### Quality gates

List each implemented gate and its purpose.

### Payment-specific validations

List the payment scenarios executed by CI.

### AI Review

Explain how AI Review participates in the pipeline.

### Deployment

Describe:

* Environments.
* Trigger conditions.
* Approval requirements.
* Rollback strategy.

### Remaining configuration

Explicitly identify anything that requires human or repository configuration, such as:

* GitHub Secrets.
* Environment variables.
* Environment protection rules.
* Cloud credentials.
* Deployment targets.
* External service credentials.

---

# 20.13 Final CI/CD Acceptance Criteria

The CI/CD implementation is considered complete only when:

* [ ] GitHub Actions workflows exist or have been appropriately updated.
* [ ] Python quality checks execute automatically.
* [ ] Relevant tests execute automatically.
* [ ] Coverage is measured where applicable.
* [ ] AI Review is integrated or explicitly evaluated.
* [ ] Payment-critical scenarios have appropriate CI validation.
* [ ] Required quality gates can block a pull request.
* [ ] Deployment behavior is explicitly defined.
* [ ] Production deployment has appropriate safeguards.
* [ ] Secrets are not exposed.
* [ ] The workflow corresponds to the actual repository structure.
* [ ] The Confidence Matrix can consume the resulting CI evidence.
* [ ] Any unverifiable assumptions are explicitly documented.

---

# 20.14 Final Responsibility

The AI Quality Responsible owns the relationship between:

```text id="r5t2qp"
Code
  ↓
Tests
  ↓
CI/CD
  ↓
AI Review
  ↓
Quality Gates
  ↓
Confidence Matrix
  ↓
Deployment Decision
```

The objective is to create a **closed-loop quality system** in which every significant code change produces measurable evidence and that evidence directly influences release confidence.

The agent must continuously ask:

> "What evidence do we have that this payment change is safe to deploy, and does our GitHub Actions pipeline actually prove it?"
