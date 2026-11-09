"""Inventory of the downloadable file archive (Drive files/, mirrored to R2).

The file host (Cloudflare R2) is case-sensitive and serves objects under the exact
names the archive holds on disk, which do not always match the spelling the original
site's links or the Wayback manifest used (Systems/ vs systems/, 1998conference/ vs
1998Conference/, Images/ vs images/). Every link the build emits to FILE_BASE is
therefore resolved case-insensitively against this inventory and emitted with the
on-disk spelling; a target that is not in the archive degrades to a Wayback lookup
instead of a 404 on the file host.

The walk over Drive takes a couple of minutes, so the result is cached next to the
other manifests; delete the cache or pass refresh=True to rebuild it.
"""
import os, time

DRIVE = r"G:/Shared drives/Software & Apps/FAA Fire Safety Site/FAA_Fire_Safety_Archive"
FILES = os.path.join(DRIVE, "files")
INVENTORY = os.path.join(DRIVE, "_manifests", "files_inventory.txt")


def _walk():
    for dp, _, fns in os.walk(FILES):
        rel = os.path.relpath(dp, FILES).replace("\\", "/")
        for fn in fns:
            yield fn if rel == "." else f"{rel}/{fn}"


def load_inventory(refresh: bool = False) -> dict:
    """lowercase archive-relative path -> '/Exact/Case/path' as stored on disk and R2"""
    if refresh or not os.path.exists(INVENTORY):
        t = time.time()
        paths = sorted(_walk())
        os.makedirs(os.path.dirname(INVENTORY), exist_ok=True)
        with open(INVENTORY, "w", encoding="utf-8") as f:
            f.write("\n".join(paths) + "\n")
        print(f"file inventory: {len(paths)} files walked in {time.time() - t:.0f}s -> {INVENTORY}")
    lookup = {}
    with open(INVENTORY, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n")
            if p:
                lookup[p.lower()] = "/" + p
    return lookup
