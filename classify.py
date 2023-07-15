import shutil
from concurrent.futures import Future, ThreadPoolExecutor
from os import name, scandir
from pathlib import Path
from typing import Iterable

import regex as re
from rich import print
from rich.progress import track

from logger import logger
from model import Platform

user_id_pattern = r"(?<=@user_id=).*?(?=@|(\.[a-zA-Z]+$))"
user_pattern = r"(?<=@user=).*?(?=@|(\.[a-zA-Z]+$))"
platform_pattern = r"(?<=@from=).*?(?=@|(\.[a-zA-Z]+$))"
tag_pattern = r"(?<=@tags=).*?(?=@|(\.[a-zA-Z]+$))"

platformId = int
platform = str
platformTarget = tuple[platformId, platform]
imagesPath = dict[platformTarget, list[Path]]


def scan_folder(loc: Path):
    folder = [str(loc)]
    file: list[str] = list()
    while folder:
        now = folder.pop(0)
        logger.info(f"正在遍历 {now}.")
        with scandir(now) as dir:
            for it in dir:
                if it.is_file():
                    file.append(it.path)
                else:
                    folder.append(it.path)
    return file


def regex_info(file: Iterable[str]):
    res: list[tuple[str, tuple[Future, Future, Future]]] = list()
    with ThreadPoolExecutor() as exec:
        for i in file:
            r = (
                exec.submit(re.search, user_id_pattern, i, concurrent=True),
                exec.submit(re.search, platform_pattern, i, concurrent=True),
                exec.submit(re.search, user_pattern, i, concurrent=True),
            )
            res.append((i, r))
    return res


def get_tag(s: Iterable[str]):
    res: list[Future] = list()
    with ThreadPoolExecutor() as exec:
        for i in s:
            r = exec.submit(re.search, tag_pattern, i, concurrent=True)
            res.append(r)
    ress: list[list[str]] = list()
    for i in res:
        a: re.Match[str] | None = i.result()
        if a:
            assert isinstance(a, re.Match)
            ress.append(a.group().split(","))
        else:
            ress.append([""])
    return ress


def find_all_fast(targets: dict[Platform, set[Path]], loc: Path):
    """
    1. 使用 `os.scandir`
    2. 递归变递推
    3. 使用第三方 `regex` 库进行正则匹配 (释放 GIL)
    """
    file = scan_folder(loc)
    res = regex_info(file)
    for i in track(res, description="", transient=True):
        a = i[1][0].result()
        b = i[1][1].result()
        if a and b:
            a = a.group()
            b = b.group()
            st = (int(a), b)
            for j in targets:
                if st == (j.platform_id, j.platform):
                    targets[j].add(Path(i[0]))


def find_all(targets: dict[Platform, list[Path]], loc: Path):
    logger.info(f"正在遍历 {loc}.")
    for path in loc.iterdir():
        if path.is_dir():
            find_all(targets, path)
        else:
            name = path.name
            _user_id = re.search(user_id_pattern, name)
            _platform = re.search(platform_pattern, name)
            if _user_id and _platform:
                _user_id = int(_user_id.group())
                _platform = _platform.group().lower()
                st = (_user_id, _platform)
                for i in targets.keys():
                    if st == (i.platform_id, i.platform):
                        targets[i].append(path)


def classify(target: dict[Platform, set[Path]], loc: Path):
    ress: list[tuple[Path, Path]] = []
    for i in target:
        if not target[i]:
            continue
        logger.info(f"正在预处理 {i} 的文件.")
        folder = loc / f"@id={i.author_id}"
        if not folder.is_dir():
            folder.mkdir()
        for path in target[i]:
            if path.parent != folder:
                ress.append((path, folder))
            else:
                logger.debug(f"文件 '{path}' 已经目标目录,将会被忽略.")
    exist_err = 0
    for i in track(ress, description=""):
        try:
            shutil.move(i[0], i[1])
        except shutil.Error as e:
            exist_err += 1
            path = Path(i[1]) / "bin"
            path.mkdir(exist_ok=True)
            logger.error(f"文件 {i[1]/i[0].name} 已经存在! 原始文件将会移动到 /bin 下.")
            shutil.move(i[0], path)

    logger.info(f"分类完毕, 本次共分类了 {len(ress)} 个文件. 其中有重复文件 {exist_err} 个.")


if __name__ == "__main__":
    dic = {(22391910, "pixiv"): []}
    find_all([(22391910, "pixiv")], Path("./testdata"), dic)  # type:ignore
    print(dic)
