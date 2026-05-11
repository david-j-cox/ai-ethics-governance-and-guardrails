#!/usr/bin/env bash
# One-time per-clone setup: register the state.json merge driver locally.
#
# .gitattributes already declares `agent/state.json merge=statejson`, but git
# requires the driver itself to be registered in the local git config (custom
# drivers are intentionally not loaded from the repo for security reasons).
# Run this once after cloning, or after `git clean -dx` blows away .git/config.
set -euo pipefail

git config merge.statejson.driver "python agent/repair_state.py --merge-driver %O %A %B"
echo "Registered merge.statejson.driver in $(git rev-parse --show-toplevel)/.git/config"
