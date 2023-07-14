import re
import shutil
import time
from pathlib import Path

import typer
from rich import print
from sqlalchemy import select
from sqlalchemy.orm import Session

from classify import classify, find_all
from model import Author, Platform, engine

app = typer.Typer()


def backup():
    path = Path(".") / "backup"
    db = Path(".") / "database.sqlite"
    if not path.is_dir():
        path.mkdir()
    bac = path / f"{db.name}.{int(time.time())}.backup"
    shutil.copy(db, bac)


def get_author_platform(author_id: int):
    with Session(engine):
        ...


@app.command("classify")
def classify_image(author_id: int, src: Path, des: Path):
    ...


@app.command("find")
def find_author(name: str, platform: str):
    with Session(engine) as session:
        stmt = (
            select(Author).where(Author.name == name).where(Author.platform == platform)
        )
        authors = list(session.scalars(stmt))
        match len(authors):
            case 0:
                print(
                    f"不存在满足 author_name = '{name}', author_platform = '{platform}' 的作者"
                )
            case 1:
                print(f"该作者在数据库中对应 id = {authors[0].id}")
            case _:
                print(f"[red]Alert![/red]出现重复字段,数据库可能已经损坏!")


@app.command("add")
def add_platform(
    user_id: int,
    platform: str,
    author_id: int,
    platform_name: str = "",
):
    backup()
    with Session(engine) as session:
        stmt = select(Author).where(Author.id == author_id)
        authors = list(session.scalars(stmt))
        match len(authors):
            case 0:
                print(f"id = {author_id} 的作者不存在!")
            case 1:
                p = Platform(
                    user_id=user_id,
                    platform=platform,
                    name=platform_name,
                    author_id=author_id,
                )
                print(f"将要添加 {p} , 是否确定. y/n")
                i = input()
                if i == "y":
                    session.add(p)
                    session.commit()
                    print("添加操作已完成")
                else:
                    print("添加操作已取消")
            case _:
                print(f"[red]Alert![/red]出现重复字段,数据库可能已经损坏!")


@app.command("create")
def add_author(name: str, platform: str):
    backup()
    with Session(engine) as session:
        stmt = (
            select(Author).where(Author.name == name).where(Author.platform == platform)
        )
        if len(list(session.scalars(stmt))) != 0:
            print(f"[green]该项已有,过程将[red][bold]停止[/bold][/red].[/green]")
            return
        author = Author(name=name, platform=platform)
        session.add(author)
        session.commit()
        print(f"Add new author '{author}'")


if __name__ == "__main__":
    app()
