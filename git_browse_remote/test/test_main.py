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
        _, ref = self.repo.resolve_refish("main~")
        self.repo.checkout(ref)
        self.assertEqual(main.get_remote_name(self.repo), "origin")

        # Returns the name of the first remote if we do not have "origin"
        self.repo.remotes.delete("origin")
        self.repo.checkout(ref)
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
