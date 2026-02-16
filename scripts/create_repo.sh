#!/bin/bash
#
# Interactive Helper to create the Schema Repository (for Terraform)
#
# This script creates an EMPTY repository on GitHub, which is a prerequisite
# for the Terraform "github_sync" module.
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Event Validator Schema Repository Setup Wizard           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# --- Prerequisites Check ---

echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed.${NC}"
    echo "This script requires 'gh' to create repositories."
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: You are not logged in to GitHub CLI.${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

CURRENT_USER=$(gh api user -q '.login' 2>/dev/null || echo "")
echo -e "${GREEN}✓ Logged in as: $CURRENT_USER${NC}"
echo ""

# --- Interactive Wizard ---

# 1. Owner
echo -e "${BLUE}Step 1: Repository Owner${NC}"
echo "Enter the GitHub organization or username for the schema repository."
echo "Press Enter to use your username ($CURRENT_USER):"
read -p "> " INPUT_OWNER
OWNER=${INPUT_OWNER:-$CURRENT_USER}
echo ""

# 2. Repo Name
echo -e "${BLUE}Step 2: Repository Name${NC}"
echo "Enter the name for the schema repository."
echo "Press Enter for default (event-schemas):"
read -p "> " INPUT_NAME
REPO_NAME=${INPUT_NAME:-event-schemas}
echo ""

# 3. Visibility
echo -e "${BLUE}Step 3: Repository Visibility${NC}"
echo "Should the repository be private? (Y/n) (Default: Yes):"
read -p "> " INPUT_VISIBILITY
if [[ "$INPUT_VISIBILITY" =~ ^[Nn] ]]; then
    VISIBILITY_FLAG="--public"
    VISIBILITY_TEXT="Public"
else
    VISIBILITY_FLAG="--private"
    VISIBILITY_TEXT="Private"
fi
echo ""

# 4. Branch Protection (Optional) (Default: No)
echo -e "${BLUE}Step 4: Branch Protection${NC}"
echo "Do you have GitHub Pro/Team or is this a Public repo?"
echo "If YES, we can enable Branch Protection (Require PRs, Status Checks)."
echo "Enable Branch Protection? (y/N) (Default: No - Safer for Free plans):"
read -p "> " INPUT_PROTECTION

# Default to false
PROTECT_TF_BOOL="false"
PROTECT_TEXT="Disabled (Free Plan / Private)"

if [[ "$INPUT_PROTECTION" =~ ^[Yy] ]]; then
    PROTECT_TF_BOOL="true"
    PROTECT_TEXT="Enabled"
fi
echo ""

# --- Confirmation ---

echo -e "${CYAN}--- Summary ---${NC}"
echo "Repository:  $OWNER/$REPO_NAME"
echo "Visibility:  $VISIBILITY_TEXT"
echo "Protection:  $PROTECT_TEXT"
echo "Action:      Create empty repo & init main branch (temporary clone)"
echo ""
read -p "Proceed? (Y/n) " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn] ]]; then
    echo "Aborted."
    exit 0
fi

# --- Execution ---

TEMP_DIR=$(mktemp -d)
CUR_DIR=$(pwd)

echo ""
echo -e "${BLUE}Creating repository...${NC}"

if gh repo view "$OWNER/$REPO_NAME" &> /dev/null; then
    echo -e "${YELLOW}Warning: Repository $OWNER/$REPO_NAME already exists.${NC}"
else
    # Create new without cloning here
    gh repo create "$OWNER/$REPO_NAME" $VISIBILITY_FLAG
    echo -e "${GREEN}✓ Repository created successfully!${NC}"
fi

# --- Initialization in Temp Dir ---

echo -e "${BLUE}Initializing 'main' branch in temp directory...${NC}"
cd "$TEMP_DIR"

# Clone nicely
gh repo clone "$OWNER/$REPO_NAME" . >/dev/null

# Check if main exists
if ! git ls-remote --exit-code --heads origin main &> /dev/null; then
     echo "Pushing initial commit..."
     touch .gitkeep
     git add .gitkeep
     git commit -m "Initial commit" >/dev/null
     git branch -M main
     git push -u origin main >/dev/null
     echo -e "${GREEN}✓ 'main' branch initialized.${NC}"
else
     echo "Branch 'main' already exists on remote."
fi

# Cleanup
cd "$CUR_DIR"
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ Temporary files cleaned up.${NC}"


# --- Next Steps Handover ---

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Repository Ready! Now configure Terraform.${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Now, please update your configuration file:"
echo "File: terraform_backend/terraform.tfvars"
echo ""
echo "Copy and paste these values:"
echo -e "${CYAN}github_token             = \"<YOUR_GITHUB_PAT>\"${NC}"
echo -e "${CYAN}schema_repo_owner        = \"$OWNER\"${NC}"
echo -e "${CYAN}schema_repo_name         = \"$REPO_NAME\"${NC}"
echo -e "${CYAN}enable_branch_protection = $PROTECT_TF_BOOL${NC}"
echo ""
echo "Then setup is complete!"
echo "1. cd terraform_backend"
echo "2. terraform apply"
echo ""
echo -e "${BLUE}Tip: To logout from GitHub CLI, run: gh auth logout${NC}"
