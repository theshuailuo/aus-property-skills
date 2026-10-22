#!/usr/bin/env bash
# validate-skills.sh — check every skill against AGENTS.md before commit.
# Adapted from coreyhaines31/marketingskills validate-skills.sh (MIT), extended for
# this repo: metadata.version, VERSIONS.md sync, orphan references, evals (>=3 + 1
# injection case), shared disclaimers, banned "permission-style" wording, private
# files never tracked, plugin manifests in sync.
#
# Usage:  bash scripts/validate-skills.sh            (from repo root; Git Bash on Windows works)
#         SKILLS_DIRS="path/a path/b" bash scripts/validate-skills.sh
# Exit 0 = no errors (warnings allowed). Exit 1 = at least one error.

export LC_ALL=C.UTF-8 2>/dev/null || true   # count characters, not bytes, for Chinese text

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

# skills/ = published skills; docs/skill-template/ = the writing sample (validated
# too, but exempt from the VERSIONS.md check).
SKILLS_DIRS="${SKILLS_DIRS:-skills docs/skill-template}"
TEMPLATE_DIR="docs/skill-template"

PY="$(command -v python3 || command -v python || true)"
# Windows Store "python3" alias exists but does nothing; make sure it really runs.
if [[ -n "$PY" ]] && ! "$PY" -c "import json" >/dev/null 2>&1; then PY="$(command -v python || true)"; fi
if [[ -n "$PY" ]] && ! "$PY" -c "import json" >/dev/null 2>&1; then PY=""; fi

ISSUES=0; WARNINGS=0; PASSED=0; CHECKED=0

# Wording that reads like permission to skip a professional, or like a promise.
BANNED='不经律师|无需律师|不需要律师|不用请律师|不用律师|无需会计|不需要会计|保证升值|稳赚|一定会涨|without (a|your) (lawyer|solicitor|conveyancer|accountant)|no need (for|to see) (a|an) (lawyer|solicitor|conveyancer|accountant)|guaranteed (return|growth|profit)'

echo "🔍 aus-property-skills · skill validation"
echo "=========================================="

repo_errors=()

