# SPDX-FileCopyrightText: 2024 Fraunhofer FKIE
# SPDX-FileContributor: Marten Ringwelski <git@maringuu.de>
#
# SPDX-License-Identifier: GPL-3.0-only WITH GPL-3.0-linking-exception

import datetime as dt
import pathlib as pl

import click

from . import database, repo
from .feed import Feed


@click.command(
    name="fkie-cve-make-release",
)
@click.option(
    "--date",
    type=click.DateTime(
        formats=[
            "%Y-%m-%d",
        ]
    ),
    help="Specifies the state of the database. If not given implies '--fetch'",
)
@click.argument(
    "PATH",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        exists=False,
        path_type=pl.Path,
    ),
)
@click.option(
    "--fetch",
    is_flag=True,
    default=False,
    help="Fetch the latest changes from https://github.com/fkie-cad/nvd-json-data-feeds",
)
@click.option(
    "--xz-preset",
    default=9,
    help="The xz compression preset level to use.",
)
@click.option(
    "--feed-name",
    default=None,
    help="The name of the feed to create. If not given, create all feeds.",
)
def cli(
    date: dt.datetime | None,
    path: pl.Path,
    fetch: bool,
    xz_preset,
    feed_name: str | None,
):
    """Create a release package of the CVE datafeeds released by FKIE-CAD."""
    fetch |= date is None
    if path.exists() and len(list(path.iterdir())) > 0:
        raise click.ClickException(
            f"{path} exists and is not empty. Please specify a non-existing or empty directory."
        )

    if feed_name is not None and not _feed_name_is_valid(feed_name):
        raise click.ClickException(
            f"{feed_name} is not a valid --feed-name."
            " Please chose either a year after 1999, or from 'all', 'recent', or 'modified'."
        )

    path.mkdir(exist_ok=True)

    if date is None:
        # XXX Timezones and times when it is not released yet
        timestamp = dt.date.today()
    else:
        timestamp = date.date()

    if fetch:
        click.echo("Fetching repository")
        repo.fetch()

    click.echo(f"Checking out repository for timestamp {timestamp}")
    repo.checkout(timestamp)
    db = database.CveDatabase.from_timestamp(timestamp)

    if feed_name is None:
        _write_all_feeds(path, db, xz_preset)
    else:
        click.echo(f"Creating {feed_name} archive")
        Feed.write(
            dest_dir=path,
            db=db,
            name=feed_name,
            xz_preset=xz_preset,
        )


def _write_all_feeds(path: pl.Path, db: database.CveDatabase, xz_preset: int):
    for year in range(1999, db.timestamp.year + 1):
        click.echo(f"Creating {year} archive")
        Feed.write(
            dest_dir=path,
            db=db,
            name=str(year),
            xz_preset=xz_preset,
        )

    click.echo("Creating all archive")
    Feed.write(
        dest_dir=path,
        db=db,
        name="all",
        xz_preset=xz_preset,
    )
    click.echo("Creating recent archive")
    Feed.write(
        dest_dir=path,
        db=db,
        name="recent",
        xz_preset=xz_preset,
    )
    click.echo("Creating modified archive")
    Feed.write(
        dest_dir=path,
        db=db,
        name="modified",
        xz_preset=xz_preset,
    )


def _feed_name_is_valid(name: str) -> bool:
    if name in ["all", "recent", "modified"]:
        return True

    try:
        year = int(name)
        return year >= 1999  # noqa: PLR2004
    except ValueError:
        return False


cli()
