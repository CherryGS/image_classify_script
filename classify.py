import re
import shutil
from pathlib import Path

from rich import print
from rich.progress import track

user_id_pattern = r"(?<=@user_id=)[0-9]+(?<=@user_id=)[0-9]+"
platform_pattern = r"(?<=@from=)[a-z]+"

authorTarget = tuple[int, str]
imagesPath = dict[authorTarget, list[Path]]


def find_all(targets: list[tuple[int, str]], loc: Path, res: imagesPath):
    for path in loc.iterdir():
        if path.is_dir():
            find_all(targets, path, res)
        else:
            name = path.name
            _user_id = re.search(user_id_pattern, name)
            _platform = re.search(platform_pattern, name)
            if _user_id and _platform:
                _user_id = _user_id.group()
                _platform = _platform.group()
                st = (_user_id, _platform)
                if st in targets:
                    res[st].append(path)


def classify(res: imagesPath, loc: Path, map: dict[authorTarget, tuple[int, str]]):
    total = 0
    for i in track(res, description="分类中..."):
        if not res[i]:
            continue
        author = map[i]
        folder = loc / f"@id={author[0]}@preview_name={author[1]}"
        if not folder.is_dir():
            folder.mkdir()
        for path in res[i]:
            shutil.copy(path, folder)
        total += len(res[i])
    print(f"分类完毕, 本次共分类了 {total} 个文件.")
