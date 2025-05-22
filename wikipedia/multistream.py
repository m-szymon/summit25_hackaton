import bz2
import xml.etree.ElementTree as ET
from typing import List, Tuple
from collections import defaultdict
import mwparserfromhell
import struct

class WikipediaMultistreamReader:
    index_type: str = 'binary'
    def __init__(self, xml_bz2_path: str, index_bz2_path: str):
        self.xml_bz2_path = xml_bz2_path
        self.index_bz2_path = index_bz2_path

    def list_index_entries(self, start: int = 0, count: int = 10) -> List[Tuple[str, str, str]]:
        """
        List entries from the multistream index file.
        Returns a list of tuples: (offset, article_id, article_title)
        """
        entries = []
        with bz2.open(self.index_bz2_path, 'rt', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if i < start:
                    continue
                if len(entries) >= count:
                    break
                parts = line.strip().split(':', 2)
                if len(parts) == 3:
                    entries.append((parts[0], int(parts[1]), parts[2]))
        return entries

    def list_binary_index_entries(self, start: int = 0, count: int = 10, index_path: str = None) -> list:
        """
        Read entries from the binary index file. Each entry is three 64-bit unsigned ints:
        (stream_offset, page_number, page_id)
        Returns a list of tuples.
        """
        if index_path is None:
            index_path = self.index_bz2_path
        entries = []
        entry_size = 8 * 3  # 3x 64-bit unsigned ints
        with open(index_path, 'rb') as f:
            f.seek(start * entry_size)
            for _ in range(count):
                data = f.read(entry_size)
                if len(data) < entry_size:
                    break
                stream_offset, page_number, page_id = struct.unpack('>QQQ', data)
                entries.append((stream_offset, page_id, page_number))
        return entries

    def _group_index_entries(self, entries):
        """
        Helper to group index entries by offset and return ordered offsets.
        """
        offset_groups = defaultdict(list)
        for offset, article_id, _ in entries:
            offset_groups[int(offset)].append(article_id)
        sorted_offsets = [int(offset) for offset, _, _ in entries]
        seen_offsets = set()
        ordered_offsets = []
        for o in sorted_offsets:
            if o not in seen_offsets:
                ordered_offsets.append(o)
                seen_offsets.add(o)
        return offset_groups, ordered_offsets

    def list_articles_by_index(self, start: int = 0, count: int = 1) -> list:
        """
        For a given starting index, return a list of (title, text) tuples for the corresponding articles from the dump.
        index_type: 'text' for text index, 'binary' for binary index.
        """
        if self.index_type == 'binary':
            entries = self.list_binary_index_entries(start, count)
        else:
            entries = self.list_index_entries(start, count)
        if not entries:
            return []
        offset_groups, ordered_offsets = self._group_index_entries(entries)
        results = []
        with open(self.xml_bz2_path, 'rb') as infile:
            for offset in ordered_offsets:
                infile.seek(offset)
                decompressor = bz2.BZ2Decompressor()
                uncompressed_data = b""
                while True:
                    chunk = infile.read(262144)
                    if not chunk:
                        break
                    try:
                        uncompressed_data += decompressor.decompress(chunk)
                    except EOFError:
                        break
                    if decompressor.eof:
                        break
                try:
                    xml_text = uncompressed_data.decode('utf-8', errors='replace')
                    xml_text = f'<root>{xml_text}</root>'
                    root = ET.fromstring(xml_text)
                    wanted_ids = [aid for aid in offset_groups[offset]]
                    idx = 0
                    for page in root.findall('page'):
                        page_id_text = page.find('id').text if page.find('id') is not None else None
                        try:
                            page_id = int(page_id_text)
                        except Exception:
                            continue
                        if page_id == wanted_ids[idx]:
                            title = page.find('title').text if page.find('title') is not None else ''
                            revision = page.find('revision')
                            text = ''
                            if revision is not None:
                                text_elem = revision.find('text')
                                if text_elem is not None:
                                    text = text_elem.text or ''
                                    wikicode = mwparserfromhell.parse(text)
                                    text = wikicode.strip_code()
                            results.append((title, text))
                            idx += 1
                            if idx >= len(wanted_ids):
                                break
                except Exception:
                    continue
        return results

    def reindex_multistream(self, output_index_path: str, progress: bool = True) -> int:
        """
        Rebuild the multistream index file from the XML dump.
        Writes a new binary index file. Each entry is three 64-bit unsigned ints:
        - stream_offset (file offset of the bzip2 stream)
        - page_number (number of the page within the stream, starting from 0)
        - page_id (as integer)
        Returns the total number of output entries written.
        """
        line_count = 0
        with open(self.xml_bz2_path, 'rb') as infile, open(output_index_path, 'wb') as outfile:
            while True:
                stream_offset = infile.tell()
                decompressor = bz2.BZ2Decompressor()
                uncompressed_data = b""
                unused = b""
                while True:
                    chunk_offset = infile.tell()
                    chunk = infile.read(262144)
                    if not chunk:
                        break
                    try:
                        data = decompressor.decompress(chunk)
                        uncompressed_data += data
                        if decompressor.eof:
                            unused = decompressor.unused_data
                            break
                    except EOFError:
                        break
                if not uncompressed_data:
                    break
                try:
                    xml_text = uncompressed_data.decode('utf-8', errors='replace')
                    xml_text = f'<root>{xml_text}</root>'
                    root = ET.fromstring(xml_text)
                    page_number = 0
                    for page in root.findall('page'):
                        page_id_text = page.find('id').text if page.find('id') is not None else ''
                        # Filter out redirects
                        is_redirect = page.find('redirect') is not None
                        if is_redirect:
                            continue
                        # Filter out unwanted namespaces by title prefix (case-insensitive)
                        title = page.find('title').text if page.find('title') is not None else ''
                        lower_title = title.lower()
                        unwanted_prefixes = (
                            'template:', 'module:', 'file:', 'talk:', 'user:', 'mediawiki:'
                        )
                        if lower_title.startswith(unwanted_prefixes):
                            continue
                        try:
                            page_id = int(page_id_text)
                        except Exception:
                            print(f"Invalid page ID: {page_id_text}")
                            continue
                        entry = struct.pack('>QQQ', stream_offset, page_number, page_id)
                        outfile.write(entry)
                        line_count += 1
                        page_number += 1
                        if progress and line_count % 1000 == 0:
                            print(f"Processed {line_count} entries...", end='\r')
                except Exception:
                    pass
                # If there was unused data, move the file pointer back so the next stream starts at the correct place
                if unused:
                    infile.seek(chunk_offset + len(chunk) - len(unused))
                if not chunk:
                    break
        return line_count

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == '--reindex':
        xml_bz2_path = sys.argv[2]
        output_index_path = sys.argv[3]
        reader = WikipediaMultistreamReader(xml_bz2_path, None)
        lines = reader.reindex_multistream(output_index_path)
        print(f"Reindexing complete. {lines} lines written to {output_index_path}")
    else:
        pass