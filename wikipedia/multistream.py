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
    
    def foreach_article(self, callback, limit: int = 100):
        """
        Iterate over all articles in the given index and call the callback function.
        Reads from the XML dump file are grouped by multistream offset.
        The callback function should accept two arguments: title and text.
        For this implementation, only the first N articles from the index are processed.
        """
        if self.index_type == 'binary':
            entries = self.list_binary_index_entries(0, limit)
        else:
            entries = self.list_index_entries(0, limit)
        if not entries:
            return
        offset_groups, ordered_offsets = self._group_index_entries(entries)
        with open(self.xml_bz2_path, 'rb') as infile:
            for offset in ordered_offsets:
                infile.seek(int(offset))
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
                            callback(title, text)
                            idx += 1
                            if idx >= len(wanted_ids):
                                break
                except Exception:
                    continue

    def find_recursive_articles(self, title: str, output_index_path: str, max_depth: int = 1, max_articles: int = 2000) -> int:
        """
        Find all articles that are recursively linked to the given title.
        Writes a binary index file (output_index_path) with entries for the found articles, sorted by stream_offset and page_number.
        Returns the number of entries written.
        Only uses the text index for all lookups and traversals.
        """
        import struct
        from collections import deque
        
        def extract_links(text):
            wikicode = mwparserfromhell.parse(text)
            return [str(link.title).strip() for link in wikicode.filter_wikilinks()]

        def get_redirect_target(text):
            wikicode = mwparserfromhell.parse(text)
            for template in wikicode.filter_templates():
                if template.name.lower().strip().startswith('redirect'):
                    if template.params:
                        return str(template.params[0].value).strip()
            lines = text.strip().splitlines()
            for line in lines:
                if line.strip().lower().startswith('#redirect'):
                    import re
                    m = re.search(r'\[\[(.*?)\]\]', line, re.IGNORECASE)
                    if m:
                        return m.group(1).strip()
            return None

        print(f"Building title-to-index mapping from {self.index_bz2_path} ...")
        title_to_index = {}
        idx = 0
        with bz2.open(self.index_bz2_path, 'rt', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.strip().split(':', 2)
                if len(parts) == 3:
                    offset, article_id, article_title = parts
                    title_to_index[article_title] = (int(offset), int(article_id), article_title, idx)
                    idx += 1
        print(f"Index loaded: {len(title_to_index)} articles.")
        
        visited = set()
        queue = deque()
        result_titles = []
        def normalize(t):
            return t.replace('_', ' ').strip()
        start_title = normalize(title)
        if start_title not in title_to_index:
            print(f"Start title '{start_title}' not found in index.")
            return 0
        print(f"Starting BFS from '{start_title}' (max_depth={max_depth}, max_articles={max_articles})")
        queue.append((start_title, 0))
        while queue and len(result_titles) < max_articles:
            curr_title, depth = queue.popleft()
            if curr_title in visited:
                continue
            visited.add(curr_title)
            if curr_title not in title_to_index:
                print(f"Title '{curr_title}' not found in index, skipping.")
                continue
            offset, article_id, article_title, index_pos = title_to_index[curr_title]
            print(f"Processing: '{curr_title}' (depth={depth}, idx={index_pos})")
            # Always use text index for lookup
            articles = self.list_index_entries(index_pos, 1)
            if not articles:
                print(f"No index entry for '{curr_title}' at idx={index_pos}")
                continue
            # Get the article text
            article_data = self.list_articles_by_index(index_pos, 1)
            if not article_data:
                print(f"No article data for '{curr_title}' at idx={index_pos}")
                continue
            art_title, art_text = article_data[0]
            # If list_articles_by_index strips the text, re-read the raw text from the dump
            # We'll try to get the raw text from the XML directly
            # Use the text from the revision element, before any stripping
            # We'll re-parse the XML for this article to get the raw text
            entries = self.list_index_entries(index_pos, 1)
            if not entries:
                print(f"No index entry for '{curr_title}' at idx={index_pos}")
                continue
            offset, article_id, article_title = entries[0]
            with open(self.xml_bz2_path, 'rb') as infile:
                infile.seek(int(offset))
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
                    found = False
                    for page in root.findall('page'):
                        page_id_text = page.find('id').text if page.find('id') is not None else None
                        try:
                            page_id = int(page_id_text)
                        except Exception:
                            continue
                        if page_id == article_id:
                            revision = page.find('revision')
                            if revision is not None:
                                text_elem = revision.find('text')
                                if text_elem is not None:
                                    art_text = text_elem.text or ''
                                    found = True
                                    break
                    if not found:
                        print(f"Raw text for '{curr_title}' not found in XML at offset {offset}")
                        continue
                except Exception as e:
                    print(f"Error parsing XML for '{curr_title}': {e}")
                    continue
            redirect_target = get_redirect_target(art_text)
            if redirect_target:
                norm_target = normalize(redirect_target)
                print(f"Redirect: '{curr_title}' -> '{norm_target}'")
                if norm_target not in visited and norm_target in title_to_index:
                    queue.appendleft((norm_target, depth))
                continue
            result_titles.append(curr_title)
            if depth < max_depth:
                links = extract_links(art_text)
                print(f"Links from '{curr_title}': {links}")
                for link in links:
                    norm_link = normalize(link)
                    if norm_link and norm_link not in visited and norm_link in title_to_index:
                        print(f"  Queueing: '{norm_link}' (depth={depth+1})")
                        queue.append((norm_link, depth + 1))
            if len(result_titles) >= max_articles:
                print(f"Reached max_articles limit: {max_articles}")
                break
        # Prepare binary entries from text index data
        found_entries = []
        for t in result_titles:
            offset, article_id, article_title, index_pos = title_to_index[t]
            found_entries.append((offset, index_pos, article_id))
        found_entries.sort(key=lambda x: (x[0], x[1]))
        print(f"Writing {len(found_entries)} entries to {output_index_path} ...")
        with open(output_index_path, 'wb') as outfile:
            for stream_offset, page_number, page_id in found_entries:
                outfile.write(struct.pack('>QQQ', stream_offset, page_number, page_id))
        print(f"Done. {len(found_entries)} entries written.")
        return len(found_entries)

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
    elif len(sys.argv) == 6 and sys.argv[1] == '--find':
        xml_bz2_path = sys.argv[2]
        xml_bz2_index_path = sys.argv[3]
        output_index_path = sys.argv[4]
        reader = WikipediaMultistreamReader(xml_bz2_path, xml_bz2_index_path)
        reader.index_type = 'text'
        lines = reader.find_recursive_articles(sys.argv[5], output_index_path, 2)
        print(f"Found {lines} lines written to {output_index_path}")
