"""Whether the file of the open network was changed by someone else (usually the game) since
the editor opened or saved it.

The game rewrites a savegame's AutoDrive_config.xml on each save, even with the same network,
so a new time stamp alone is no change: the network in the file is compared as well."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.file_io.autodrive_xml_writer import DECIMALS
from autodrive_editor.model.autodrive_data import AutoDriveData


@dataclass(frozen=True)
class DiskState:
    """The file as the editor last read or wrote it."""

    # Modification time (ns) and size; None while the file does not exist.
    stamp: tuple[int, int] | None
    fingerprint: str


def file_stamp(path: Path) -> tuple[int, int] | None:
    try:
        info = path.stat()
    except OSError:
        return None

    return info.st_mtime_ns, info.st_size


def network_fingerprint(data: AutoDriveData, file_format: ConfigFormat) -> str:
    """A hash of what the file holds of the network: positions with the file's decimals, flags,
    connections, markers and groups, with node ids numbered as the writer does."""

    decimals = DECIMALS[file_format]
    nodes = data.get_sorted_nodes()
    new_ids = {node.node_id: new_id for new_id, node in enumerate(nodes, start=1)}
    digest = hashlib.sha1()

    for node in nodes:
        outgoing = sorted(new_ids[t] for t in node.outgoing if t in new_ids)
        incoming = sorted(new_ids[t] for t in node.incoming if t in new_ids)
        digest.update(
            f"{node.x:.{decimals}f} {node.y:.{decimals}f} {node.z:.{decimals}f} {node.flag} "
            f"{outgoing} {incoming}\n".encode()
        )

    for marker in data.markers.values():
        digest.update(f"m {new_ids.get(marker.node_id)} {marker.name}\t{marker.group}\n".encode())

    for name in data.marker_group_names():
        digest.update(f"g {name}\n".encode())

    return digest.hexdigest()