# ===== REPO-LEVEL CHECKS =====
if [[ -n "$PY" ]]; then
  for j in .claude-plugin/marketplace.json .claude-plugin/plugin.json; do
    if [[ ! -f "$j" ]]; then repo_errors+=("Missing $j")
    elif ! "$PY" -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" "$j" 2>/dev/null; then
      repo_errors+=("$j is not valid JSON"); fi
  done
  if [[ ${#repo_errors[@]} -eq 0 ]]; then
    vers=$("$PY" -c "
import json
m=json.load(open('.claude-plugin/marketplace.json',encoding='utf-8'))
p=json.load(open('.claude-plugin/plugin.json',encoding='utf-8'))
print(m['metadata']['version'], p['version'])")
    read -r mv pv <<<"$vers"
    [[ "$mv" != "$pv" ]] && repo_errors+=("Version mismatch: marketplace.json=$mv plugin.json=$pv")
    if ! grep -q "^### $pv " VERSIONS.md 2>/dev/null; then
      repo_errors+=("VERSIONS.md has no '### $pv (date)' block for plugin version $pv")
    fi
  fi
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  leaked=$(git ls-files | grep -E '(^|/)[^/]*\.local\.md$|(^|/)buyer-strategy\.md$|(^|/)\.env($|\.)' | grep -v '\.env\.example$' || true)
  [[ -n "$leaked" ]] && repo_errors+=("Private files are tracked by git (must stay local): $(echo $leaked)")
fi

if [[ ${#repo_errors[@]} -gt 0 ]]; then
  echo -e "${RED}❌ repo${NC}"; for e in "${repo_errors[@]}"; do echo -e "   ${RED}Error:${NC} $e"; done
  ((ISSUES++))
else
  echo -e "${GREEN}✓ repo${NC} (plugin manifests, VERSIONS.md, no private files tracked)"
fi
[[ -z "$PY" ]] && { echo -e "${YELLOW}⚠️  python not found — JSON checks skipped${NC}"; ((WARNINGS++)); }

# ===== PER-SKILL CHECKS =====
for base in $SKILLS_DIRS; do
  [[ -d "$base" ]] || continue
  for skill_dir in "$base"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_dir="${skill_dir%/}"
    skill_name=$(basename "$skill_dir")
    [[ "$skill_name" == _* ]] && continue
    ((CHECKED++))
    skill_file="$skill_dir/SKILL.md"
    errs=(); warns=()

    if [[ ! -f "$skill_file" ]]; then
      echo -e "${RED}❌ $skill_dir${NC}"; echo "   Missing SKILL.md"; ((ISSUES++)); continue
    fi

    frontmatter=$(awk '
        { sub(/\r$/, "") }
        NR == 1 && $0 != "---" { exit 1 }
        /^---$/ { count++; if (count == 2) exit; next }
        count == 1 { print }
        END { if (count != 2) exit 1 }
    ' "$skill_file")
    if [[ $? -ne 0 || -z "$frontmatter" ]]; then
      echo -e "${RED}❌ $skill_dir${NC}"; echo "   Missing or unclosed YAML frontmatter (---)"; ((ISSUES++)); continue
    fi

    # name
    name_in_file=$(echo "$frontmatter" | grep "^name:" | sed 's/^name: *//' | tr -d ' "')
    if [[ -z "$name_in_file" ]]; then errs+=("Missing 'name' in frontmatter")
    elif [[ "$name_in_file" != "$skill_name" ]]; then errs+=("Name mismatch: directory='$skill_name' frontmatter='$name_in_file'")
    elif ! [[ "$name_in_file" =~ ^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$ ]] || [[ "$name_in_file" == *--* ]]; then
      errs+=("Invalid name '$name_in_file' (lowercase letters, digits, single hyphens; 1-64 chars)")
    fi

    # description (single line, quoted or not)
    dline=$(echo "$frontmatter" | grep "^description:" | head -1)
    description=$(echo "$dline" | sed -E 's/^description: *//; s/^"//; s/"$//')
    if [[ -z "$description" ]]; then errs+=("Missing 'description'")
    elif [[ "$description" == ">"* || "$description" == "|"* ]]; then errs+=("description must be a single line (no YAML block scalars)")
    else
      dl=${#description}
      (( dl < 1 || dl > 1024 )) && errs+=("description is $dl characters (must be 1-1024)")
      echo "$description" | grep -Eqi '触发|trigger|when|use' || warns+=("description has no trigger phrases (触发 / Triggers / when / use)")
      echo "$description" | grep -Eqi '见|see |not for|不适用|不负责|不在范围' || warns+=("description has no scope boundary ('X 见 Y' / 'For X, see Y' / 'not for')")
    fi

    # license / version
    license=$(echo "$frontmatter" | grep "^license:" | sed 's/^license: *//' | tr -d ' "')
    [[ -n "$license" && "$license" != "MIT" ]] && warns+=("license '$license' is not MIT (repo default)")
    echo "$frontmatter" | grep -q "^version:" && errs+=("'version' is top-level (put it under 'metadata:')")
    skill_ver=$(echo "$frontmatter" | awk '/^metadata:/{m=1;next} m && /^[^ ]/{m=0} m && /^ +version:/{sub(/^ +version: */,""); gsub(/["\047 ]/,""); print; exit}')
    if [[ -z "$skill_ver" ]]; then errs+=("Missing metadata.version")
    elif ! [[ "$skill_ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then errs+=("metadata.version '$skill_ver' is not x.y.z"); fi

    # VERSIONS.md row (published skills only)
    if [[ "$base" != "$TEMPLATE_DIR" && -n "$skill_ver" ]]; then
      row=$(grep -E "^\|\s*$skill_name\s*\|" VERSIONS.md 2>/dev/null | head -1)
      if [[ -z "$row" ]]; then errs+=("No row for '$skill_name' in VERSIONS.md table")
      else
        row_ver=$(echo "$row" | awk -F'|' '{gsub(/ /,"",$3); print $3}')
        [[ "$row_ver" != "$skill_ver" ]] && errs+=("VERSIONS.md says $row_ver but SKILL.md says $skill_ver")
      fi
    fi

    # length
    lc=$(wc -l < "$skill_file")
    (( lc >= 500 )) && errs+=("SKILL.md is $lc lines (must be <500; move detail to references/)")

    # Claude-only syntax in a cross-agent skill
    grep -q '!`' "$skill_file" && warns+=("SKILL.md contains '!\`' command injection (Claude Code only; keep it in a private overlay)")

    # references: every file must be linked from SKILL.md
    if [[ -d "$skill_dir/references" ]]; then
      while IFS= read -r ref; do
        [[ -z "$ref" ]] && continue
        rel="${ref#$skill_dir/}"
        grep -qF "$rel" "$skill_file" || errs+=("Orphan reference: $rel is not linked from SKILL.md")
      done < <(find "$skill_dir/references" -type f -name '*.md' | sort)
    fi

    # disclaimers come from the shared library
    grep -q 'shared/disclaimers.md' "$skill_file" || errs+=("SKILL.md must point to shared/disclaimers.md for its disclaimer")

    # banned permission-style / promise wording
    hits=$(grep -rEn "$BANNED" "$skill_dir" --include='*.md' 2>/dev/null | grep -v 'BANNED-EXAMPLE' | head -3)
    [[ -n "$hits" ]] && errs+=("Permission-style or promise wording found (see shared/disclaimers.md):"$'\n'"      $hits")

    # evals
    ev="$skill_dir/evals/evals.json"
    if [[ ! -f "$ev" ]]; then errs+=("Missing evals/evals.json")
    elif [[ -n "$PY" ]]; then
      evmsg=$("$PY" - "$ev" "$skill_name" <<'PYEOF'
import json, sys
path, name = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception as e:
    print("evals.json is not valid JSON: %s" % e); sys.exit()
out = []
if d.get("skill_name") != name:
    out.append("evals.json skill_name=%r, expected %r" % (d.get("skill_name"), name))
evs = d.get("evals") or []
if len(evs) < 4:
    out.append("evals.json has %d cases (need >=3 scenarios + 1 injection)" % len(evs))
if not any(e.get("type") == "injection" for e in evs):
    out.append("evals.json has no case with \"type\": \"injection\"")
for e in evs:
    if not e.get("prompt") or not e.get("assertions"):
        out.append("eval id=%s needs prompt and assertions" % e.get("id")); break
print("; ".join(out))
PYEOF
)
      [[ -n "$evmsg" ]] && errs+=("$evmsg")
    fi

    # report
    if [[ ${#errs[@]} -gt 0 ]]; then
      echo -e "${RED}❌ $skill_dir${NC}"
      for e in "${errs[@]}"; do echo -e "   ${RED}Error:${NC} $e"; done
      for w in "${warns[@]}"; do echo -e "   ${YELLOW}Warning:${NC} $w"; done
      ((ISSUES++))
    elif [[ ${#warns[@]} -gt 0 ]]; then
      echo -e "${YELLOW}⚠️  $skill_dir${NC}"
      for w in "${warns[@]}"; do echo -e "   ${YELLOW}Warning:${NC} $w"; done
      ((WARNINGS++))
    else
      echo -e "${GREEN}✓ $skill_dir${NC} (v$skill_ver, $lc lines)"
      ((PASSED++))
    fi
  done
done

echo "=========================================="
echo -e "Skills checked: $CHECKED  ${GREEN}passed: $PASSED${NC}  ${YELLOW}warnings: $WARNINGS${NC}  ${RED}errors: $ISSUES${NC}"
if [[ $ISSUES -eq 0 ]]; then echo -e "${GREEN}All checks passed ✓${NC}"; exit 0
else echo -e "${RED}Fix the errors above before committing.${NC}"; exit 1; fi
