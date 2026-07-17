#!/bin/bash
#
# Unified Installer Script for Event Validator pipeline
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║             Event Validator Setup Wizard                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# --- Project Preferences ---
echo "Do you want to enable GitHub GitOps synchronization (Optional)? [Y/n]"
echo "If enabled, schemas will be continuously synced from a GitHub repository."
read -p "Enable GitOps? (Y/n) " ENABLE_GITOPS
echo ""

# --- Prerequisites Check ---
echo -e "${BLUE}Checking prerequisites...${NC}"

HAS_ERROR=0

echo "Checking required tools:"
TOOLS="gcloud terraform jq"
if [[ ! "$ENABLE_GITOPS" =~ ^[Nn] ]]; then TOOLS="gh gcloud terraform jq"; fi

for cmd in $TOOLS; do
  if ! command -v $cmd &> /dev/null; then
      echo -e "  ${RED}✗ $cmd is missing${NC}"
      HAS_ERROR=1
  else
      echo -e "  ${GREEN}✓ $cmd is installed${NC}"
  fi
done

if [ $HAS_ERROR -eq 1 ]; then
    echo -e "\n${RED}Please install the missing tools and try again.${NC}"
    exit 1
fi

echo ""
echo "Checking authentications:"

if ! gcloud auth print-access-token &> /dev/null; then
    echo -e "  ${RED}✗ Google Cloud CLI session is not valid or has expired${NC}"
    echo -e "    ${YELLOW}Fix by running: gcloud auth login${NC}"
    HAS_ERROR=1
else
    echo -e "  ${GREEN}✓ Google Cloud CLI authenticated (Account: $(gcloud config get-value account 2>/dev/null))${NC}"
fi

if [[ ! "$ENABLE_GITOPS" =~ ^[Nn] ]]; then
    if ! gh auth status &> /dev/null; then
        echo -e "  ${RED}✗ GitHub CLI (gh) is not authenticated${NC}"
        echo -e "    ${YELLOW}Fix by running: gh auth login${NC}"
        HAS_ERROR=1
    else
        CURRENT_GITHUB_USER=$(gh api user -q '.login' 2>/dev/null || echo "")
        echo -e "  ${GREEN}✓ GitHub CLI authenticated (User: $CURRENT_GITHUB_USER)${NC}"
    fi
fi

if ! gcloud auth application-default print-access-token &> /dev/null; then
    echo -e "  ${RED}✗ Google Cloud (Application Default Credentials) not authenticated${NC}"
    echo -e "    ${YELLOW}Fix by running: gcloud auth application-default login${NC}"
    HAS_ERROR=1
else
    DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    ADC_EMAIL=$(curl -s "https://oauth2.googleapis.com/tokeninfo?access_token=$(gcloud auth application-default print-access-token)" | jq -r '.email // empty' 2>/dev/null || echo "")
    ADC_FILE="$(gcloud info --format='value(config.paths.global_config_dir)' 2>/dev/null || echo "")/application_default_credentials.json"
    ADC_QUOTA_PROJECT=$(jq -r '.quota_project_id // empty' "$ADC_FILE" 2>/dev/null || echo "")

    if [ -n "$DEFAULT_PROJECT" ]; then
        echo -e "  ${GREEN}✓ Google Cloud authenticated (Default Project: $DEFAULT_PROJECT)${NC}"
    else
        echo -e "  ${GREEN}✓ Google Cloud authenticated${NC}"
    fi

    if [ -n "$ADC_EMAIL" ]; then
        echo -e "    ${YELLOW}↳ ADC identity: $ADC_EMAIL${NC}"
    fi

    if [ -n "$ADC_QUOTA_PROJECT" ] && [ -n "$DEFAULT_PROJECT" ] && [ "$ADC_QUOTA_PROJECT" != "$DEFAULT_PROJECT" ]; then
        echo -e "    ${YELLOW}⚠ ADC quota project ('$ADC_QUOTA_PROJECT') differs from gcloud's active project ('$DEFAULT_PROJECT'). This may cause 'set-quota-project' errors later.${NC}"
    fi
fi

if [ $HAS_ERROR -eq 1 ]; then
    echo -e "\n${RED}Aborting. Please fix the authentication errors above and try again.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✓ All prerequisites and authentications validated!${NC}"
echo ""

# --- Wizard: Global Configuration Collection ---
echo -e "${BLUE}--- Step 1: Global Configuration ---${NC}"

# Project ID
echo "Fetching your available GCP projects..."
PROJECTS_LIST=$(gcloud projects list --format="value(projectId)" 2>/dev/null || echo "")

if [ -n "$PROJECTS_LIST" ]; then
    echo "Available projects:"
    # Read the list into an array (compatible with bash 3.x on macOS)
    PROJECT_ARRAY=()
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            PROJECT_ARRAY+=("$line")
        fi
    done <<< "$PROJECTS_LIST"
    
    # Print numbered list
    for i in "${!PROJECT_ARRAY[@]}"; do
        echo "$((i+1))) ${PROJECT_ARRAY[$i]}"
    done
    echo ""
    echo "Enter the number corresponding to your project, or type a Project ID manually."
else
    echo -e "${YELLOW}Could not automatically fetch project list (or list is empty).${NC}"
fi

