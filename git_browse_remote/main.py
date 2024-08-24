from email.policy import default
from .logger import logger
import logging
import os
from typing import NoReturn, Optional
from urllib.parse import ParseResult, urljoin, urlparse, urlunparse
import pygit2


def get_remote_name(repo: pygit2.Repository) -> str:
    if not repo.head_is_detached:
        # head is the branch
        branch = repo.lookup_branch(repo.head.shorthand)
        if branch.upstream is not None:
            return branch.upstream.remote_name

    # get the default branch
    remote_names = list(repo.remotes.names())
    if "origin" in remote_names:
        return "origin"
    else:
        # Don't care about local-only repository!
        return remote_names[0]  # type: ignore


def get_browse_url_base(url: str) -> str:
    # Remove trailing slash
    if url.endswith("/"):
        url = url[:-1]

    # GitHub cannot create repository suffixed with `.git`
    if url.endswith(".git"):
        url = url[:-4]

    parsed = urlparse(url)
    match parsed.scheme:
        case "https":
            return url
        case "ssh":
            # Remove username / password from netloc
            new_host: str = parsed.hostname  # type: ignore
            new_host += f":{parsed.port}" if parsed.port is not None else ""
            return parsed._replace(scheme="https", netloc=new_host).geturl()
        case _:
            raise RuntimeError(f"Unknown scheme: {parsed.scheme}")


def get_remote_browse_url_base(repo: pygit2.Repository) -> str:
    remote_name = get_remote_name(repo)
    remote = next(x for x in repo.remotes if x.name == remote_name)
    # Push URL is not used for building the target url (Fork source repo is preferred on most cases)
    return get_browse_url_base(remote.url)  # type: ignore


def get_pr_url(url_base: str, branch: str) -> str:
    return url_base + f"/pull/{branch}"


def exec_git_browse(url: str) -> NoReturn:
    os.execlp("git", "git", "web--browse", url)


def open_pr() -> NoReturn:
    repo = pygit2.Repository(os.getcwd())
    if repo.head_is_detached:
        raise RuntimeError("Failed to detect the branch name: HEAD is detatched")

    head_name = repo.head.shorthand
    url_base = get_remote_browse_url_base(repo)
    pr_url = get_pr_url(url_base, head_name)
    logger.info(f"Pull request URL: {pr_url}")
    exec_git_browse(pr_url)


def open_path(path: Optional[str]):
    repo = pygit2.Repository(os.getcwd())
    head_name = repo.head.shorthand
    print(head_name)
