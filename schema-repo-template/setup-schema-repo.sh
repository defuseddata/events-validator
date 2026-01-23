#!/bin/bash
#
# Setup Script for Event Validator Schema Repository
#
# This script automates the creation and configuration of a separate GitHub
# repository for storing event validation schemas.
#
# Prerequisites:
#   - gh CLI installed and authenticated (gh auth login)
#   - jq installed for JSON parsing
#
# Usage:
#   ./setup-schema-repo.sh [options]
#
# Options:
#   -o, --owner         GitHub owner (org or user) [required]
#   -n, --name          Repository name [default: event-schemas]
#   -b, --bucket        GCS bucket name [required for GCS sync]
#   -p, --private       Create as private repository [default: public]
#   -s, --sa-key        Path to GCP service account key JSON file
#   --wif-provider      Workload Identity Federation provider
#   --wif-sa            Service account email for WIF
#   --copy-schemas      Copy existing schemas from source directory
#   --source-dir        Source directory for schemas [default: ../terraform_backend/src/GA4 Recommended/schemas]
#   -h, --help          Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REPO_NAME="event-schemas"
VISIBILITY="public"
SCHEMA_PATH="schemas"
COPY_SCHEMAS=false
SOURCE_DIR="../terraform_backend/src/GA4 Recommended/schemas"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--owner)
            OWNER="$2"
            shift 2
            ;;
        -n|--name)
            REPO_NAME="$2"
            shift 2
            ;;
        -b|--bucket)
            GCS_BUCKET="$2"
            shift 2
            ;;
        -p|--private)
            VISIBILITY="private"
            shift
            ;;
        -s|--sa-key)
            SA_KEY_FILE="$2"
            shift 2
            ;;
        --wif-provider)
            WIF_PROVIDER="$2"
            shift 2
            ;;
        --wif-sa)
            WIF_SA="$2"
            shift 2
            ;;
        --copy-schemas)
            COPY_SCHEMAS=true
            shift
            ;;
        --source-dir)
            SOURCE_DIR="$2"
            shift 2
            ;;
        -h|--help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$OWNER" ]; then
    echo -e "${RED}Error: --owner is required${NC}"
    echo "Usage: $0 --owner <github-owner> [options]"
    exit 1
fi

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: gh CLI is not installed${NC}"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: gh CLI is not authenticated${NC}"
    echo "Run: gh auth login"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed. Some features may be limited.${NC}"
fi

echo -e "${GREEN}Prerequisites OK${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if repository already exists
echo -e "\n${BLUE}Checking if repository exists...${NC}"
if gh repo view "$OWNER/$REPO_NAME" &> /dev/null; then
    echo -e "${YELLOW}Repository $OWNER/$REPO_NAME already exists${NC}"
    read -p "Do you want to continue and update it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    REPO_EXISTS=true
else
    REPO_EXISTS=false
fi

# Create repository if it doesn't exist
if [ "$REPO_EXISTS" = false ]; then
    echo -e "\n${BLUE}Creating repository $OWNER/$REPO_NAME...${NC}"

    gh repo create "$OWNER/$REPO_NAME" \
        --"$VISIBILITY" \
        --description "Event validation schemas for Events Validator" \
        --clone=false

    echo -e "${GREEN}Repository created${NC}"
fi

# Clone repository to temp directory
TEMP_DIR=$(mktemp -d)
echo -e "\n${BLUE}Cloning repository to temp directory...${NC}"

if [ "$REPO_EXISTS" = true ]; then
    gh repo clone "$OWNER/$REPO_NAME" "$TEMP_DIR"
else
    # Initialize new repo
    cd "$TEMP_DIR"
    git init
    git remote add origin "https://github.com/$OWNER/$REPO_NAME.git"
fi

cd "$TEMP_DIR"

# Create directory structure
echo -e "\n${BLUE}Setting up directory structure...${NC}"
mkdir -p .github/workflows
mkdir -p "$SCHEMA_PATH"

# Copy workflow files
echo -e "${BLUE}Copying GitHub Actions workflows...${NC}"
cp "$SCRIPT_DIR/.github/workflows/sync-to-gcs.yml" .github/workflows/
cp "$SCRIPT_DIR/.github/workflows/sync-to-gcs-simple.yml" .github/workflows/

# Copy README
cp "$SCRIPT_DIR/README.md" ./

