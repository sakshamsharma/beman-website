#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

set -euo pipefail

BRANCH="${1:-gh-pages}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/build"
WORKTREE_DIR="${REPO_ROOT}/.gh-pages-worktree"
SOURCE_SHA="$(git -C "${REPO_ROOT}" rev-parse --short HEAD)"

if [[ ! -d "${BUILD_DIR}" ]]; then
  echo "Build output directory not found: ${BUILD_DIR}" >&2
  exit 1
fi

cleanup() {
  if git -C "${REPO_ROOT}" worktree list | grep -q "${WORKTREE_DIR}"; then
    git -C "${REPO_ROOT}" worktree remove --force "${WORKTREE_DIR}" || true
  fi
  rm -rf "${WORKTREE_DIR}"
}
trap cleanup EXIT

rm -rf "${WORKTREE_DIR}"
git -C "${REPO_ROOT}" fetch origin "${BRANCH}" || true

if git -C "${REPO_ROOT}" show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
  git -C "${REPO_ROOT}" worktree add --force "${WORKTREE_DIR}" "origin/${BRANCH}"
  git -C "${WORKTREE_DIR}" checkout -B "${BRANCH}" "origin/${BRANCH}"
else
  git -C "${REPO_ROOT}" worktree add --detach "${WORKTREE_DIR}"
  git -C "${WORKTREE_DIR}" checkout --orphan "${BRANCH}"
  git -C "${WORKTREE_DIR}" rm -rf . >/dev/null 2>&1 || true
fi

rsync -a --delete --exclude='.git' "${BUILD_DIR}/" "${WORKTREE_DIR}/"
touch "${WORKTREE_DIR}/.nojekyll"

git -C "${WORKTREE_DIR}" add -A

if git -C "${WORKTREE_DIR}" diff --cached --quiet; then
  echo "No gh-pages changes to publish."
  exit 0
fi

git -C "${WORKTREE_DIR}" commit -m "Deploy website from ${SOURCE_SHA}"
git -C "${WORKTREE_DIR}" push origin "${BRANCH}"
