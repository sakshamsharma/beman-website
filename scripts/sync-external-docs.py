#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import argparse
import shutil
import subprocess
from pathlib import Path


REPO_DOCS = [
    {
        "name": "optional",
        "build_cmd": ["make", "docs"],
        "docs_output_rel": Path("docs") / "html",
        "static_target_rel": Path("static") / "optional",
    },
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repos-root",
        help="path to folder containing external repos (default: parent of website repo)",
        type=str,
        default="",
    )
    return parser.parse_args()


def run_build(repo_path: Path, build_cmd: list[str]) -> bool:
    print(f"Building docs in {repo_path} with: {' '.join(build_cmd)}")
    try:
        subprocess.run(build_cmd, cwd=repo_path, check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"Build failed in {repo_path} (exit {exc.returncode})")
        return False


def copy_docs(source: Path, target: Path) -> bool:
    if not source.exists():
        print(f"Missing docs output: {source}")
        return False
    print(f"Copying {source} to {target}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return True


def main():
    args = parse_args()
    website_repo_path = Path(__file__).parent.parent
    repos_root = Path(args.repos_root) if args.repos_root else website_repo_path.parent

    failures = 0
    for repo in REPO_DOCS:
        repo_path = repos_root / repo["name"]
        if not repo_path.exists():
            print(f"Skipping missing repo: {repo_path}")
            continue

        if not run_build(repo_path, repo["build_cmd"]):
            failures += 1
            continue

        source = repo_path / repo["docs_output_rel"]
        target = website_repo_path / repo["static_target_rel"]
        if not copy_docs(source, target):
            failures += 1

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
