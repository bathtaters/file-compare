from .compFile import File, FileGroup
from .compUtils import printerr, get_matches

def check_data(file_data: list[FileGroup]):
    """Check that each file has at least one selected to keep,
    returns list of files to delete"""
    
    keeping: dict[int,int] = {}
    to_delete: list[File] = []

    for group, files in enumerate(file_data):

        for file in files:
            if not file.keep:
                to_delete.append(file)
            
            if group not in keeping:
                keeping[group] = int(file.keep)
            else:
                keeping[group] += int(file.keep)
    
    deleteing = [g for g in keeping if not keeping[g]]
    if deleteing:
        if len(deleteing) == len(keeping):
            printerr(f"  WARNING! Missing selections from all groups: Add marks in Keep column.")
        else:
            printerr(f"  WARNING! Missing selections from these groups: {', '.join(str(d) for d in deleteing)}")

    return to_delete


def clean_data(file_data: list[FileGroup], clean_solo = False, clean_kept = False, min_stats = 0, verbose = True):
    """Checks each file, removing deleted ones.
    - If clean_solo is True, will remove groups with one member.
    - If clean_kept is True, will remove all groups whoose entire group is marked to keep.
    - Will remove files who don't share > min_stats stats with any other group member.
    - If verbose is True, shows alert on removing deleted file/group.
    - Returns a count of (deleted files, removed groups)"""

    def matcher(file: File, other: File, min_stats=min_stats):
        return file.match_count(other, min_stats) >= min_stats

    empty, count, groups = [], 0, 0
    for idx, files in enumerate(file_data):

        removed = set(i for i,p in enumerate(files) if not p.path.exists())

        if min_stats:
            keep = get_matches(files, matcher, removed)
            removed.update(i for i in range(len(files)) if i not in keep)
        
        if clean_solo and len(removed) + 1 == len(files):
            removed = range(len(files))
        else:
            removed = sorted(removed)

        for i in reversed(removed):
            p = files.pop(i)
            count += 1
            if verbose:
                printerr(f"  Cleaned up deleted file: {p.short}")
        if all(p.keep for p in files) if clean_kept else not files:
            empty.append(idx)
    
    for idx in reversed(empty):
        file_data.pop(idx)
        groups += 1
        if verbose:
            printerr(f"  Removed entire group: {idx}")
    
    return (count, groups)