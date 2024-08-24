# git-browse-remote

Browse the GitHub repository with the browser from CLI

This module is inpired by [git-browse-remote](https://github.com/motemen/git-browse-remote) gem but has limited features, which I use on daily, than the gem.

## Supported environments

- Python >= 3.12
- GitHub (and repositories that have compatible URL structure with GitHub, e.g. GitHub enterprise)

This tool executes `$ git web--remote` to open a URL. To change the browser to be used, see [git-web--browse documentation](https://git-scm.com/docs/git-web--browse).

## Usage

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
$ poetry install
$ poetry run git-browse-remote --help
$ poetry run python3 -m unittest
``
