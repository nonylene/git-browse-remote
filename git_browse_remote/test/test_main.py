import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import pygit2

from git_browse_remote import main


class TestWithRepo(unittest.TestCase):

    remote_origin_url = "https://github.com/nonylene/git-browse-remote"

    remote_sub = "sub"
    remote_sub_url = "https://github.com/octocat/hello-world"

    branch_name_without_upstream = "branch-wo-upstream"
    branch_name_with_upstream = "branch-with-upstream"

    @classmethod
    def setUpClass(cls):
        cls.cloned_dir = tempfile.TemporaryDirectory()
        repo = pygit2.clone_repository(cls.remote_origin_url, cls.cloned_dir.name)
        remote = repo.remotes.create(cls.remote_sub, cls.remote_sub_url)  # type: ignore
        remote.fetch()

        br = repo.create_branch(cls.branch_name_with_upstream, repo.head.peel())  # type: ignore
        br.upstream = repo.lookup_branch("sub/master", pygit2.enums.BranchType.REMOTE)
        repo.create_branch(cls.branch_name_without_upstream, repo.head.peel())  # type: ignore

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        shutil.copytree(self.cloned_dir.name, self.temp_dir.name, dirs_exist_ok=True)
        self.repo = pygit2.Repository(self.temp_dir.name)

    def test_get_repo(self):
        temp_dir_path = pathlib.Path(self.temp_dir.name).resolve()
        git_dir = temp_dir_path / ".git"

        os.chdir(temp_dir_path)
        self.assertEqual(main.get_repo().path, str(git_dir) + "/")

        # Subdir
        os.chdir(temp_dir_path / "git_browse_remote")
        self.assertEqual(main.get_repo().path, str(git_dir) + "/")

        # Parint dir
        os.chdir(temp_dir_path.parent)
        self.assertRaises(RuntimeError, main.get_repo)

    def test_get_remote_name(self):
        test_cases = [
            (
                ("main",),
                "origin",
            ),
            (
                (self.branch_name_with_upstream,),
                self.remote_sub,
            ),
            (
                (self.branch_name_without_upstream,),
                "origin",
            ),
        ]

        for (arg,), expected in test_cases:
            branch = self.repo.lookup_branch(arg)
            self.repo.checkout(branch.name)
            self.assertEqual(main.get_remote_name(self.repo), expected)

    def test_get_remote_name_detached(self):
        commit, _ = self.repo.resolve_refish("main~")
        self.repo.set_head(commit.id)
        self.assertTrue(self.repo.head_is_detached)  # test code confirmation
        self.assertEqual(main.get_remote_name(self.repo), "origin")

        # Returns the name of the first remote if we do not have "origin"
        self.repo.remotes.delete("origin")
        self.assertEqual(main.get_remote_name(self.repo), self.remote_sub)

    def test_get_remote_browse_url_base(self):
        test_cases = [
            (
                ("main", "origin"),
                self.remote_origin_url,
            ),
            (
                (self.branch_name_with_upstream, "sub"),
                self.remote_sub_url,
            ),
        ]

        for (arg, arg2), expected in test_cases:
            branch = self.repo.lookup_branch(arg)
            self.repo.checkout(branch.name)
            self.assertEqual(main.get_remote_browse_url_base(self.repo, arg2), expected)

    def test_has_branch_on_remote(self):
        test_cases = [
            (
                ("origin", "main"),
                True,
            ),
            (
                ("origin", "master"),
                False,
            ),
            (
                ("sub", "master"),
                True,
            ),
        ]

        for (arg, arg2), expected in test_cases:
            self.assertEqual(main.has_branch_on_remote(self.repo, arg, arg2), expected)

    def test_get_remote_default_branch(self):
        test_cases = [
            (
                ("origin",),
                "main",
            ),
            (
                ("sub",),
                "main",  # no origin HEAD fetched by just adding aremote
            ),
        ]

        for (arg,), expected in test_cases:
            self.assertEqual(main.get_remote_default_branch(self.repo, arg), expected)

    def test_get_ref_for_pathview(self):
        self.assertEqual(main.get_ref_for_pathview(self.repo, "origin"), "main")

        branch = self.repo.lookup_branch(self.branch_name_without_upstream)
        self.repo.checkout(branch.name)
        self.assertEqual(main.get_ref_for_pathview(self.repo, "origin"), "main")

        # detached HEAD
        commit, _ = self.repo.resolve_refish("main~")
        self.repo.set_head(commit.id)
        self.assertEqual(main.get_ref_for_pathview(self.repo, "origin"), str(commit.id))

    def test_tree_or_blob(self):
        test_cases = [
            (
                (None,),
                "tree",
            ),
            (
                ("git_browse_remote",),
                "tree",
            ),
            (
                ("git_browse_remote/",),
                "tree",
            ),
            (
                ("README.md",),
                "blob",
            ),
            (
                ("no-exist-path",),
                "blob",
            ),
        ]

        for (arg,), expected in test_cases:
            self.assertEqual(
                main.tree_or_blob(pathlib.Path(self.temp_dir.name), arg), expected
            )

    def test_get_subpath(self):
        test_cases = [
            (
                (None,),
                "",
            ),
            (
                (".",),
                "",
            ),
            (
                ("git_browse_remote",),
                "/git_browse_remote",
            ),
            (
                ("git_browse_remote/",),
                "/git_browse_remote",
            ),
            (
                ("git_browse_remote/../README.md",),
                "/README.md",
            ),
            (
                ("./README.md",),
                "/README.md",
            ),
            (
                ("sym_src",),
                "/sym_src",
            ),
            (
                ("../",),
                "",
            ),
        ]

        p = pathlib.Path(self.temp_dir.name)
        os.symlink(
            p / "sym_src",
            p / "sym_dst",
        )

        for (arg,), expected in test_cases:
            self.assertEqual(
                main.get_subpath(pathlib.Path(self.temp_dir.name), arg), expected
            )

    def test_open_pr(self):
        os.chdir(self.temp_dir.name)

        with patch("os.execlp") as p:
            main.open_pr()
            p.assert_called_once_with(
                "git",
                "git",
                "web--browse",
                "https://github.com/nonylene/git-browse-remote/pull/main",
            )

            commit, _ = self.repo.resolve_refish("main~")
            self.repo.set_head(commit.id)
            self.assertRaises(RuntimeError, main.open_pr)

    def test_open_path(self):
        os.chdir(self.temp_dir.name)

        with patch("os.execlp") as p:
            main.open_path("README.md")
            p.assert_called_once_with(
                "git",
                "git",
                "web--browse",
                "https://github.com/nonylene/git-browse-remote/blob/main/README.md",
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls.cloned_dir.cleanup()


class TestWithoutRepo(unittest.TestCase):

    def test_get_browse_url_base(self):
        test_cases = [
            (
                ("https://github.com/nonylene/git-browse-remote",),
                "https://github.com/nonylene/git-browse-remote",
            ),
            (
                ("https://github.com/nonylene/git-browse-remote.git",),
                "https://github.com/nonylene/git-browse-remote",
            ),
            (
                ("https://github.com/nonylene/git-browse-remote/",),
                "https://github.com/nonylene/git-browse-remote",
            ),
            (
                ("ssh://git@github.com/nonylene/git-browse-remote",),
                "https://github.com/nonylene/git-browse-remote",
            ),
            (
                ("ssh://git@github.com/nonylene/git-browse-remote.git",),
                "https://github.com/nonylene/git-browse-remote",
            ),
            (
                ("git@github.com:nonylene/git-browse-remote.git",),
                "https://github.com/nonylene/git-browse-remote",
            ),
            (
                ("git@github.com:nonylene/git-browse-remote",),
                "https://github.com/nonylene/git-browse-remote",
            ),
        ]

        for (arg,), expected in test_cases:
            self.assertEqual(main.get_browse_url_base(arg), expected)

    def test_get_browse_url_exception(self):
        test_cases = [
            (("http://github.com/nonylene/git-browse-remote",),),
            (("git@github.com:~foo/nonylene/git-browse-remote",),),
            (("invalid-url",),),
        ]

        for ((arg,),) in test_cases:
            self.assertRaises(RuntimeError, main.get_browse_url_base, arg)

    def test_get_path_url(self):
        test_cases = [
            (
                (
                    "https://github.com/nonylene/git-browse-remote",
                    "tree",
                    "main",
                    "/README.md",
                ),
                "https://github.com/nonylene/git-browse-remote/tree/main/README.md",
            ),
        ]

        for (arg, arg2, arg3, arg4), expected in test_cases:
            self.assertEqual(main.get_path_url(arg, arg2, arg3, arg4), expected)

    def test_get_pr_url(self):
        test_cases = [
            (
                ("https://github.com/nonylene/git-browse-remote", "main"),
                "https://github.com/nonylene/git-browse-remote/pull/main",
            ),
        ]

        for (arg, arg2), expected in test_cases:
            self.assertEqual(main.get_pr_url(arg, arg2), expected)

    def test_exec_git_browse(self):
        with patch("os.execlp") as p:
            main.exec_git_web_browse("https://github.com/nonylene/git-browse-remote")
            p.assert_called_once_with(
                "git",
                "git",
                "web--browse",
                "https://github.com/nonylene/git-browse-remote",
            )
