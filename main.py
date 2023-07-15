"""stage 1"""
import os
from pathlib import Path

os.chdir(Path(os.path.realpath(__file__)).parent)

"""stage 2"""
from logger import logger

"""stage 3"""
import shutil
import time
from typing import Annotated, Iterable, Optional

import typer
from rich import print
from rich.progress import track
from rich.traceback import install
from sqlalchemy import select
from sqlalchemy.orm import Session

from classify import classify, find_all_fast, get_tag, regex_info, scan_folder
from model import Author, Platform, engine

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


@app.command("nsfw")
def classify_nsfw(folders: Annotated[list[Path], typer.Argument(help="待扫描的目标目录们")]):
    """
    扫描文件夹 , 将含有 nsfw 图片移到相应子文件夹.
    建议首先使用 `classify` 将图片移到作者文件夹下.
    """
    paths: set[str] = set()
    for folder in folders:
        for path in scan_folder(folder):
            paths.add(path)
    logger.info(f"已统计完源路径所有图片,共 {len(paths)} 张.")
    ok = typer.confirm(f" 是否继续?")
    if not ok:
        logger.info("停止.")
        raise typer.Abort()
    total = 0
    total_move = 0
    tags = get_tag(paths)
    for i, j in track(zip(paths, tags), description=""):
        if "R18" in j or "R-18" in j or "R-18G" in j or "R18G" in j:
            total += 1
            p = Path(i)
            if p.parent.parts[-1] != "nsfw":
                total_move += 1
                l = p.parent / "nsfw"
                if not l.is_dir():
                    l.mkdir(exist_ok=True)
                logger.debug(f"正在移动 {p} 至 {l}.")
                shutil.move(p, l)
    logger.info(f"共有nsfw图 {total} 张,其中有 {total_move} 张被移动.")


@app.command("scan")
def scan_image(folders: Annotated[list[Path], typer.Argument(help="待扫描的目标目录们")]):
    paths: set[str] = set()
    for folder in folders:
        for path in scan_folder(folder):
            paths.add(path)
    res = regex_info(paths)
    info: dict[tuple[int, str], int] = dict()
    for i in track(res, description="", transient=True):
        a = i[1][0].result()
        b = i[1][1].result()
        if a and b:
            a = a.group()
            b = b.group()
            st = (int(a), b)
            if st in info:
                info[st] += 1
            else:
                info[st] = 1
    logger.info(f"{sorted(info.items(), key=lambda x: x[1])}")
    logger.info(f"共有文件 {sum(info.values())}")


@app.command("classify")
def classify_image(
    src: Annotated[list[Path], typer.Argument(help="待分类文件顶层目录")],
    des: Annotated[Path, typer.Option(help="目标目录")],
    ids: Annotated[tuple[int, int], typer.Option(help="作者在数据库对应的唯一标识符范围,左闭右开.")],
):
    """
    将具有相同数据库id的作者平台的图片分到一起.
    """
    author_ids = [i for i in range(ids[0], ids[1])]
    lis = get_author_platform(author_ids)
    if not lis:
        logger.warning("未获取到作者的平台信息或该作者在数据库中不存在,程序将退出.")
        raise typer.Abort()
    logger.debug(f"获取到的平台信息:\n {lis}")

    paths: dict[Platform, set[Path]] = dict()
    for i in lis:
        paths[i] = set()
    for i in src:
        find_all_fast(paths, i)
    logger.debug(f"获取到的文件信息:\n{paths}")
    info = [(i, f"{len(paths[i])} 个文件.") for i in paths]
    logger.info(f"{info}")

    logger.info(f"已统计完源路径所有图片,共 {sum([len(paths[i]) for i in paths])} 张.")
    ok = typer.confirm(f" 是否继续?")
    if ok:
        classify(paths, des)
    else:
        logger.info("停止.")
        raise typer.Abort()


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
                logger.info(f"将要添加 {p} .")
                i = typer.confirm(" 是否确定?")
                if i:
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
                    print("添加操作已取消")
                    raise typer.Abort()
            case _:
                print(f"[red]Alert![/red]出现重复字段,数据库可能已经损坏!")


@app.command("new")
def add_author(
    platform_id: Annotated[int, typer.Argument(help="作者在平台的唯一标识符")],
    platform: Annotated[str, typer.Argument(help="唯一标识符对应的平台")],
    name: Annotated[
        str, typer.Argument(help="作者在数据库的预览名,默认为空.添加含有特殊字符(如空格)的作者名时请注意使用引号.")
    ] = "",
    quick: Annotated[bool, typer.Option(help="快速添加对应平台")] = False,
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
        session.commit()
        logger.info(f"数据库中添加了新作者 {author}.")
    if quick:
        add_platform(platform_id, platform, author.id, name)


if __name__ == "__main__":
    logger.debug("Run in debug Mode.")
    app()
    from logger import file

    file.close()
