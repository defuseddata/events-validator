#!/bin/bash
#
# Interactive Setup Script for Event Validator Schema Repository
#
# This script walks you through setting up a separate GitHub repository
# for storing event validation schemas.
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Event Validator Schema Repository Setup Wizard           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v gh &> /dev/null; then
    echo -e "${RED}✗ gh CLI is not installed${NC}"
    echo ""
    echo "Please install the GitHub CLI first:"
    echo "  macOS:   brew install gh"
    echo "  Linux:   https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo "  Windows: winget install --id GitHub.cli"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ gh CLI installed${NC}"

if ! gh auth status &> /dev/null 2>&1; then
    echo -e "${RED}✗ gh CLI is not authenticated${NC}"
    echo ""
    echo "Please authenticate first:"
    echo "  gh auth login"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ gh CLI authenticated${NC}"

CURRENT_USER=$(gh api user -q '.login' 2>/dev/null || echo "")
echo -e "${GREEN}✓ Logged in as: $CURRENT_USER${NC}"
echo ""

# Get GitHub owner
echo -e "${BLUE}Step 1: Repository Owner${NC}"
echo "Enter the GitHub organization or username for the schema repository."
echo "Press Enter to use your username ($CURRENT_USER):"
read -p "> " OWNER
OWNER=${OWNER:-$CURRENT_USER}
echo ""

# Get repository name
echo -e "${BLUE}Step 2: Repository Name${NC}"
echo "Enter the name for the schema repository."
echo "Press Enter for default (event-schemas):"
read -p "> " REPO_NAME
REPO_NAME=${REPO_NAME:-event-schemas}
echo ""

# Visibility
echo -e "${BLUE}Step 3: Repository Visibility${NC}"
echo "Should the repository be private? (y/N):"
read -p "> " IS_PRIVATE
if [[ $IS_PRIVATE =~ ^[Yy]$ ]]; then
    VISIBILITY="--private"
else
    VISIBILITY="--public"
fi
echo ""

# GCS bucket
echo -e "${BLUE}Step 4: GCS Bucket (Optional)${NC}"
echo "Enter your GCS bucket name for schema sync."
echo "Leave empty to skip GCS configuration:"
read -p "> " GCS_BUCKET
echo ""

# Authentication method
if [ -n "$GCS_BUCKET" ]; then
    echo -e "${BLUE}Step 5: GCP Authentication Method${NC}"
    echo "Choose authentication method for GitHub Actions:"
    echo "  1. Service Account Key (simpler)"
    echo "  2. Workload Identity Federation (more secure)"
    echo "  3. Skip (configure manually later)"
    read -p "> " AUTH_METHOD

    case $AUTH_METHOD in
        1)
            echo ""
            echo "Enter the path to your service account key JSON file:"
            read -p "> " SA_KEY_FILE
            ;;
        2)
            echo ""
            echo "Enter your Workload Identity Provider:"
            echo "(e.g., projects/123/locations/global/workloadIdentityPools/github/providers/github)"
            read -p "> " WIF_PROVIDER
            echo ""
            echo "Enter your service account email:"
            read -p "> " WIF_SA
            ;;
    esac
fi
echo ""

# Copy existing schemas
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/../terraform_backend/src/GA4 Recommended/schemas"

echo -e "${BLUE}Step 6: Copy Existing Schemas${NC}"
if [ -d "$SOURCE_DIR" ]; then
    SCHEMA_COUNT=$(ls -1 "$SOURCE_DIR"/*.json 2>/dev/null | wc -l)
    echo "Found $SCHEMA_COUNT existing schema file(s)."
    echo "Do you want to copy them to the new repository? (Y/n):"
    read -p "> " COPY_SCHEMAS
    if [[ ! $COPY_SCHEMAS =~ ^[Nn]$ ]]; then
        COPY_FLAG="--copy-schemas"
    fi
else
    echo "No existing schemas found at: $SOURCE_DIR"
fi
echo ""

# Confirmation
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Configuration Summary:${NC}"
echo ""
echo "  Repository:    $OWNER/$REPO_NAME"
echo "  Visibility:    ${VISIBILITY#--}"
echo "  GCS Bucket:    ${GCS_BUCKET:-not configured}"
echo "  Auth Method:   ${AUTH_METHOD:-none}"
echo "  Copy Schemas:  ${COPY_FLAG:-no}"
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Proceed with setup? (Y/n):${NC}"
read -p "> " CONFIRM

if [[ $CONFIRM =~ ^[Nn]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Build command
CMD="$SCRIPT_DIR/setup-schema-repo.sh --owner \"$OWNER\" --name \"$REPO_NAME\" $VISIBILITY"

if [ -n "$GCS_BUCKET" ]; then
    CMD="$CMD --bucket \"$GCS_BUCKET\""
fi

if [ -n "$SA_KEY_FILE" ]; then
    CMD="$CMD --sa-key \"$SA_KEY_FILE\""
fi

if [ -n "$WIF_PROVIDER" ]; then
    CMD="$CMD --wif-provider \"$WIF_PROVIDER\""
fi

if [ -n "$WIF_SA" ]; then
    CMD="$CMD --wif-sa \"$WIF_SA\""
fi

if [ -n "$COPY_FLAG" ]; then
    CMD="$CMD $COPY_FLAG"
fi

# Run setup
echo ""
echo -e "${BLUE}Running setup...${NC}"
echo ""

eval $CMD

echo ""
echo -e "${GREEN}Setup complete!${NC}"
