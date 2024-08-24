from typing import Optional
import click

from .logger import logger
from .main import open_path, open_pr


@click.command()
@click.option(
    "-p", "--pr", is_flag=True, help="Open the Pull request view for the current branch"
)
@click.argument("path", required=False)
def run(pr: bool, path: Optional[str]):
    if path is not None and pr:
        logger.warn("Path is ignored when the `--pr` flag is set")

    if pr:
        open_pr()
    else:
        open_path(path)


if __name__ == "__main__":
    run()  # type: ignore