# Copy schemas if requested
if [ "$COPY_SCHEMAS" = true ]; then
    if [ -d "$SOURCE_DIR" ]; then
        echo -e "${BLUE}Copying existing schemas from $SOURCE_DIR...${NC}"
        cp "$SOURCE_DIR"/*.json "$SCHEMA_PATH/" 2>/dev/null || true

        # Also copy repo.json if it exists
        REPO_JSON_DIR="$(dirname "$SOURCE_DIR")"
        if [ -f "$REPO_JSON_DIR/repo.json" ]; then
            cp "$REPO_JSON_DIR/repo.json" "$SCHEMA_PATH/"
            echo -e "${GREEN}Copied repo.json${NC}"
        fi

        SCHEMA_COUNT=$(ls -1 "$SCHEMA_PATH"/*.json 2>/dev/null | wc -l)
        echo -e "${GREEN}Copied $SCHEMA_COUNT schema file(s)${NC}"
    else
        echo -e "${YELLOW}Source directory not found: $SOURCE_DIR${NC}"
        echo -e "${YELLOW}Creating empty schema directory${NC}"
    fi
fi

# Create a placeholder if no schemas
if [ ! "$(ls -A $SCHEMA_PATH 2>/dev/null)" ]; then
    echo '{}' > "$SCHEMA_PATH/.gitkeep"
fi

# Create .gitignore
cat > .gitignore << 'GITIGNORE'
# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*.swo
*~
.idea/
.vscode/

# Temporary files
*.tmp
*.bak
GITIGNORE

# Commit and push
echo -e "\n${BLUE}Committing changes...${NC}"
git add -A

if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to commit${NC}"
else
    git commit -m "Initialize schema repository

- Add GitHub Actions workflows for GCS sync
- Add repository documentation
- Set up schemas directory"

    echo -e "${BLUE}Pushing to GitHub...${NC}"

    if [ "$REPO_EXISTS" = false ]; then
        git branch -M main
    fi

    git push -u origin main
    echo -e "${GREEN}Changes pushed${NC}"
fi

# Configure repository secrets
echo -e "\n${BLUE}Configuring repository secrets...${NC}"

if [ -n "$GCS_BUCKET" ]; then
    echo "Setting GCS_BUCKET_NAME secret..."
    gh secret set GCS_BUCKET_NAME --repo "$OWNER/$REPO_NAME" --body "$GCS_BUCKET"
    echo -e "${GREEN}GCS_BUCKET_NAME set${NC}"
fi

if [ -n "$SA_KEY_FILE" ]; then
    if [ -f "$SA_KEY_FILE" ]; then
        echo "Setting GCP_SA_KEY secret..."
        gh secret set GCP_SA_KEY --repo "$OWNER/$REPO_NAME" < "$SA_KEY_FILE"
        echo -e "${GREEN}GCP_SA_KEY set${NC}"
    else
        echo -e "${RED}Service account key file not found: $SA_KEY_FILE${NC}"
    fi
fi

if [ -n "$WIF_PROVIDER" ]; then
    echo "Setting GCP_WORKLOAD_IDENTITY_PROVIDER secret..."
    gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$OWNER/$REPO_NAME" --body "$WIF_PROVIDER"
    echo -e "${GREEN}GCP_WORKLOAD_IDENTITY_PROVIDER set${NC}"
fi

if [ -n "$WIF_SA" ]; then
    echo "Setting GCP_SERVICE_ACCOUNT secret..."
    gh secret set GCP_SERVICE_ACCOUNT --repo "$OWNER/$REPO_NAME" --body "$WIF_SA"
    echo -e "${GREEN}GCP_SERVICE_ACCOUNT set${NC}"
fi

# Configure branch protection (optional)
echo -e "\n${BLUE}Configuring branch protection...${NC}"
read -p "Do you want to enable branch protection for main? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Note: Branch protection requires admin access
    gh api \
        --method PUT \
        -H "Accept: application/vnd.github+json" \
        "/repos/$OWNER/$REPO_NAME/branches/main/protection" \
        -f "required_status_checks[strict]=true" \
        -f "required_status_checks[contexts][]=validate" \
        -f "enforce_admins=false" \
        -f "required_pull_request_reviews[required_approving_review_count]=1" \
        -f "required_pull_request_reviews[dismiss_stale_reviews]=true" \
        -f "restrictions=null" \
        2>/dev/null && echo -e "${GREEN}Branch protection enabled${NC}" || echo -e "${YELLOW}Could not enable branch protection (may require admin access)${NC}"
fi

# Cleanup
cd - > /dev/null
rm -rf "$TEMP_DIR"

# Generate environment variables for Events Validator
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Repository setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}Add these environment variables to your Events Validator:${NC}"
echo ""
echo "# GitHub Schema Repository Configuration"
echo "SCHEMA_REPO_OWNER=$OWNER"
echo "SCHEMA_REPO_NAME=$REPO_NAME"
echo "SCHEMA_REPO_PATH=$SCHEMA_PATH"
echo "SCHEMA_REPO_DEFAULT_BRANCH=main"
echo "GITHUB_TOKEN=<your-github-token>"
echo ""

echo -e "${BLUE}To create a GitHub token:${NC}"
echo "1. Go to https://github.com/settings/tokens"
echo "2. Generate new token (classic) with 'repo' scope"
echo "3. Or use: gh auth token"
echo ""

echo -e "${BLUE}Repository URL:${NC}"
echo "https://github.com/$OWNER/$REPO_NAME"
echo ""

# List configured secrets
echo -e "${BLUE}Configured secrets:${NC}"
gh secret list --repo "$OWNER/$REPO_NAME" 2>/dev/null || echo "(none)"
