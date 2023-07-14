import re
import shutil
from pathlib import Path
from logger import logger
from rich import print
from rich.progress import track

user_id_pattern = r"(?<=@user_id=)[0-9]+"
platform_pattern = r"(?<=@from=)\w+"

platformId = int
platform = str
platformTarget = tuple[platformId, platform]
imagesPath = dict[platformTarget, list[Path]]


def find_all(targets: list[platformTarget], loc: Path, res: imagesPath):
    for path in loc.iterdir():
        logger.info(f"正在遍历 {path}.")
        if path.is_dir():
            find_all(targets, path, res)
        else:
            name = path.name
            _user_id = re.search(user_id_pattern, name)
            _platform = re.search(platform_pattern, name)
            if _user_id and _platform:
                _user_id = int(_user_id.group())
                _platform = _platform.group().lower()
                st = (_user_id, _platform)
                if st in targets:
                    res[st].append(path)


def classify(
    res: imagesPath, loc: Path, map: dict[platformTarget, tuple[int, str, str]]
):
    ress: list[tuple] = []
    for i in track(res, description=""):
        if not res[i]:
            continue
        logger.info(f"正在预处理作者 {i} 的文件.")
        author = map[i]
        pre = loc / f"@id={author[0]}"
        folder = pre
        if not folder.is_dir():
            folder.mkdir()
        for path in res[i]:
            ress.append((path, folder))
    for i in track(ress, description=""):
        shutil.copy(i[0], i[1])

    print(f"分类完毕, 本次共分类了 {len(ress)} 个文件.")


if __name__ == "__main__":
    dic = {(22391910, "pixiv"): []}
    find_all([(22391910, "pixiv")], Path("./testdata"), dic)  # type:ignore
    print(dic)
