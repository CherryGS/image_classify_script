"""stage 1"""
import os
from datetime import date
from functools import cache
from pathlib import Path

import regex

os.chdir(Path(os.path.realpath(__file__)).parent)

"""stage 2"""
from .logger import logger

"""stage 3"""
import shutil
import time
from typing import Annotated, Hashable, Iterable, Optional

import typer
from anyutils.file import scan_folder
from anyutils.regex import regex_info
from rich import print
from rich.progress import track
from rich.traceback import install
from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import Author, Platform, engine

install(show_locals=True)
app = typer.Typer()


def backup():
    path = Path(".") / "backup"
    db = Path(".") / "database.sqlite"
    if not path.is_dir():
        path.mkdir()
    bac = path / f"{db.name}.{int(time.time())}.backup"
    shutil.copy(db, bac)


def get_author_platform(author_ids: list[int]):
    with Session(engine) as session:
        stmt = select(Platform).where(Platform.author_id.in_(author_ids))
        return [i for i in session.scalars(stmt)]


user_id_pattern = r"(?<=@user_id=).*?(?=@|(\.[a-zA-Z]+$))"
user_pattern = r"(?<=@user=).*?(?=@|(\.[a-zA-Z]+$))"
from_pattern = r"(?<=@from=).*?(?=@|(\.[a-zA-Z]+$))"
date_pattern = r"(?<=@date=).*?(?=@|(\.[a-zA-Z]+$))"
id_pattern = r"(?<=@id=).*?(?=@|(\.[a-zA-Z]+$))"


@cache
def get_author(platform: str, user_id: str, user: str):
    with Session(engine) as session:
        res = list(
            session.scalars(
                select(Platform)
                .where(Platform.platform == platform)
                .where(Platform.platform_id == user_id)
            )
        )

        if not res:
            author = Author(name=user, platform=platform, platform_id=user_id)
            session.add(author)
            session.flush()
            platf = Platform(
                platform_id=user_id,
                platform=platform,
                name=user,
                author_id=author.id,
            )
            session.add(platf)
            session.commit()
            res = [platf]
            logger.info(f"Add {author}")
            logger.info(f"Add {platf}")

        authors = list(
            session.scalars(select(Author).where(Author.id == res[0].author_id))
        )
        logger.debug(f"{authors[0]}")
        return authors[0]


@app.command("auto")
def auto(
    folders: Annotated[list[Path], typer.Argument(help="待扫描的目标目录们")],
    des: Annotated[Path, typer.Option(help="目标目录")],
):
    """
    扫描目录,加入作者.
    """
    backup()
    paths: set[os.DirEntry[str]] = set()
    for folder in folders:
        for path in scan_folder(folder):
            paths.add(path)
    info = regex_info(
        map(lambda x: x.name, paths),
        [from_pattern, user_id_pattern, user_pattern, date_pattern],
    )
    dic: dict[int, Path] = dict()
    for i in os.scandir(des):
        if i.is_dir():
            res = regex.search(id_pattern, i.name)
            if res:
                dic[int(res.group())] = Path(i)
    for i, j in track(zip(info, paths)):
        (platform, user_id, user, create_time) = i
        if platform is None or user_id is None:
            logger.warning(f"图片 '{i[0]}' 无法查询到信息 , 跳过.")
            continue
        author = get_author(platform, user_id, user if user else "Unknown")
        if author.id not in dic:
            name = author.name.replace("@", "＠").replace(".", "。")
            path = des / f"@id={author.id}@name={author.platform}_{name}".replace(
                " ", "-"
            )
            dic[author.id] = path

        date_ = (
            date.fromisoformat(create_time) if create_time else date.fromtimestamp(0)
        )
        path = (
            dic[author.id]
            / f"@from={platform}"
            / f"@date={date_.year}-{('0'+str(date_.month))[-2:]}-01"
        )
        if not path.is_dir():
            os.makedirs(path)
            logger.info(f"Make dir '{path}'")
        if not (path / j.name).is_file():
            shutil.move(j, path)
        else:
            logger.debug(f"重复的文件 '{j.path}'")


@app.command("find")
def find_author(
    platform_id: Annotated[Optional[int], typer.Option(help="作者在平台对应的唯一标识")] = None,
    name: Annotated[Optional[str], typer.Option(help="作者在平台的名称")] = None,
    platform: Annotated[Optional[str], typer.Option(help="唯一标识符所对应的平台")] = None,
):
    """
    根据信息查找作者的数据库id. 平台应该使用小写.
    """
    if platform:
        platform = platform.lower()
    if platform_id is None and name is None and platform is None:
        print("不可同时为空.")
        raise typer.Abort()
    with Session(engine) as session:
        stmt = select(Platform)
        if platform_id:
            stmt = stmt.where(Platform.platform_id == platform_id)
        if name:
            stmt = stmt.where(Platform.name == name)
        if platform:
            stmt = stmt.where(Platform.platform == platform)
        author_ids = {i.author_id for i in list(session.scalars(stmt))}
        authors = list(session.scalars(select(Author).where(Author.id.in_(author_ids))))
        print(f"查询结果为:\n{authors}")


