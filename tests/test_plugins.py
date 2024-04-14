from sys import path as syspath
from pathlib import Path

THIS_PATH = Path(__file__)
syspath.insert(0, THIS_PATH.parent.parent.as_posix())

from src.base.compPlugin import ComparisonPlugin, EnumGet


def validate_plugins(test_files_folder: Path | str, *plugins: type[ComparisonPlugin], ignore_warnings=False):
    """Run validation tests on the provided plugins and print any errors."""

    test_files = list(Path(test_files_folder).glob("*"))

    try:
        check_stats(plugins)
    except AssertionError as e:
        print(e)

    for plugin in plugins:
        files = _get_test_files(plugin, test_files)
        if not ignore_warnings and not files:
            print(f"{plugin.__name__} warning: Missing test files (Add some to tests folder)")

        try:
            plugin.validate(*files, ignore_warnings=ignore_warnings)
            
        except AssertionError as e:
            print(e)

        else:
            print(f"{plugin.__name__} successfully validated.")



def check_stats(plugins: list[ComparisonPlugin]):
    """Check for collisions in all Stat Enums. Raises AssertionError if any found."""
    enum: EnumGet
    vals: list[str] = []
    dupes: list[str] = []

    for plugin in plugins:
        for enum in plugin.STATS:
            if enum.name.upper() in vals:
                dupes.append(f"{enum}.name: ({enum.name})")
            if str(enum.value).upper() in vals:
                dupes.append(f"{enum}.value ({enum.value})")
            vals.append(enum.name.upper())
            vals.append(str(enum.value).upper())
    
    if dupes:
        raise AssertionError(f"Repeated StatEnums found in plugins: {', '.join(dupes)}")


def _get_test_files(plugin: type[ComparisonPlugin], files: list[Path]):
    """Get list of valid files for plugin from full file list."""
    result: list[ComparisonPlugin] = []
    for file in files:
        try:
            result.append(plugin(file))
        except plugin.InvalidFile:
            pass
    
    return result



if __name__ == "__main__":
    from src.base.compFilePlugin import FilePlugin
    from src.plugins.imagePlugin import ImagePlugin
    from src.plugins.videoPlugin import VideoPlugin

    validate_plugins(
        THIS_PATH.parent,
        FilePlugin, ImagePlugin, VideoPlugin,
        ignore_warnings=False
    )