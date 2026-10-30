#!/bin/bash
# End-to-end check of a deployment, from outside, against its public addresses.
#
#   scripts/smoke.sh <web base> <api base> [<mcp base>]
#   scripts/smoke.sh https://new.janoubona.net https://api-new.janoubona.net https://mcp-new.janoubona.net
#
# Optional, read from the environment (never pass them on the command line):
#   SMOKE_EXPECT_STATS    "96/282/37" -- businesses/products/talents the public
#                         stats must show, e.g. the old deployment's numbers
#                         after a data copy. Without it the stats only have to load.
#   SMOKE_ADMIN_EMAIL     an administrator's sign-in; without both, the admin
#   SMOKE_ADMIN_PASSWORD  and owner sections are skipped.
#   SMOKE_MCP_TOKEN       the mcp service's SOUTH_MCP_TOKEN; without it the MCP
#                         section only checks that a tokenless request is refused.
#
# It changes no data, with one exception to know about: the owner section opens
# a view-as session (POST /api/admin/users/{id}/view-as), which the API logs
# with the administrator's id. It reads through that session and writes nothing.
# Exits non-zero when any check fails.
set -u

WEB=${1:?web base URL}
API=${2:?api base URL}
MCP=${3:-}
pass=0
fail=0

ok() { echo "PASS  $1"; pass=$((pass + 1)); }
bad() { echo "FAIL  $1 -- $2"; fail=$((fail + 1)); }
skip() { echo "SKIP  $1"; }
code() { curl -s -m 30 -o /dev/null -w '%{http_code}' "$@"; }
check() {
  local name=$1 want=$2 got
  shift 2
  got=$(code "$@")
  if [ "$got" = "$want" ]; then ok "$name ($got)"; else bad "$name" "got $got, want $want"; fi
}

echo "== public"
check "home page" 200 "$WEB/"
stats=$(curl -s -m 30 "$WEB/api/businesses/stats")
got=$(echo "$stats" | jq -r '"\(.total_businesses)/\(.total_products)/\(.total_talents)"' 2>/dev/null)
if [ -n "${SMOKE_EXPECT_STATS:-}" ]; then
  [ "$got" = "$SMOKE_EXPECT_STATS" ] && ok "stats $got" || bad "stats" "got $got, want $SMOKE_EXPECT_STATS"
else
  [[ "$got" =~ ^[0-9]+/[0-9]+/[0-9]+$ ]] && ok "stats $got" || bad "stats" "$stats"
fi
slug=$(curl -s -m 30 "$API/api/businesses?page_size=1" | jq -r '.items[0].slug // empty')
check "business detail API" 200 "$API/api/businesses/$slug"
check "business page via web" 200 "$WEB/business/$slug"
tslug=$(curl -s -m 30 "$API/api/talent?page_size=1" | jq -r '.items[0].slug // empty')
check "talent detail API" 200 "$API/api/talent/$tslug"
img=$(curl -s -m 30 "$API/api/businesses/$slug" | grep -o '/media/[^"]*\.\(jpg\|jpeg\|png\|webp\)' | head -1)
if [ -n "$img" ]; then check "photo from storage" 200 "$WEB$img"; else bad "photo from storage" "no image on $slug"; fi
# PRIVATE_MEDIA_FOLDERS: refused by name, whether the file exists or not.
check "private: owner-verification" 404 "$WEB/media/owner-verification/x.jpg"
check "private: owner-cv" 404 "$WEB/media/owner-cv/x.pdf"
check "private: backups" 404 "$WEB/media/backups/db/x.dump"