while true; do
    read -p "Select GCP Project (number or ID) [$DEFAULT_PROJECT]: " INPUT_PROJECT
    INPUT_PROJECT=${INPUT_PROJECT:-$DEFAULT_PROJECT}
    
    # Check if the input is a valid number from our list
    if [[ "$INPUT_PROJECT" =~ ^[0-9]+$ ]] && [ "$INPUT_PROJECT" -ge 1 ] && [ "$INPUT_PROJECT" -le "${#PROJECT_ARRAY[@]}" ]; then
        PROJECT_ID="${PROJECT_ARRAY[$((INPUT_PROJECT-1))]}"
    else
        PROJECT_ID="$INPUT_PROJECT"
    fi

    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Project ID is required.${NC}"
        continue
    fi

    echo "Checking if GCP Project '$PROJECT_ID' exists and is accessible..."
    if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        echo -e "${GREEN}✓ Project '$PROJECT_ID' verified.${NC}"
        
        echo -e "${YELLOW}Are you SURE you want to deploy to project: $PROJECT_ID? (Y/n)${NC}"
        read -p "> " CONFIRM_PROJECT
        if [[ "$CONFIRM_PROJECT" =~ ^[Nn] ]]; then
            echo "Please select again."
            continue
        fi
        echo ""
        echo -e "${BLUE}Checking IAM permissions on '$PROJECT_ID' for $(gcloud config get-value account 2>/dev/null)...${NC}"

        REQUIRED_PERMISSIONS=(
            "serviceusage.services.enable"
            "servicemanagement.services.bind"
            "resourcemanager.projects.get"
            "resourcemanager.projects.setIamPolicy"
            "iam.serviceAccounts.create"
            "iam.serviceAccounts.get"
            "iam.serviceAccounts.actAs"
            "storage.buckets.create"
            "bigquery.datasets.create"
            "cloudfunctions.functions.create"
            "run.services.create"
            "apigateway.apis.create"
            "apikeys.keys.create"
            "artifactregistry.repositories.create"
        )

        PERM_JSON_ITEMS=$(printf '"%s",' "${REQUIRED_PERMISSIONS[@]}")
        PERM_JSON="[${PERM_JSON_ITEMS%,}]"
        REQUEST_BODY=$(printf '{"permissions": %s}' "$PERM_JSON")

        RESPONSE=$(curl -s -X POST \
            -H "Authorization: Bearer $(gcloud auth application-default print-access-token 2>/dev/null)" \
            -H "Content-Type: application/json; charset=utf-8" \
            -d "$REQUEST_BODY" \
            "https://cloudresourcemanager.googleapis.com/v1/projects/${PROJECT_ID}:testIamPermissions" 2>&1) || true

        if [ -z "$RESPONSE" ] || echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
            echo -e "${YELLOW}Warning: could not run the permission check.${NC}"
            if [ -n "$RESPONSE" ]; then
                echo "$RESPONSE" | jq -r '.error.message // .' 2>/dev/null || echo "$RESPONSE"
            fi
            echo -e "${YELLOW}Skipping this check and continuing.${NC}"
        else
            GRANTED=$(echo "$RESPONSE" | jq -r '.permissions[]? // empty')
            MISSING=()
            for p in "${REQUIRED_PERMISSIONS[@]}"; do
                if ! echo "$GRANTED" | grep -qx "$p"; then
                    MISSING+=("$p")
                fi
            done

            if [ ${#MISSING[@]} -gt 0 ]; then
                echo -e "${RED}✗ Missing permissions on '$PROJECT_ID':${NC}"
                for p in "${MISSING[@]}"; do
                    echo "   - $p"
                done
                echo -e "${YELLOW}You likely need the Owner or Editor role on this project (see README.md for the full breakdown). Ask a project admin, or if you're allowed to self-grant:${NC}"
                echo -e "${CYAN}  gcloud projects add-iam-policy-binding $PROJECT_ID --member=\"user:$(gcloud config get-value account)\" --role=\"roles/editor\"${NC}"
                read -p "Continue anyway? (y/N) " CONTINUE_WITHOUT_PERMS
                if [[ ! "$CONTINUE_WITHOUT_PERMS" =~ ^[Yy] ]]; then
                    exit 1
                fi
            else
                echo -e "${GREEN}✓ All checked permissions present.${NC}"
            fi
        fi

        echo -e "${YELLOW}Enabling foundational GCP APIs for Terraform... (this takes ~15 seconds)${NC}"
        gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com iam.googleapis.com iap.googleapis.com cloudbuild.googleapis.com --project="$PROJECT_ID" --quiet < /dev/null
        
        while true; do
            echo -e "${YELLOW}Setting Application Default Credentials quota project...${NC}"
            if ADC_ERR=$(gcloud auth application-default set-quota-project "$PROJECT_ID" 2>&1); then
                echo -e "${GREEN}✓ ADC quota project set to '$PROJECT_ID'.${NC}"
                break
            fi

            echo -e "${RED}✗ Could not set the ADC quota project.${NC}"
            echo -e "${YELLOW}gcloud said:${NC}"
            echo "$ADC_ERR"
            echo ""
            echo -e "${BLUE}--- Your current context ---${NC}"
            echo -e "  Active gcloud configuration    : $(gcloud config configurations list --filter='is_active=true' --format='value(name)' 2>/dev/null)"
            echo -e "  Active gcloud CLI account      : $(gcloud config get-value account 2>/dev/null)"
            echo -e "  ADC account (used by Terraform) : ${ADC_EMAIL:-unknown}"
            echo -e "  Active project (gcloud config) : $(gcloud config get-value project 2>/dev/null)"
            echo -e "  Target project (this install)  : $PROJECT_ID"
            echo ""
            echo -e "${YELLOW}This usually means either: (a) 'serviceusage.googleapis.com' hasn't finished propagating yet, or (b) the ADC account above ('${ADC_EMAIL:-unknown}') lacks the Service Usage Consumer role on '$PROJECT_ID'.${NC}"
            echo -e "${RED}This must be fixed before continuing — API Keys, API Gateway, and IAP resources later in this install are known to fail without a working ADC quota project.${NC}"
            echo ""
            echo "What do you want to do?"
            echo "  1) Re-authenticate ADC now (opens browser)"
            echo "  2) I fixed it in another terminal — retry now"
            echo "  3) Wait 15 seconds and retry (in case this is just API propagation)"
            echo "  4) Abort installation"
            read -p "> " ADC_FIX_CHOICE
            case "$ADC_FIX_CHOICE" in
                1)
                    echo -e "${YELLOW}Opening browser to re-authenticate Application Default Credentials...${NC}"
                    if ! gcloud auth application-default login; then
                        echo -e "${RED}ADC re-authentication failed or was cancelled.${NC}"
                    fi
                    ADC_EMAIL=$(curl -s "https://oauth2.googleapis.com/tokeninfo?access_token=$(gcloud auth application-default print-access-token)" | jq -r '.email // empty' 2>/dev/null || echo "")
                    echo -e "${GREEN}✓ ADC identity is now: ${ADC_EMAIL:-unknown}${NC}"
                    ;;
                3)
                    echo "Waiting 15 seconds..."
                    sleep 15
                    ;;
                4)
                    echo -e "${RED}Aborting installation. Fix ADC and re-run this script when ready.${NC}"
                    exit 1
                    ;;
                *)
                    echo -e "${YELLOW}Retrying...${NC}"
                    ;;
            esac
        done
        break
    else
        echo -e "${RED}Error: Project '$PROJECT_ID' does not exist or you don't have access to it.${NC}"
        echo -e "${YELLOW}Please verify the Project ID and try again.${NC}"
    fi
