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
from typing import Annotated, Optional

app = typer.Typer()


def backup():
    path = Path(".") / "backup"
    db = Path(".") / "database.sqlite"
    if not path.is_dir():
        path.mkdir()
    bac = path / f"{db.name}.{int(time.time())}.backup"
    shutil.copy(db, bac)


def get_author_platform(author_id: int):
    with Session(engine) as session:
        stmt = select(Platform).where(Platform.author_id == author_id)
        lis = []
        for i in session.scalars(stmt):
            lis.append((i.platform_id, i.platform))
        return lis


@app.command("classify")
def classify_image(
    author_id: Annotated[int, typer.Argument(help="作者在数据库对应的唯一标识符")],
    src: Annotated[Path, typer.Argument(help="待分类文件顶层目录")],
    des: Annotated[Path, typer.Argument(help="目标目录")],
):
    lis = get_author_platform(author_id)
    paths = dict()
    map = dict()
    for i in lis:
        paths[i] = list()
        map[i] = author_id
    find_all(lis, src, paths)
    ok = typer.confirm(f"已统计完源路径所有图片, 是否继续?")
    if ok:
        classify(paths, des, map)
    else:
        print("停止.")
        raise typer.Abort()


@app.command("find")
def find_author(
    platform_id: Annotated[Optional[int], typer.Argument(help="作者在平台对应的唯一标识")] = None,
    name: Annotated[Optional[str], typer.Argument(help="作者在数据库")] = None,
    platform: Annotated[Optional[str], typer.Argument(help="唯一标识符所对应的平台")] = None,
):
    if platform_id is None and name is None and platform is None:
        print("不可同时为空.")
        raise typer.Abort()
    with Session(engine) as session:
        stmt = select(Author)
        if platform_id:
            stmt = stmt.where(Author.platform_id == platform_id)
        if name:
            stmt = stmt.where(Author.name == name)
        if platform:
            stmt = stmt.where(Author.platform == platform)
        authors = list(session.scalars(stmt))
        print(f"查询结果为:\n{authors}")


@app.command("add")
def add_platform(
    platform_id: Annotated[int, typer.Argument(help="作者在平台对应的唯一标识符")],
    platform: Annotated[str, typer.Argument(help="唯一标识符所对应的平台")],
    author_id: Annotated[int, typer.Argument(help="作者在数据库对应的唯一标识符")],
    platform_name: Annotated[str, typer.Argument(help="作者的平台名称,默认为空")] = "",
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
                    platform_id=platform_id,
                    platform=platform,
                    name=platform_name,
                    author_id=author_id,
                )
                i = typer.confirm(f"将要添加 {p} , 是否确定.")
                if i == "y":
                    session.add(p)
                    session.commit()
                    print("添加操作已完成")
                else:
                    print("添加操作已取消")
                    raise typer.Abort()
            case _:
                print(f"[red]Alert![/red]出现重复字段,数据库可能已经损坏!")


@app.command("new")
def add_author(
    platform_id: Annotated[int, typer.Argument(help="作者在平台的唯一标识符")],
    platform: Annotated[str, typer.Argument(help="唯一标识符对应的平台")],
    name: Annotated[str, typer.Argument(help="作者在数据库的预览名")],
):
    backup()
    with Session(engine) as session:
        stmt = (
            select(Author)
            .where(Author.platform_id == platform_id)
            .where(Author.platform == platform)
        )
        if len(list(session.scalars(stmt))) != 0:
            print(f"[green]该项已有,过程将[red][bold]停止[/bold][/red].[/green]")
            raise typer.Abort()
        author = Author(name=name, platform=platform, platform_id=platform_id)
        session.add(author)
        session.commit()
        print(f"数据库中添加了新作者 {author}.")


if __name__ == "__main__":
    app()