echo "== admin"
if [ -n "${SMOKE_ADMIN_EMAIL:-}" ] && [ -n "${SMOKE_ADMIN_PASSWORD:-}" ]; then
  body=$(jq -n --arg i "$SMOKE_ADMIN_EMAIL" --arg p "$SMOKE_ADMIN_PASSWORD" '{identifier:$i,password:$p}')
  tok=$(curl -s -m 30 -H 'Content-Type: application/json' -d "$body" "$API/api/auth/login" | jq -r '.access_token // empty')
  [ -n "$tok" ] && ok "admin sign-in" || bad "admin sign-in" "no token"
  H="Authorization: Bearer $tok"
  check "admin stats" 200 -H "$H" "$API/api/admin/stats"
  pending=$(curl -s -m 30 -H "$H" "$API/api/admin/businesses?status=PENDING_REVIEW&page_size=50")
  n=$(echo "$pending" | jq -r '.total // (.items | length)' 2>/dev/null)
  [[ "$n" =~ ^[0-9]+$ ]] && ok "moderation queue ($n pending)" || bad "moderation queue" "$(echo "$pending" | head -c 200)"
  pslug=$(echo "$pending" | jq -r '.items[0].slug // empty' 2>/dev/null)
  if [ -n "$pslug" ]; then check "pending listing not public" 404 "$API/api/businesses/$pslug"; else skip "pending listing not public (queue empty)"; fi

  echo "== owner (view-as, read only)"
  owner=$(curl -s -m 30 -H "$H" "$API/api/admin/businesses?status=APPROVED&page_size=1" | jq -r '.items[0] | (.owner_id // .owner.id // empty)')
  if [ -n "$owner" ]; then
    otok=$(curl -s -m 30 -X POST -H "$H" "$API/api/admin/users/$owner/view-as" | jq -r '.access_token // empty')
    [ -n "$otok" ] && ok "owner session" || bad "owner session" "no token"
    check "owner /api/auth/me" 200 -H "Authorization: Bearer $otok" "$API/api/auth/me"
    nb=$(curl -s -m 30 -H "Authorization: Bearer $otok" "$API/api/my/businesses" | jq 'length' 2>/dev/null)
    [ "${nb:-0}" -ge 1 ] 2>/dev/null && ok "owner dashboard lists $nb business(es)" || bad "owner dashboard" "${nb:-no answer}"
  else
    bad "owner session" "no owner id in the admin payload"
  fi
else
  skip "admin and owner (SMOKE_ADMIN_EMAIL / SMOKE_ADMIN_PASSWORD unset)"
fi

echo "== mcp"
if [ -n "$MCP" ]; then
  check "mcp without token refused" 401 -X POST "$MCP/mcp"
  if [ -n "${SMOKE_MCP_TOKEN:-}" ]; then
    hdr=$(mktemp)
    mh=(-H "Authorization: Bearer $SMOKE_MCP_TOKEN" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
    init=$(curl -s -m 30 -D "$hdr" "${mh[@]}" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' "$MCP/mcp")
    sid=$(grep -i '^mcp-session-id:' "$hdr" | cut -d' ' -f2 | tr -d '\r')
    rm -f "$hdr"
    echo "$init" | grep -q '"serverInfo"' && ok "mcp initialize" || bad "mcp initialize" "$(echo "$init" | head -c 200)"
    [ -n "$sid" ] && mh+=(-H "mcp-session-id: $sid")
    curl -s -m 30 "${mh[@]}" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' "$MCP/mcp" >/dev/null
    # platform_stats answers only if the mcp service can sign in to the API.
    call=$(curl -s -m 60 "${mh[@]}" -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"platform_stats","arguments":{}}}' "$MCP/mcp")
    if echo "$call" | grep -q 'businesses' && ! echo "$call" | grep -q '"isError":true'; then
      ok "mcp platform_stats"
    else
      bad "mcp platform_stats" "$(echo "$call" | head -c 300)"
    fi
  else
    skip "mcp tools (SMOKE_MCP_TOKEN unset)"
  fi
else
  skip "mcp (no mcp base URL)"
fi

echo
echo "passed $pass, failed $fail"
[ "$fail" -eq 0 ]