done

# Region
while true; do
    read -p "GCP Region [europe-west1]: " INPUT_REGION
    REGION=${INPUT_REGION:-europe-west1}

    echo "Verifying if Region '$REGION' is valid..."
    
    # SAFE CHECK: First verify if Compute API is enabled WITHOUT triggering the command that drops into interactive loops.
    # We pipe < /dev/null to absolutely guarantee gcloud cannot freeze waiting for keyboard input.
    API_CHECK=$(gcloud services list --enabled --filter="config.name:compute.googleapis.com" --project="$PROJECT_ID" --format="value(config.name)" < /dev/null 2>/dev/null || true)
    
    if [ "$API_CHECK" != "compute.googleapis.com" ]; then
        echo -e "${YELLOW}The Compute Engine API (compute.googleapis.com) must be enabled to verify regions on this account.${NC}"
        read -p "Would you like the script to enable it for you automatically? (Y/n) " ENABLE_COMPUTE
        if [[ ! "$ENABLE_COMPUTE" =~ ^[Nn] ]]; then
            echo "Enabling compute.googleapis.com... (hang tight, this takes about 30 seconds)"
            gcloud services enable compute.googleapis.com --project="$PROJECT_ID" --quiet < /dev/null
            echo -e "${GREEN}✓ API enabled! Resuming region verification...${NC}"
        else
            echo -e "${YELLOW}Skipping strict verification. We will trust your manual input: $REGION${NC}"
            break
        fi
    fi

    # Now it is safe to run the actual region check
    REGION_ERROR=$(gcloud compute regions describe "$REGION" --project="$PROJECT_ID" --quiet < /dev/null 2>&1 > /dev/null || true)

    if [ -z "$REGION_ERROR" ]; then
        echo -e "${GREEN}✓ Region '$REGION' verified.${NC}"
        break
    else
        echo -e "${RED}Error: Region '$REGION' could not be verified.${NC}"
        echo -e "${YELLOW}Reason: $REGION_ERROR${NC}"
        
        if [[ "$REGION_ERROR" == *"billing-enabled"* ]] || [[ "$REGION_ERROR" == *"BILLING_NOT_FOUND"* ]]; then
            echo -e "${RED}CRITICAL: Billing is not enabled for project '$PROJECT_ID'.${NC}"
            echo -e "${YELLOW}Please visit https://console.cloud.google.com/billing and link a billing account to proceed.${NC}"
            exit 1
        fi
        
        echo -e "${YELLOW}Please enter a valid GCP region (e.g., europe-west1, us-central1).${NC}"
    fi
done

echo ""
echo -e "${BLUE}--- Step 2: GitHub Repository Setup ---${NC}"

if [[ ! "$ENABLE_GITOPS" =~ ^[Nn] ]]; then
    echo "This script requires a GitHub Personal Access Token (PAT)."
    echo "It MUST have the following scopes checked: [repo] and [workflow]."
    echo -e "${YELLOW}Generate one quickly here: https://github.com/settings/tokens/new?scopes=repo,workflow&description=Event+Validator+Deployment${NC}"
    echo ""

