from pathlib import Path
from .compFile import File
from .compUtils import get_sibling, is_yes, printerr


def delete_files(files: list[File], verbose = False):
    """Delete all files not marked to keep. Returns ([deleted files], [failed files])."""
    
    if not files:
        printerr("No files were marked for deletion.")
        return (None, None)
    elif not is_yes(f"Are you sure you want to delete {len(files)} files"):
        return (None, None)

    printerr("Deleting files...")
    deleted: list[File] = []
    failed: list[File] = []
    for file in files:
        try:
            file.path.unlink()
            deleted.append(file)
            if verbose:
                printerr(f"  Deleted: {file.path}")
        except Exception as e:
            if file.path.name in str(e):
                printerr(f"  ERROR deleting: {e}")
            else:
                printerr(f"  ERROR deleting {file.short}: {e}")
            failed.append(file)

    return (deleted, failed)


def move_files(files: list[File], to_dirs: list[Path | str], verbose = False):
    """Move all files not marked to keep. Returns ([moved files], [failed files])."""
    
    if not files:
        printerr("No files were marked for moving.")
        return (None, None)
    
    for d in range(len(to_dirs)):
        to_dirs[d] = Path(to_dirs[d]).expanduser().resolve()
        if not to_dirs[d].is_dir():
            printerr(f"{to_dirs[d]} is not a valid directory. Move failed.")
            return (None, None)
    
    to_move: list[File] = []
    for file in files:
        if file not in to_move:
            to_move.append(file)
    if not is_yes(f"Are you sure you want to move {len(to_move)} files to {', '.join(str(d) for d in to_dirs)}"):
        return (None, None)

    printerr("Moving files...")
    moved: list[File] = []
    failed: list[File] = []
    for file in to_move:
        try:
            to_dir = get_sibling(file.path, to_dirs)
            file.path.rename(Path(to_dir, file.path.name))
            moved.append(file)
            if verbose:
                printerr(f"  Moved: '{file.path}' -> '{to_dir}/'")
        except Exception as e:
            if file.path.name in str(e):
                printerr(f"  ERROR moving: {e}")
            else:
                printerr(f"  ERROR moving {file.short}: {e}")
            failed.append(file)

    return (moved, failed)


def recover_files(files: list[File], from_dirs: list[Path | str], verbose = False):
    """Recover all files from dir not marked to keep. Returns ([recovered files], [failed files])"""
    if not files:
        printerr("No files were marked for recovering.")
        return (None, None)
    
    for d in range(len(from_dirs)):
        from_dirs[d] = Path(from_dirs[d]).expanduser().resolve()
        if not from_dirs[d].is_dir():
            printerr(f"{from_dirs[d]} is not a valid directory. Move failed.")
            return (None, None)
    
    to_move: list[File] = []
    for file in files:
        if file not in to_move:
            to_move.append(file)
    if not is_yes(f"Are you sure you want to attempt to recover {len(to_move)} files from {', '.join(str(d) for d in from_dirs)}"):
        return (None, None)

    printerr("Recovering files...")
    recovered: list[File] = []
    failed: list[File] = []
    for file in to_move:
        try:
            from_dir = get_sibling(file.path, from_dirs)
            Path(from_dir, file.path.name).rename(file.path)
            recovered.append(file)
            if verbose:
                printerr(f"  Moved: '{from_dir}/' -> '{file.path}'")
        except Exception as e:
            if file.path.name in str(e):
                printerr(f"  ERROR recovering: {e}")
            else:
                printerr(f"  ERROR recovering {file.short}: {e}")
            failed.append(file)
    
    return (recovered, failed)