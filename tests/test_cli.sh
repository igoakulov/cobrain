#!/bin/bash

cd "$(dirname "$0")/.."
export PATH="$(pwd)/.venv/bin:$PATH"

FAILED=()

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED+=("$1"); }

rm -rf test-vault
mkdir -p test-vault
cd test-vault

(hippo version > /dev/null 2>&1) && (hippo init --vault . > /dev/null 2>&1) && pass smoke || fail smoke

mkdir -p topics

cat > topics/a.md << 'EOF'
---
id: a
title: Topic A
aliases: alias-a,topic-a
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
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
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
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
progress: started
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: nlp
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
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
parent: nonexistent-parent
related: []
sources:
  - https://orphan.example.com
---
# Orphan Topic

Content for orphan.
EOF

(hippo sync > /dev/null 2>&1) && pass "sync with topics" || fail "sync with topics"

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
progress: new
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
hippo sync > /dev/null 2>&1

# Test warning hint appears without --warnings flag
(hippo sync 2>&1 | grep -q "(add --warnings to see)") && pass "sync warning hint" || fail "sync warning hint"
(hippo graph --sync 2>&1 | grep -q "(add --warnings to see)") && pass "graph warning hint" || fail "graph warning hint"

# Test detailed warnings with --warnings flag
(hippo sync --warnings 2>&1 | grep -q "^WARNINGS$") && pass "sync --warnings format" || fail "sync --warnings format"
(hippo sync --warnings 2>&1 | grep -q "no-sources") && pass "sync no_sources warning" || fail "sync no_sources warning"
(hippo sync --warnings 2>&1 | grep -q "no-parent") && pass "sync no_parent warning" || fail "sync no_parent warning"
(hippo sync --warnings 2>&1 | grep -q "nonexistent-parent") && pass "sync orphan_parent warning" || fail "sync orphan_parent warning"
(hippo sync --warnings 2>&1 | grep -q "Empty body") && pass "sync empty_body warning" || fail "sync empty_body warning"

# Test --warnings (only works with sync or --sync)
(hippo topics > /dev/null 2>&1) && pass "topics summary" || fail "topics summary"
(hippo topics --ids a,b,c > /dev/null 2>&1) && pass "topics read" || fail "topics read"
(hippo topics --ids a --sync > /dev/null 2>&1) && pass "topics read sync" || fail "topics read sync"
(hippo topics --ids nonexistent 2>&1 | grep -q "Topic not found") && pass "topics read error" || fail "topics read error"
(hippo topics --ids a --set progress=completed > /dev/null 2>&1) && pass "topics set single" || fail "topics set single"
(hippo topics --ids b,c --set cluster=nlp progress=started > /dev/null 2>&1) && pass "topics set multiple" || fail "topics set multiple"
(hippo topics --ids a --set progress=new cluster=ml aliases="[alias-a-new]" --sync > /dev/null 2>&1) && pass "topics set sync" || fail "topics set sync"

(hippo graph > /dev/null 2>&1) && pass "graph full" || fail "graph full"
(hippo graph --sync > /dev/null 2>&1) && pass "graph sync" || fail "graph sync"
(hippo graph --from a > /dev/null 2>&1) && pass "graph from" || fail "graph from"
(hippo graph --from a --depth 1 > /dev/null 2>&1) && pass "graph from depth" || fail "graph from depth"
(hippo graph --from b --to c > /dev/null 2>&1) && pass "graph path" || fail "graph path"
(hippo graph --minimal > /dev/null 2>&1) && pass "graph minimal" || fail "graph minimal"
(hippo graph --full > /dev/null 2>&1) && pass "graph full fields" || fail "graph full fields"
(hippo graph --full+ > /dev/null 2>&1) && pass "graph full+" || fail "graph full+"
(hippo graph --full+ --block > /dev/null 2>&1) && pass "graph full+ block" || fail "graph full+ block"
(hippo graph --from b --depth 1 --full+ > /dev/null 2>&1) && pass "graph traversal full+" || fail "graph traversal full+"
(hippo graph --from b --to c --block > /dev/null 2>&1) && pass "graph path block" || fail "graph path block"
(hippo graph --from a --depth 1 --block > /dev/null 2>&1) && pass "graph neighborhood block" || fail "graph neighborhood block"

(hippo backup > /dev/null 2>&1) && pass backup || fail backup

(hippo topics --ids a,b,c --set cluster=modified-cluster > /dev/null 2>&1) && pass "modify topics" || fail "modify topics"

(python3 -c "import yaml; d=yaml.safe_load(open('.hippo/clusters.yaml'))" > /dev/null 2>&1) && pass "clusters valid" || fail "clusters valid"

(hippo topics --ids b --set aliases="[new-alias]" related="[]" sources="[]" > /dev/null 2>&1) && pass "topics set multi-target" || fail "topics set multi-target"
(hippo topics --ids b > /dev/null 2>&1) && pass "verify updated" || fail "verify updated"

(hippo topics --ids a --set cluster=ml > /dev/null 2>&1) && pass "reset cluster" || fail "reset cluster"

(hippo sync > /dev/null 2>&1) && pass "sync" || fail "sync"

# Sources warning tests
mkdir -p sources
echo "unused source content" > sources/unused.md
(hippo sources 2>&1 | grep -q "warnings:") && pass "sources warning hint" || fail "sources warning hint"
(hippo sources --warnings 2>&1 | grep -q "^UNUSED SOURCES") && pass "sources --warnings format" || fail "sources --warnings format"
(hippo sources --warnings 2>&1 | grep -q "unused") && pass "sources unused warning" || fail "sources unused warning"

echo "---"
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "cli: all passed"
else
    echo "cli: ${#FAILED[@]} failed: ${FAILED[*]}"
fi

[ ${#FAILED[@]} -eq 0 ]