while true; do
    read -p "GitHub Personal Access Token: " GITHUB_TOKEN_INPUT
    # Remove any whitespaces
    GITHUB_TOKEN=$(echo "$GITHUB_TOKEN_INPUT" | tr -d '[:space:]')

    if [ -z "$GITHUB_TOKEN" ]; then
        echo -e "${RED}GitHub token is required to setup the UI integration.${NC}"
        continue
    fi

    echo "Verifying GitHub Token..."
    # The 'gh api' command will fail if the token is completely invalid
    if ! gh api user -H "Authorization: bearer $GITHUB_TOKEN" &> /dev/null; then
        echo -e "${RED}Error: This GitHub token is invalid or has insufficient permissions.${NC}"
        continue
    fi
    echo -e "${GREEN}✓ GitHub Token verified.${NC}"
    break
done

# The token implicitly acts on behalf of the user who owns it
SCHEMA_REPO_OWNER=$CURRENT_GITHUB_USER

while true; do
    read -p "Schema Repository Name [event-schemas]: " INPUT_REPO
    SCHEMA_REPO_NAME=${INPUT_REPO:-event-schemas}

    echo ""
    echo "Checking if repository $SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME exists..."

    if gh repo view "$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME" &> /dev/null; then
        echo -e "${YELLOW}Repository '$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME' already exists.${NC}"
        echo "Do you want to use this existing repository? (Y/n)"
        read -p "> " USE_EXISTING
        if [[ "$USE_EXISTING" =~ ^[Nn] ]]; then
            echo -e "${YELLOW}Please provide a different repository name.${NC}"
            continue # Restart the loop to ask for a new name
        fi
        echo -e "${GREEN}✓ Will use existing repository.${NC}"
        break
    else
        echo -e "${BLUE}Repository '$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME' does NOT exist.${NC}"
        echo "Do you want to create it now? (Y/n)"
        read -p "> " CREATE_REPO
        if [[ ! "$CREATE_REPO" =~ ^[Nn] ]]; then
            echo -e "${YELLOW}Creating repository $SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME...${NC}"
            read -p "Should it be private? (Y/n) " IS_PRIVATE
            VISIBILITY="--private"
            if [[ "$IS_PRIVATE" =~ ^[Nn] ]]; then VISIBILITY="--public"; fi

            echo "Executing: gh repo create \"$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME\" $VISIBILITY"
            if ! gh repo create "$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME" $VISIBILITY; then
                echo -e "${RED}Error: Failed to create repository '$SCHEMA_REPO_NAME'.${NC}"
                echo -e "${YELLOW}Your logged-in CLI user might lack organization permissions, or the name is invalid.${NC}"
                continue
            fi

            # Temporary clone to push main
            TEMP_DIR=$(mktemp -d)
            cd "$TEMP_DIR"
            gh repo clone "$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME" . >/dev/null
            touch .gitkeep && git add .gitkeep
            git commit -m "Initial commit" >/dev/null
            git branch -M main
            git push -u origin main >/dev/null
            cd - >/dev/null
            rm -rf "$TEMP_DIR"
            echo -e "${GREEN}✓ Repository created & initialized!${NC}"
            break
        else
            echo -e "${YELLOW}You chose not to create the repository now.${NC}"
            echo -e "Make sure it exists before Terraform deployment, or the build might fail."
            echo "Are you sure you want to proceed with this configuration? (Y/n)"
            read -p "> " PROCEED_ANYWAY
            if [[ ! "$PROCEED_ANYWAY" =~ ^[Nn] ]]; then
                break
            else
                echo -e "${YELLOW}Please provide a different repository name.${NC}"
                continue
            fi
        fi
    fi
done

echo "Do you want to enable Branch Protection?"
echo "This requires GitHub Pro/Team plan for private repositories or a Public repository."
read -p "Enable Branch Protection? (y/N) " INPUT_PROTECTION
if [[ "$INPUT_PROTECTION" =~ ^[Yy] ]]; then PROTECT_TF="true"; else PROTECT_TF="false"; fi

else
    echo -e "${YELLOW}Skipping GitHub GitOps setup. The backend will run natively without a repository pipeline.${NC}"
    GITHUB_TOKEN=""
    SCHEMA_REPO_OWNER=""
    SCHEMA_REPO_NAME=""
    PROTECT_TF="false"
fi

# Secondary Backend Settings & Advanced Customization
echo ""
echo -e "${BLUE}--- Step 2.5: Infrastructure & Advanced Settings ---${NC}"
echo "Configure Cloud Function scaling to handle varying levels of traffic."
read -p "Backend Max Instances [10]: " INPUT_MAX_INSTANCES
BACKEND_MAX_INST=${INPUT_MAX_INSTANCES:-10}

read -p "Backend Min Instances (0 to save costs, 1 to prevent cold-starts) [0]: " INPUT_MIN_INSTANCES
BACKEND_MIN_INST=${INPUT_MIN_INSTANCES:-0}

echo ""
echo "By default, the validator looks for events formatted as: { \"event_name\": \"...\", \"data\": {...} }"
echo "It also logs all errors to BigQuery by default."
read -p "Do you want to customize these Advanced Payload & Logging Settings? (y/N) " CUSTOMIZE_ADVANCED

