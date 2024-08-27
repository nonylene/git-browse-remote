# git-browse-remote

Browse the GitHub repository with the browser from CLI

This module is inpired by [git-browse-remote](https://github.com/motemen/git-browse-remote) gem but has limited features, which I use on daily, than the gem.

## Supported environments

- Python >= 3.11
- GitHub (and repositories that have compatible URL structure with GitHub, e.g. GitHub enterprise)

This tool executes `$ git web--remote` to open a URL. To change the browser to be used, see [git-web--browse documentation](https://git-scm.com/docs/git-web--browse).

## Usage

### Install

```
$ pipx install git-browse-remote
```

PyPI: https://pypi.org/project/git-browse-remote/


### Open the PR url for the current branch

```
$ git browse-remote -p # e.g. https://github.com/nonylene/git-browse-remote/pull/{current_branch}
```


### Open the blob/tree url for the path of the current branch

```
$ git browse-remote {path} # e.g. https://github.com/nonylene/git-browse-remote/tree/{current_branch}/{path}
```


## Development

```
# Install dependencies
$ poetry install
# Run
$ poetry run git-browse-remote --help
# Test
$ poetry run python3 -m unittest
# Coverage
$ poetry run coverage run -m unittest
$ poetry run coverage report -m
```

### Release

- Bump up version in pyproject.toml
- `git tag v{version}`
