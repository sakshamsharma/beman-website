#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import argparse
import shutil
import subprocess
from pathlib import Path


REPO_DOCS = [
    {
        "name": "optional",
        "repo_url": "https://github.com/bemanproject/optional",
        "repo_branch": "main",
        "build_cmd": ["make", "docs"],
        "docs_output_rel": Path("docs") / "html",
        "static_target_rel": Path("static") / "optional",
        "markdown_docs": [
            {
                "source_rel": Path("docs") / "overview.md",
                "target_rel": Path("docs") / "libraries" / "optional" / "overview.md",
                "sidebar_position": 2,
                "sidebar_label": "Overview",
            },
            {
                "source_rel": Path("docs") / "debug-ci.md",
                "target_rel": Path("docs") / "libraries" / "optional" / "debug-ci.md",
                "sidebar_position": 3,
                "sidebar_label": "Debugging CI",
            },
            {
                "target_rel": Path("docs") / "libraries" / "optional" / "index.md",
                "sidebar_position": 1,
                "sidebar_label": "beman.optional",
                "generated": "index",
            },
        ],
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
    parser.add_argument(
        "--skip-builds",
        help="skip running build commands and only sync existing docs outputs",
        action="store_true",
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


def copy_markdown_with_frontmatter(
    source: Path,
    target: Path,
    sidebar_position: int,
    sidebar_label: str,
    repo_url: str = "",
    repo_branch: str = "main",
    intro_block: str = "",
) -> bool:
    if source and not source.exists():
        print(f"Missing markdown source: {source}")
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    content = source.read_text() if source else ""
    content = rewrite_repo_links(content, repo_url, repo_branch)
    content = sanitize_mdx_text(content)
    if intro_block:
        content = intro_block + "\n\n" + content
        content = content.replace("\n# Overview", "\n## Overview", 1)

    if not content.lstrip().startswith("---"):
        frontmatter = (
            "---\n"
            f"sidebar_position: {sidebar_position}\n"
            f"sidebar_label: {sidebar_label}\n"
            "---\n\n"
        )
        content = frontmatter + content

    target.write_text(content)
    print(f"Copied markdown {source} to {target}")
    return True


def rewrite_repo_links(content: str, repo_url: str, repo_branch: str) -> str:
    if not repo_url:
        return content

    replacements = {
        "](.github/": f"]({repo_url}/tree/{repo_branch}/.github/",
        "](./.github/": f"]({repo_url}/tree/{repo_branch}/.github/",
        "](../.github/": f"]({repo_url}/tree/{repo_branch}/.github/",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    return content


def build_index_block(repo_name: str, repo_url: str, static_target_rel: Path) -> str:
    api_path = f"/{static_target_rel.name}/index.html" if static_target_rel else ""
    parts = [
        f"# {repo_name}",
        "",
        "Links:",
    ]
    if repo_url:
        parts.append(f"- [Repository]({repo_url})")
    if api_path:
        parts.append(
            f"- <a href=\"{api_path}\" data-noBrokenLinkCheck>API reference</a>"
        )
    parts.append("- [Overview](/docs/libraries/optional/overview)")
    parts.append("- [Debugging CI](/docs/libraries/optional/debug-ci)")
    return "\n".join(parts)


def sanitize_mdx_text(content: str) -> str:
    """
    Escape angle brackets in non-code text to avoid MDX JSX parsing errors.
    """
    content = content.replace("`struct ref {int * p;``", "`struct ref {int * p;}`")
    lines = content.splitlines(keepends=True)
    in_fence = False
    fence_marker = ""
    sanitized = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            sanitized.append(line)
            continue

        if in_fence:
            sanitized.append(line)
            continue

        parts = line.split("`")
        for i in range(0, len(parts), 2):
            parts[i] = (
                parts[i]
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("{", "&#123;")
                .replace("}", "&#125;")
            )
        sanitized.append("`".join(parts))

    return "".join(sanitized)


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

        build_ok = True
        if not args.skip_builds:
            build_ok = run_build(repo_path, repo["build_cmd"])
            if not build_ok:
                failures += 1

        if build_ok:
            source = repo_path / repo["docs_output_rel"]
            target = website_repo_path / repo["static_target_rel"]
            if not copy_docs(source, target):
                failures += 1

        for doc in repo.get("markdown_docs", []):
            md_source = repo_path / doc["source_rel"] if "source_rel" in doc else None
            md_target = website_repo_path / doc["target_rel"]
            intro_block = ""
            if doc.get("generated") == "index":
                intro_block = build_index_block(
                    repo.get("name", ""),
                    repo.get("repo_url", ""),
                    repo.get("static_target_rel", Path()),
                )
            if not copy_markdown_with_frontmatter(
                md_source,
                md_target,
                doc["sidebar_position"],
                doc["sidebar_label"],
                repo_url=repo.get("repo_url", ""),
                repo_branch=repo.get("repo_branch", "main"),
                intro_block=intro_block,
            ):
                failures += 1

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