if [[ "$CUSTOMIZE_ADVANCED" =~ ^[Yy] ]]; then
    read -p "Event Name Attribute [event_name]: " INPUT_EVENT_NAME
    EVENT_NAME_ATTR=${INPUT_EVENT_NAME:-event_name}
    
    read -p "Event Data Path [data]: " INPUT_EVENT_DATA
    EVENT_DATA_PATH=${INPUT_EVENT_DATA:-data}
    
    read -p "Log individual valid fields to BigQuery? (Y/n) " INPUT_LOG_FIELDS
    if [[ "$INPUT_LOG_FIELDS" =~ ^[Nn] ]]; then LOG_VALID_FIELDS="false"; else LOG_VALID_FIELDS="true"; fi

    read -p "Log full payload when validation fails? (Y/n) " INPUT_LOG_ERRORS
    if [[ "$INPUT_LOG_ERRORS" =~ ^[Nn] ]]; then LOG_PAYLOAD_ERROR="false"; else LOG_PAYLOAD_ERROR="true"; fi

    read -p "Log full payload when validation passes? (y/N) " INPUT_LOG_PASS
    if [[ "$INPUT_LOG_PASS" =~ ^[Yy] ]]; then LOG_PAYLOAD_VALID="true"; else LOG_PAYLOAD_VALID="false"; fi
else
    echo -e "${YELLOW}Using default Payload & Logging settings.${NC}"
    EVENT_NAME_ATTR="event_name"
    EVENT_DATA_PATH="data"
    LOG_VALID_FIELDS="true"
    LOG_PAYLOAD_ERROR="true"
    LOG_PAYLOAD_VALID="false"
fi

# Backend Configuration Gen
echo ""
echo -e "${BLUE}Generating backend terraform.tfvars...${NC}"

cat <<EOF > terraform_backend/terraform.tfvars
project_id          = "$PROJECT_ID"
location            = "$REGION"
region              = "$REGION"
function_source_dir = "../validator_src"
bq_schema_file      = "src/bq_schema/bq_schema.json"

EVENT_NAME_ATTRIBUTE        = "$EVENT_NAME_ATTR"
EVENT_DATA_PATH             = "$EVENT_DATA_PATH"
LOG_VALID_FIELDS_FLAG       = $LOG_VALID_FIELDS
LOG_PAYLOAD_WHEN_ERROR_FLAG = $LOG_PAYLOAD_ERROR
LOG_PAYLOAD_WHEN_VALID_FLAG = $LOG_PAYLOAD_VALID

backend_min_instances = $BACKEND_MIN_INST
backend_max_instances = $BACKEND_MAX_INST

deletion_protection   = false
force_destroy_buckets = true

# GitHub Integration
github_token          = "$GITHUB_TOKEN"
schema_repo_owner     = "$SCHEMA_REPO_OWNER"
schema_repo_name      = "$SCHEMA_REPO_NAME"
enable_branch_protection = $PROTECT_TF
EOF

echo -e "${GREEN}✓ Backend variables configured.${NC}"

# --- Step 3: Backend Deployment ---
echo ""
echo -e "${BLUE}--- Step 3: Deploying Backend ---${NC}"

read -p "Ready to run 'terraform apply' for Backend? (Y/n) " CONFIRM_BACKEND
if [[ ! "$CONFIRM_BACKEND" =~ ^[Nn] ]]; then
   cd terraform_backend
   terraform init
   terraform apply -auto-approve
   echo ""
   echo -e "${GREEN}✓ Backend Deploy Complete.${NC}"
   
   # Parse outputs
   echo "Fetching Terraform backend outputs..."
   SCHEMAS_BUCKET=$(terraform output -raw schemas_bucket 2>/dev/null || echo "")
   BQ_DATASET=$(terraform output -raw bq_dataset 2>/dev/null || echo "event_data_dataset")
   BQ_TABLE=$(terraform output -raw bq_table 2>/dev/null || echo "event_data_table")
   API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
   API_KEY=$(terraform output -raw api_key 2>/dev/null || echo "")
   cd ..
else
   echo -e "${YELLOW}Skipping Backend deployment.${NC}"
   echo "Attempting to fetch existing Terraform backend outputs..."
   cd terraform_backend
   SCHEMAS_BUCKET=$(terraform output -raw schemas_bucket 2>/dev/null || echo "")
   BQ_DATASET=$(terraform output -raw bq_dataset 2>/dev/null || echo "event_data_dataset")
   BQ_TABLE=$(terraform output -raw bq_table 2>/dev/null || echo "event_data_table")
   API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
   API_KEY=$(terraform output -raw api_key 2>/dev/null || echo "")
   cd ..

   if [ -z "$SCHEMAS_BUCKET" ]; then
       echo -e "${YELLOW}Could not find existing backend outputs in the terraform state.${NC}"
       echo "To proceed with UI deployment, please provide the backend resources manually:"
       
       read -p "Schemas Bucket Name (e.g. event_validator_schemas_bucket-123): " SCHEMAS_BUCKET
       if [ -z "$SCHEMAS_BUCKET" ]; then
           echo -e "${RED}Schemas Bucket is strictly required for the UI. Exiting.${NC}"
           exit 1
       fi
       
       read -p "BigQuery Dataset [event_data_dataset]: " INPUT_BQ_DATASET
       BQ_DATASET=${INPUT_BQ_DATASET:-event_data_dataset}
       
       read -p "BigQuery Table [event_data_table]: " INPUT_BQ_TABLE
       BQ_TABLE=${INPUT_BQ_TABLE:-event_data_table}
   else
       echo -e "${GREEN}✓ Found existing backend variables.${NC}"
   fi
