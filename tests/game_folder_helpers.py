"""A fake FS25 user folder for tests."""


def make_game_folder(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "game.xml").write_text("<game/>", encoding="utf-8")
    for number in (1, 2, 10):
        (path / f"savegame{number}").mkdir()
    (path / "savegameBackup").mkdir()
    return path