@app.command("add")
def add_platform(
    platform_id: Annotated[int, typer.Argument(help="作者在平台对应的唯一标识符")],
    platform: Annotated[str, typer.Argument(help="唯一标识符所对应的平台")],
    author_id: Annotated[int, typer.Argument(help="作者在数据库对应的唯一标识符")],
    platform_name: Annotated[str, typer.Argument(help="作者的平台名称,默认为空")] = "",
    ok: Annotated[bool, typer.Option(help="快速添加对应平台")] = False,
):
    """
    向数据库中添加作者所属的平台账号信息. 平台应该使用小写.
    """
    platform = platform.lower()
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
                logger.info(f"将要添加 {p}.")
                if not ok:
                    ok = typer.confirm(" 是否确定?")
                if ok:
                    stmt = (
                        select(Platform)
                        .where(Platform.platform_id == platform_id)
                        .where(Platform.platform == platform)
                    )
                    res = list(session.scalars(stmt))
                    match len(res):
                        case 0:
                            session.add(p)
                            session.commit()
                            logger.info("添加操作已完成")
                        case 1:
                            if res[0].author_id == p.author_id:
                                logger.info("重复添加,该操作将会跳过.")
                            else:
                                logger.warning(
                                    f"出现了仅有 author_id 不一样的项,请检查数据表. {res[0]}"
                                )
                        case _:
                            logger.warning(f"出现了多项重复项,请检查数据表. {res}")
                else:
                    logger.info("添加操作已取消")
                    raise typer.Abort()
            case _:
                logger.error(f"[red]Alert![/red]出现重复字段,数据库可能已经损坏!")


def merge_file(id: int, ids: list[int], des: Path):
    dic: dict[int, Path] = dict()
    for i in os.scandir(des):
        if i.is_dir():
            res = regex.search(id_pattern, i.name)
            if res:
                dic[int(res.group())] = Path(i)
    if not id in dic:
        logger.error(f"id 为 {id} 的相关文件夹必须存在.")
        raise typer.Abort()

    path = dic[id]
    logger.info(f"目标目录 '{path}'")
    for i in ids:
        logger.info(f"正在合并 {i} 相关文件.")
        if i in dic:
            shutil.copytree(dic[i], path, dirs_exist_ok=True)


@app.command("merge")
def merge_author(
    ids: Annotated[list[int], typer.Argument(help="待合并的id,默认合并到第一个上")],
    des: Annotated[Optional[Path], typer.Option(help="根目录")] = None,
):
    """
    将多个作者合并成一个.
    指定了 --des 之后会合并文件.
    """
    id = ids[0]
    ids = ids[1:]
    backup()
    with Session(engine) as session:
        p1 = list(session.scalars(select(Author).where(Author.id == id)))
        p2 = list(session.scalars(select(Author).where(Author.id.in_(ids))))
        logger.info(f"{p2} 将被合并到 {p1} 中. 其在数据库中的信息会被删除.")
        ok = typer.confirm(" 是否确定?")
        if not ok:
            logger.info("停止.")
            raise typer.Abort()
        for i in track(ids, description=""):
            stmt = select(Platform).where(Platform.author_id == i)
            res = list(session.scalars(stmt))
            for j in res:
                j.author_id = id
        for i in p2:
            logger.info(f"正在删除 {i}.")
            session.delete(i)
        session.commit()
    if des is not None:
        merge_file(id, ids, des)


@app.command("new")
def add_author(
    platform_id: Annotated[int, typer.Argument(help="作者在平台的唯一标识符")],
    platform: Annotated[str, typer.Argument(help="唯一标识符对应的平台")],
    name: Annotated[
        str, typer.Argument(help="作者在数据库的预览名,默认为空.添加含有特殊字符(如空格)的作者名时请注意使用引号.")
    ] = "",
    quick: Annotated[bool, typer.Option(help="忽略确定.")] = False,
):
    """
    向数据库中添加作者信息. 平台应该使用小写.
    """
    platform = platform.lower()
    backup()
    with Session(engine) as session:
        stmt = (
            select(Author)
            .where(Author.platform_id == platform_id)
            .where(Author.platform == platform)
        )
        if len(list(session.scalars(stmt))) != 0:
            logger.info(f"[green]该项已有,过程将[red][bold]停止[/bold][/red].[/green]")
            raise typer.Abort()
        author = Author(name=name, platform=platform, platform_id=platform_id)
        session.add(author)
        session.flush()
        logger.info(f"将要添加 {author}.")
        if not quick:
            quick = typer.confirm(" 是否确定?")
        if quick:
            session.commit()
            logger.info(f"数据库中添加了新作者 {author}.")
        else:
            session.rollback()
            logger.info(f"停止.")
            raise typer.Abort()
    if quick:
        add_platform(platform_id, platform, author.id, name, quick)