fi

echo ""
echo -e "${BLUE}--- UI Deployment ---${NC}"

echo "The Streamlit UI gives you a dashboard to manage schemas on Cloud Run."
read -p "Do you want to deploy the UI Frontend? (Y/n) " DEPLOY_UI
if [[ "$DEPLOY_UI" =~ ^[Nn] ]]; then
   echo -e "${GREEN}Finished! Only backend was deployed.${NC}"
   echo -e "${BLUE}API Gateway URL:${NC} https://$API_URL"
   echo -e "${BLUE}API Gateway Key:${NC} $API_KEY"

   if [[ -n "$BACKEND_MIN_INST" ]] && [ "$BACKEND_MIN_INST" -gt 0 ] 2>/dev/null; then
       echo ""
       echo -e "${CYAN}--- Running API Health Check ---${NC}"
       echo "Testing API Gateway endpoint... (Warning: newly deployed APIs may take 10-15 mins to propagate)."
       
       RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://${API_URL}/eventsValidator?key=${API_KEY}" \
          -H "Content-Type: application/json" \
          -d '{"data": {"event_name": "install_validation_test"}}')
          
       HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
       BODY=$(echo "$RESPONSE" | sed '$ d')
       
       if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "404" ] || [ "$HTTP_CODE" == "400" ]; then
           echo -e "${GREEN}✓ API responded with logic code $HTTP_CODE! Cloud Function is connected and alive!${NC}"
           echo -e "Response: $BODY"
       elif [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "503" ] || [ "$HTTP_CODE" == "401" ]; then
           echo -e "${YELLOW}API is currently returning $HTTP_CODE (Network/Auth Pending).${NC}"
           echo -e "${YELLOW}This is completely normal. Please allow 10-15 minutes for API Gateway limits to propagate!${NC}"
       else
           echo -e "${RED}API response HTTP $HTTP_CODE.${NC}"
           echo "$BODY"
       fi
   else
       echo ""
       echo -e "${YELLOW}Important:${NC} It may take up to 10-15 minutes for the API Gateway to fully propagate."
   fi

   exit 0
fi

# --- Step 4: UI Configuration Collection ---
echo ""
echo -e "${BLUE}--- Step 4: Streamlit UI Configuration ---${NC}"
echo "Configure Streamlit UI scaling."
read -p "UI Max Instances [2]: " INPUT_UI_MAX
UI_MAX_INST=${INPUT_UI_MAX:-2}

read -p "UI Min Instances (0 to save costs, 1 to prevent cold-starts) [0]: " INPUT_UI_MIN
UI_MIN_INST=${INPUT_UI_MIN:-0}

echo ""
echo "Do you want to use Classic Global Load Balancer (\$18/mo) for standard IAP?"
echo "If NO, it will use Cloud Run Direct Integration (Cheaper/Free, Preview feature)."
read -p "Use Classic Load Balancer? (y/N) " INPUT_LB
if [[ "$INPUT_LB" =~ ^[Yy] ]]; then USE_LB="true"; else USE_LB="false"; fi

echo ""
echo -e "${YELLOW}--- Security Notice: OAuth Consent Screen ---${NC}"
echo "We need Identity-Aware Proxy (IAP) OAuth credentials to protect the UI."
echo -e "However, on a new project, Google requires you to configure the ${YELLOW}Google Auth Platform${NC} (formerly 'OAuth consent screen') first."
echo ""
echo -e "1. Go to: ${CYAN}https://console.cloud.google.com/auth/branding?project=$PROJECT_ID${NC}"
echo -e "2. Fill in the required App Name and Support Email, then click Save."
echo -e "3. Go to the 'Audience' tab: ${CYAN}https://console.cloud.google.com/auth/audience?project=$PROJECT_ID${NC}"
echo -e "4. Choose 'Internal' (Workspace only) or 'External' (any Google account)."
echo -e "5. If you chose External and the app stays in 'Testing' status, you MUST add every user you plan to authorize as a Test User on this same page — otherwise Google's own login screen will block them, even though IAP's IAM policy allows them."
echo -e "   ${RED}Note: Test user access expires after 7 days and needs re-approving. For anything beyond a quick trial, consider publishing to 'Production' instead — no Google review is needed as long as you don't request extra scopes.${NC}"
echo -e "6. NEXT, go to the 'Clients' tab: ${CYAN}https://console.cloud.google.com/auth/clients?project=$PROJECT_ID${NC}"
echo -e "7. Click 'Create Client' -> 'Web application'."
echo ""

while true; do
    read -p "Have you created the OAuth Consent Screen and your Client Credentials? (Y/n) " CONFIRM_OAUTH
    if [[ "$CONFIRM_OAUTH" =~ ^[Nn] ]]; then
        echo -e "${YELLOW}Please complete the steps in your browser first. The script is waiting patiently...${NC}"
        continue
    fi
    break
done

echo ""

