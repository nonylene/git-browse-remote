import pathlib
import re
from .logger import logger
import os
from typing import NoReturn, Optional
from urllib.parse import urlparse
import pygit2


def get_repo() -> pygit2.Repository:
    repo_path = pygit2.discover_repository(os.getcwd())
    if repo_path is None:
        raise RuntimeError("No repository found")

    return pygit2.Repository(os.getcwd())


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


# https://git-scm.com/docs/git-fetch#URLS
SSH_URL_PATTERN = re.compile(r"^([\w\-]+)@(?P<host_name>[\w\-\.]+):(?P<path>[\w\-/]+)$")


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
        case "":
            # it may be the url like git@github.com:nonylene/git-browse-remote
            if m := SSH_URL_PATTERN.match(url):
                return f"https://{m['host_name']}/{m['path']}"

            raise RuntimeError(f"Unknown remote url: {url}")
        case _:
            raise RuntimeError(f"Unknown scheme: {parsed.scheme}")


def get_remote_browse_url_base(repo: pygit2.Repository, remote_name: str) -> str:
    remote = next(x for x in repo.remotes if x.name == remote_name)
    # Push URL is not used for building the target url (Fork source repo is preferred on most cases)
    return get_browse_url_base(remote.url)  # type: ignore


def has_branch_on_remote(
    repo: pygit2.Repository, remote_name: str, branch_name: str
) -> bool:
    return (
        repo.lookup_branch(
            f"{remote_name}/{branch_name}", pygit2.enums.BranchType.REMOTE
        )
        is not None
    )


def get_remote_default_branch(repo: pygit2.Repository, remote_name: str) -> str:
    try:
        origin_head_ref = repo.lookup_reference(
            f"refs/remotes/{remote_name}/HEAD"
        ).target
        # It should be like "refs/remotes/origin/main"
        prefix = f"refs/remotes/{remote_name}/"
        if type(origin_head_ref) != str or not origin_head_ref.startswith(prefix):
            raise RuntimeError(f"Invalid remote HEAD reference: {origin_head_ref}")

        return origin_head_ref[len(prefix) :]

    except KeyError:
        logger.warning(
            f"The remote default branch information is not found for the remote '{remote_name}' and defaulted to 'main'.\n"
            "You can set the remote HEAD by running the following command:\n"
            f"$ git remote set-head {remote_name} -a"
        )
        return "main"


def get_ref_for_pathview(repo: pygit2.Repository, remote_name: str) -> str:
    head_name = repo.head.shorthand
    if repo.head_is_detached:
        # repo.head is 'HEAD'
        return str(repo.head.target)

    if has_branch_on_remote(repo, remote_name, head_name):
        return head_name

    logger.info(
        f"The current branch '{head_name}' is not found on the remote '{remote_name}'. The remote default branch will be opened."
    )
    return get_remote_default_branch(repo, remote_name)


def tree_or_blob(repo_root: pathlib.Path, path: Optional[str]) -> str:
    if not path:
        # toplevel
        return "tree"

    target_path = repo_root / path
    if not target_path.exists():
        # Blob should work on dirs!
        return "blob"

    if target_path.is_dir():
        return "tree"

    return "blob"


# Returned path may have "/" prefix
def get_subpath(repo_root: pathlib.Path, path: Optional[str]) -> str:
    if not path:
        # toplevel
        return ""

    if str(repo_root) != os.path.commonpath(
        [os.path.abspath(repo_root / path), repo_root]
    ):
        # Outside path
        logger.warning(
            f"Specified path {path} resides outside of the repository. The repository root will be opened."
        )
        return ""

    # Path.resolve does not fit here since that follows symlinks.
    # Path.absolute also does not fit here since that does not normalize `..`s.
    return os.path.abspath(repo_root / path)[len(os.path.abspath(repo_root)) :]


def get_pr_url(url_base: str, branch: str) -> str:
    return url_base + f"/pull/{branch}"


def get_path_url(url_base: str, tree_or_blob: str, ref: str, path: str):
    return f"{url_base}/{tree_or_blob}/{ref}{path}"


def exec_git_web_browse(url: str) -> NoReturn:
    os.execlp("git", "git", "web--browse", url)


def open_pr() -> NoReturn:
    repo = get_repo()
    if repo.head_is_detached:
        raise RuntimeError("Failed to detect the branch name: HEAD is detatched")

    remote_name = get_remote_name(repo)
    url_base = get_remote_browse_url_base(repo, remote_name)
    head_name = repo.head.shorthand
    pr_url = get_pr_url(url_base, head_name)
    logger.info(f"Pull request URL: {pr_url}")
    exec_git_web_browse(pr_url)


def open_path(path: Optional[str]) -> NoReturn:
    repo = get_repo()
    # repo.path points '.git' directory
    repo_root = pathlib.Path(repo.path).parent
    remote_name = get_remote_name(repo)
    url_base = get_remote_browse_url_base(repo, remote_name)
    ref = get_ref_for_pathview(repo, remote_name)
    t_b = tree_or_blob(repo_root, path)
    path_normalized = get_subpath(repo_root, path)
    path_url = get_path_url(url_base, t_b, ref, path_normalized)
    logger.info(f"Path URL: {path_url}")
    exec_git_web_browse(path_url)
