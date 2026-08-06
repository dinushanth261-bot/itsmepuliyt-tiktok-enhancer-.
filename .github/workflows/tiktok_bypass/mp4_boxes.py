from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Box:
    type: str
    offset: int
    size: int
    end: int

def header_size(box: Box) -> int:
    return 16 if box.size == 1 else 8

def parse_boxes(data: bytes, start: int = 0, end: Optional[int] = None) -> List[Box]:
    if end is None:
        end = len(data)

    boxes = []
    pos = start
    while pos + 8 <= end:
        size = struct.unpack(">I", data[pos : pos + 4])[0]
        btype = data[pos + 4 : pos + 8].decode("latin1", errors="replace")

        if size == 1:
            if pos + 16 > end:
                break
            size = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]

        if size == 0:
            box_end = end
        else:
            box_end = pos + size

        if box_end > end or box_end <= pos:
            break

        boxes.append(Box(type=btype, offset=pos, size=size, end=box_end))
        pos = box_end

    return boxes

def find_box(data: bytes, box_type: str, start: int = 0, end: Optional[int] = None) -> Optional[Box]:
    for box in parse_boxes(data, start, end):
        if box.type == box_type:
            return box
    return None

def handler_type(data: bytes, hdlr_box: Box) -> str:
    offset = hdlr_box.offset + header_size(hdlr_box) + 8
    return data[offset : offset + 4].decode("latin1", errors="replace")