while true; do
    read -p "IAP OAuth Client ID: " IAP_CLIENT_ID
    # Remove whitespaces
    IAP_CLIENT_ID=$(echo "$IAP_CLIENT_ID" | tr -d '[:space:]')
    if [ -z "$IAP_CLIENT_ID" ]; then
        echo -e "${RED}IAP Client ID is required.${NC}"
        continue
    fi
    
    if [[ ! "$IAP_CLIENT_ID" == *apps.googleusercontent.com ]] && [[ ! "$IAP_CLIENT_ID" == *.apps.googleusercontent.com ]]; then
        echo -e "${YELLOW}Warning: A typical IAP Client ID ends with 'apps.googleusercontent.com'.${NC}"
        read -p "Are you sure you entered the Client ID? (y/N) " CONFIRM_ID
        if [[ ! "$CONFIRM_ID" =~ ^[Yy] ]]; then
            continue
        fi
    fi
    break
done

echo ""
echo -e "${YELLOW}--- ACTION REQUIRED: Add Redirect URI to your OAuth Client ---${NC}"
echo -e "Because you are using Identity-Aware Proxy (IAP), Google requires a specific Authorized Redirect URI."
echo ""
echo -e "1. Go back to the Clients tab: ${CYAN}https://console.cloud.google.com/auth/clients?project=$PROJECT_ID${NC}"
echo -e "2. Click the Web Application client you just created to open it."
echo -e "3. Scroll down to ${CYAN}'Authorized redirect URIs'${NC} and click 'ADD URI'."
echo -e "4. Copy and paste this EXACT URL into the box:"
echo -e "   ${GREEN}https://iap.googleapis.com/v1/oauth/clientIds/${IAP_CLIENT_ID}:handleRedirect${NC}"
echo -e "5. Click 'Save' at the bottom of the page."
echo ""
while true; do
    read -p "Have you added and saved the Redirect URI? (Y/n) " CONFIRM_URI
    if [[ "$CONFIRM_URI" =~ ^[Nn] ]]; then
        echo -e "${YELLOW}Please complete the steps in your browser first...${NC}"
        continue
    fi
    break
done

echo ""

while true; do
    read -p "IAP OAuth Client Secret: " IAP_CLIENT_SECRET
    # Remove whitespaces
    IAP_CLIENT_SECRET=$(echo "$IAP_CLIENT_SECRET" | tr -d '[:space:]')
    if [ -z "$IAP_CLIENT_SECRET" ]; then
        echo -e "${RED}IAP Client Secret is required.${NC}"
        continue
    fi
    
    # Check if they pasted the Client ID by mistake
    if [[ "$IAP_CLIENT_SECRET" == *apps.googleusercontent.com ]] || [[ "$IAP_CLIENT_SECRET" == *.apps.googleusercontent.com ]]; then
        echo -e "${RED}Error: That looks like a Client ID! The Client Secret should be a shorter, random string.${NC}"
        continue
    fi
    
    # Check if it lacks the typical Google prefix
    if [[ ! "$IAP_CLIENT_SECRET" == GOCSPX-* ]]; then
        echo -e "${YELLOW}Warning: A typical modern Client Secret starts with 'GOCSPX-'.${NC}"
        read -p "Are you sure this is the correct Client Secret? (y/N) " CONFIRM_SECRET
        if [[ ! "$CONFIRM_SECRET" =~ ^[Yy] ]]; then
            continue
        fi
    fi
    break
done

