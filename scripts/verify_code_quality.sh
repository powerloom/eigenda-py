#!/bin/bash
# Script to verify code quality checks are passing
# Usage: ./verify_code_quality.sh [--fix]

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if --fix flag is provided
FIX_MODE=false
if [ "$1" == "--fix" ] || [ "$1" == "-f" ]; then
    FIX_MODE=true
    echo -e "${YELLOW}=== Running in FIX mode ===${NC}"
    echo "Will automatically fix formatting issues"
else
    echo -e "${GREEN}=== Code Quality Verification ===${NC}"
    echo "Run with --fix flag to automatically fix issues"
fi
echo ""

# Function to run checks or fixes
run_quality_checks() {
    local fix=$1
    local all_passed=true
    
    if [ "$fix" = true ]; then
        # Fix mode - apply formatters
        echo -e "${YELLOW}1. Applying black formatting...${NC}"
        uv run black src/ tests/ examples/
        echo -e "${GREEN}✅ Black formatting applied${NC}"
        echo ""
        
        echo -e "${YELLOW}2. Fixing import sorting with isort...${NC}"
        uv run isort src/ tests/ examples/
        echo -e "${GREEN}✅ Import sorting fixed${NC}"
        echo ""
        
        echo -e "${YELLOW}3. Running flake8 to identify remaining issues...${NC}"
        if uv run flake8 .; then
            echo -e "${GREEN}✅ No linting issues found${NC}"
        else
            echo -e "${YELLOW}⚠️  Some linting issues cannot be auto-fixed${NC}"
            echo "   Please review and fix manually"
            all_passed=false
        fi
    else
        # Check mode - verify without changing
        echo "1. Checking black formatting..."
        if uv run black --check src/ tests/ examples/; then
            echo -e "${GREEN}✅ Black formatting check passed${NC}"
        else
            echo -e "${RED}❌ Black formatting check failed${NC}"
            echo "   Run: ./scripts/verify_code_quality.sh --fix"
            all_passed=false
        fi
        echo ""
        
        echo "2. Checking import sorting with isort..."
        if uv run isort --check-only src/ tests/ examples/; then
            echo -e "${GREEN}✅ Import sorting check passed${NC}"
        else
            echo -e "${RED}❌ Import sorting check failed${NC}"
            echo "   Run: ./scripts/verify_code_quality.sh --fix"
            all_passed=false
        fi
        echo ""
        
        echo "3. Running flake8 linting..."
        if uv run flake8 .; then
            echo -e "${GREEN}✅ Flake8 linting passed${NC}"
        else
            echo -e "${RED}❌ Flake8 linting failed${NC}"
            echo "   Some issues need manual fixing"
            all_passed=false
        fi
    fi
    
    echo ""
    
    # Always run pre-commit check at the end
    echo "4. Running pre-commit hooks (check only)..."
    if uv run pre-commit run --all-files; then
        echo -e "${GREEN}✅ All pre-commit hooks passed${NC}"
    else
        echo -e "${RED}❌ Pre-commit hooks failed${NC}"
        if [ "$fix" = false ]; then
            echo "   Run: ./scripts/verify_code_quality.sh --fix"
        fi
        all_passed=false
    fi
    
    return $([ "$all_passed" = true ] && echo 0 || echo 1)
}

# Run the checks/fixes
if run_quality_checks $FIX_MODE; then
    echo ""
    if [ "$FIX_MODE" = true ]; then
        echo -e "${GREEN}=== ✅ All formatting applied successfully! ===${NC}"
        echo "Please review changes and commit"
    else
        echo -e "${GREEN}=== ✅ All code quality checks passed! ===${NC}"
        echo "Your code is ready for commit!"
    fi
    exit 0
else
    echo ""
    if [ "$FIX_MODE" = true ]; then
        echo -e "${YELLOW}=== ⚠️  Some issues remain after auto-fix ===${NC}"
        echo "Please review and fix remaining issues manually"
    else
        echo -e "${RED}=== ❌ Code quality checks failed ===${NC}"
        echo "Run with --fix flag to auto-fix formatting issues:"
        echo "  ./scripts/verify_code_quality.sh --fix"
    fi
    exit 1
fi