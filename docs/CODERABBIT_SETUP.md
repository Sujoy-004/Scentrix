# CodeRabbit Setup Instructions

## Automatic CodeRabbit Configuration

Phase 0 bootstrap has created the following files:
- `.coderabbit.yaml` — Configuration for CodeRabbit review behavior
- `.github/workflows/coderabbit.yml` — GitHub Actions workflow that triggers CodeRabbit on PRs

## Manual Setup Required

CodeRabbit requires ONE manual browser-based action before it will activate:

### Step 1: Register with CodeRabbit (if you haven't already)
1. Go to **[https://coderabbit.ai](https://coderabbit.ai)**
2. Click "Sign in with GitHub"
3. Authorize CodeRabbit to access your GitHub account

### Step 2: Add API Key to GitHub Repository Secrets
1. Go to your GitHub repository: **https://github.com/YOUR_USERNAME/scentscape**
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `CODERABBIT_API_KEY`
5. Value: Copy your API key from **[https://coderabbit.ai/account](https://coderabbit.ai/account)** → "API Keys" section
6. Click **Add secret**

### Step 3: Verify Activation
Once the secret is set, CodeRabbit will automatically:
- Review every new Pull Request
- Leave inline comments on problematic code
- Block merges if HIGH or CRITICAL issues are found
- Require request_changes approval before merge

## What CodeRabbit Checks
Based on `.coderabbit.yaml` configuration:
- **Security issues** (SQL injection, missing auth, hardcoded secrets) → BLOCKING
- **Missing input validation** → BLOCKING
- **Missing test coverage on ML pipeline changes** → BLOCKING
- **Type errors and undefined variables** → BLOCKING
- **Style violations** (formatting, naming) → INFORMATIONAL

## Troubleshooting
- If reviews don't appear within 2 minutes of opening a PR, check that `CODERABBIT_API_KEY` is set correctly in repo secrets.
- If you see "Authentication failed", regenerate the API key at [coderabbit.ai/account](https://coderabbit.ai/account) and update the secret.

**Note:** CodeRabbit is free for public repositories and has a generous free tier for private repos. No credit card required.