while true; do
    read -p "Authorized Users (comma separated, e.g. user:test@example.com): " INPUT_USERS
    if [ -z "$INPUT_USERS" ]; then
        echo -e "${RED}At least one authorized user is required.${NC}"
        continue
    fi
    # Split and format users for terraform list
    IFS=',' read -ra ADDR <<< "$INPUT_USERS"
    USERS_TF_LIST="["
    for i in "${!ADDR[@]}"; do
        USER_CLEAN=$(echo "${ADDR[$i]}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        # Check if the user starts with the required prefix, if not, auto-append "user:" 
        if [[ ! "$USER_CLEAN" == user:* ]] && [[ ! "$USER_CLEAN" == serviceAccount:* ]] && [[ ! "$USER_CLEAN" == group:* ]] && [[ ! "$USER_CLEAN" == domain:* ]]; then
            USER_CLEAN="user:$USER_CLEAN"
            echo -e "${YELLOW}Auto-added 'user:' prefix -> $USER_CLEAN${NC}"
        fi
        
        USERS_TF_LIST+="\"$USER_CLEAN\""
        if [ $i -lt $((${#ADDR[@]}-1)) ]; then
            USERS_TF_LIST+=", "
        fi
    done
    USERS_TF_LIST+="]"
    break
done

echo ""
echo -e "${BLUE}Generating UI terraform.tfvars...${NC}"

cat <<EOF > terraform_ui/terraform.tfvars
project_id             = "$PROJECT_ID"
region                 = "$REGION"

# Backend Integration
schemas_bucket         = "$SCHEMAS_BUCKET"
bq_dataset             = "$BQ_DATASET"
bq_table               = "$BQ_TABLE"

ui_min_instances       = $UI_MIN_INST
ui_max_instances       = $UI_MAX_INST

# IAP Configuration
iap_client_id          = "$IAP_CLIENT_ID"
iap_client_secret      = "$IAP_CLIENT_SECRET"
authorized_users       = $USERS_TF_LIST
streamlit_image_tag    = "latest"

# Security mode
use_classic_load_balancer = $USE_LB


# GitHub Integration
github_token           = "$GITHUB_TOKEN"
schema_repo_owner      = "$SCHEMA_REPO_OWNER"
schema_repo_name       = "$SCHEMA_REPO_NAME"
schema_repo_path       = "schemas"
schema_repo_branch     = "main"
EOF

echo -e "${GREEN}✓ UI variables configured.${NC}"

# --- Step 5.5: Build UI Image ---
echo ""
echo -e "${BLUE}--- Step 5.5: Build UI Docker Image ---${NC}"
echo "We need to build the Streamlit UI container and push it to Google Cloud Artifact Registry."
read -p "Ready to build and push the UI image? (Y/n) " CONFIRM_BUILD
if [[ ! "$CONFIRM_BUILD" =~ ^[Nn] ]]; then
   # Terraform needs to create the Artifact Registry repo first.
   # So we initialize UI terraform and apply JUST the repository resource
   cd terraform_ui
   terraform init >/dev/null 2>&1
   
   echo -e "${YELLOW}Provisioning Artifact Registry Repository...${NC}"
   if ! terraform apply -target="google_artifact_registry_repository.streamlit_repo" -target="google_project_iam_member.cloudbuild_artifact_writer" -auto-approve >/dev/null; then
       echo -e "${RED}Error: Failed to provision the Artifact Registry repository.${NC}"
       echo -e "${YELLOW}Hint: Ensure 'artifactregistry.googleapis.com' API is enabled and your user has sufficient IAM permissions.${NC}"
       exit 1
   fi

   cd ..
   echo -e "${YELLOW}Building Docker Image via Cloud Build... (this may take 2-4 minutes)${NC}"
   if ! gcloud builds submit --project="$PROJECT_ID" --region="$REGION" --tag "$REGION-docker.pkg.dev/$PROJECT_ID/event-validator-ui-repo/event-validator-ui:latest" ./streamlit_ev; then
       echo -e "${RED}Error: Failed to build and push the UI Docker image.${NC}"
       echo -e "${YELLOW}Hint: Ensure 'cloudbuild.googleapis.com' API is enabled and your project has billing attached.${NC}"
       exit 1
   fi
   echo -e "${GREEN}✓ UI Image built and pushed successfully.${NC}"
else
   echo -e "${YELLOW}Skipping UI build... The final deployment might fail if the image doesn't exist.${NC}"
fi

# --- Step 6: UI Deployment ---
echo ""
echo -e "${BLUE}--- Step 6: Deploying UI ---${NC}"
read -p "Ready to run 'terraform apply' for UI infrastructure? (Y/n) " CONFIRM_UI
if [[ ! "$CONFIRM_UI" =~ ^[Nn] ]]; then
   cd terraform_ui
   terraform init
   terraform apply -auto-approve
   
   UI_URL=$(terraform output -raw cloud_run_service_url 2>/dev/null || terraform output -raw streamlit_ui_url 2>/dev/null || echo "")
   cd ..
else
   echo -e "${YELLOW}Skipping UI deployment.${NC}"
   exit 0
fi

# --- Step 6: Final Report ---
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}                 DEPLOYMENT SUCCESSFUL!                         ${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
if [ -n "$UI_URL" ]; then
    echo -e "${BLUE}Streamlit UI URL:${NC} $UI_URL"
fi
echo -e "${BLUE}API Gateway URL:${NC} https://$API_URL"
echo -e "${BLUE}API Gateway Key:${NC} $API_KEY"
echo ""

if [[ -n "$BACKEND_MIN_INST" ]] && [ "$BACKEND_MIN_INST" -gt 0 ] 2>/dev/null; then
    echo -e "${CYAN}--- Running API Health Check ---${NC}"
    echo "Testing API Gateway endpoint... (Warning: newly deployed APIs may take 10-15 mins to propagate)."
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://${API_URL}/eventsValidator?key=${API_KEY}" \
       -H "Content-Type: application/json" \
       -d '{"data": {"event_name": "install_validation_test"}}')
       
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$ d')
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "404" ] || [ "$HTTP_CODE" == "400" ]; then
        echo -e "${GREEN}✓ API responded with logic code $HTTP_CODE! Cloud Function is connected and alive!${NC}"
        echo -e "Response: $BODY"
    elif [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "503" ] || [ "$HTTP_CODE" == "401" ]; then
        echo -e "${YELLOW}API is currently returning $HTTP_CODE (Network/Auth Pending).${NC}"
        echo -e "${YELLOW}This is completely normal. Please allow 10-15 minutes for API Gateway to fully propagate!${NC}"
    else
        echo -e "${RED}API response HTTP $HTTP_CODE.${NC}"
        echo "$BODY"
    fi
else
    echo -e "${YELLOW}Important:${NC} It may take up to 10-15 minutes for the API Gateway and IAP to fully propagate."
fi

echo ""
if [ -n "$GITHUB_TOKEN" ] && [ -n "$SCHEMA_REPO_OWNER" ] && [ -n "$SCHEMA_REPO_NAME" ]; then
    echo "You can view your schema repository at: https://github.com/$SCHEMA_REPO_OWNER/$SCHEMA_REPO_NAME"
fi