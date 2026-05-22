#!/bin/bash

cd "$(dirname "$0")/.."
export PATH="$(pwd)/.venv/bin:$PATH"
export PYTHONPATH="$(pwd)/src"
COBRAIN="$(pwd)/.venv/bin/cobrain"

FAILED=()

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED+=("$1"); }

rm -rf test-vault
mkdir -p test-vault
cd test-vault

$COBRAIN init > /dev/null 2>&1 && pass smoke || fail smoke

cat > topics/a.md << 'EOF'
---
id: a
title: Topic A
aliases: alias-a,topic-a
created_at: 2026-03-19
updated_at: 2026-03-19
category: ml
parent:
related: []
sources:
  - https://example.com/a
---
# Topic A

Content for A.
EOF

cat > topics/b.md << 'EOF'
---
id: b
title: Topic B
aliases: alias-b
created_at: 2026-03-19
updated_at: 2026-03-19
category: ml
parent: a
related:
  - c
sources:
  - https://example.com/b
---
# Topic B

Content for B.
EOF

cat > topics/c.md << 'EOF'
---
id: c
title: Topic C
aliases:
created_at: 2026-03-19
updated_at: 2026-03-19
category: nlp
parent: a
related: []
sources:
---
# Topic C

Content for C.
EOF

cat > topics/orphan.md << 'EOF'
---
id: orphan
title: Orphan Topic
aliases:
created_at: 2026-03-19
updated_at: 2026-03-19
category: ml
parent: nonexistent-parent
related: []
sources:
  - https://orphan.example.com
---
# Orphan Topic

Content for orphan.
EOF

($COBRAIN sync > /dev/null 2>&1) && pass "sync with topics" || fail "sync with topics"

# Warnings test data - add topics with various warning conditions

# Topic with no sources
cat > topics/no-sources.md << 'EOF'
---
id: no-sources
title: No Sources
parent: a
sources: []
---
# No Sources
EOF

# Topic with no parent
cat > topics/no-parent.md << 'EOF'
---
id: no-parent
title: No Parent
parent:
sources: []
---
# No Parent
Content here.
EOF

# Topic with empty body
cat > topics/empty-body.md << 'EOF'
---
id: empty-body
title: Empty Body
parent: a
sources:
---
EOF

# Re-sync to pick up new topics
$COBRAIN sync > /dev/null 2>&1

# Test warning hint appears without --warnings flag
($COBRAIN sync 2>&1 | grep -q "warnings.*run") && pass "sync warning hint" || fail "sync warning hint"

# Test detailed warnings with --warnings flag
($COBRAIN sync --warnings 2>&1 | grep -q "^WARNINGS$") && pass "sync --warnings format" || fail "sync --warnings format"
($COBRAIN sync --warnings 2>&1 | grep -q "no-sources") && pass "sync no_sources warning" || fail "sync no_sources warning"
($COBRAIN sync --warnings 2>&1 | grep -q "no-parent") && pass "sync no_parent warning" || fail "sync no_parent warning"
($COBRAIN sync --warnings 2>&1 | grep -q "nonexistent-parent") && pass "sync orphan_parent warning" || fail "sync orphan_parent warning"
($COBRAIN sync --warnings 2>&1 | grep -q "Empty body") && pass "sync empty_body warning" || fail "sync empty_body warning"

# Test vault (list topics)
($COBRAIN vault > /dev/null 2>&1) && pass "vault summary" || fail "vault summary"
($COBRAIN vault --ids a,b,c > /dev/null 2>&1) && pass "vault read" || fail "vault read"
($COBRAIN vault --ids nonexistent 2>&1 | grep -q "Topic not found") && pass "vault read error" || fail "vault read error"

($COBRAIN vault --ids a --set category=ml > /dev/null 2>&1) && pass "vault set single" || fail "vault set single"
($COBRAIN vault --ids b,c --set category=nlp > /dev/null 2>&1) && pass "vault set multiple" || fail "vault set multiple"
($COBRAIN vault --ids a --set category=ml aliases="[alias-a-new]" > /dev/null 2>&1) && pass "vault set sync" || fail "vault set sync"

($COBRAIN vault > /dev/null 2>&1) && pass "vault full" || fail "vault full"
($COBRAIN vault --from a > /dev/null 2>&1) && pass "vault from" || fail "vault from"
($COBRAIN vault --from a --depth 1 > /dev/null 2>&1) && pass "vault from depth" || fail "vault from depth"
($COBRAIN vault --from b --to c > /dev/null 2>&1) && pass "vault path" || fail "vault path"
($COBRAIN vault --minimal > /dev/null 2>&1) && pass "vault minimal" || fail "vault minimal"
($COBRAIN vault --full > /dev/null 2>&1) && pass "vault full fields" || fail "vault full fields"
($COBRAIN vault --full+ > /dev/null 2>&1) && pass "vault full+" || fail "vault full+"
($COBRAIN vault --full+ --block > /dev/null 2>&1) && pass "vault full+ block" || fail "vault full+ block"
($COBRAIN vault --from b --depth 1 --full+ > /dev/null 2>&1) && pass "vault traversal full+" || fail "vault traversal full+"
($COBRAIN vault --from b --to c --block > /dev/null 2>&1) && pass "vault path block" || fail "vault path block"
($COBRAIN vault --from a --depth 1 --block > /dev/null 2>&1) && pass "vault neighborhood block" || fail "vault neighborhood block"

($COBRAIN backup > /dev/null 2>&1) && pass backup || fail backup

($COBRAIN vault --ids a,b,c --set category=modified-category > /dev/null 2>&1) && pass "modify topics" || fail "modify topics"

($COBRAIN show 2>&1 | grep -q "Vault page ready") && pass "show" || fail "show"

($COBRAIN vault --ids b --set aliases="[new-alias]" related="[]" sources="[]" > /dev/null 2>&1) && pass "vault set multi-target" || fail "vault set multi-target"
($COBRAIN vault --ids b > /dev/null 2>&1) && pass "verify updated" || fail "verify updated"

($COBRAIN vault --ids a --set category=ml > /dev/null 2>&1) && pass "reset category" || fail "reset category"

($COBRAIN sync > /dev/null 2>&1) && pass "sync" || fail "sync"

# Sources warning tests
mkdir -p sources
echo "unused source content" > sources/unused.md
($COBRAIN sources 2>&1 | grep -q "warnings:") && pass "sources warning hint" || fail "sources warning hint"
($COBRAIN sources --warnings 2>&1 | grep -q "^UNUSED SOURCES") && pass "sources --warnings format" || fail "sources --warnings format"
($COBRAIN sources --warnings 2>&1 | grep -q "unused") && pass "sources unused warning" || fail "sources unused warning"

echo "---"
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "cli: all passed"
else
    echo "cli: ${#FAILED[@]} failed: ${FAILED[*]}"
fi

[ ${#FAILED[@]} -eq 0 ]
