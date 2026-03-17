"""Passage rendering helper functions."""

import re


def parse_tag(tag_str):
    parts = tag_str.split('.')
    tag_name = parts[0]
    classes = " ".join(parts[1:])
    class_attr = f' class="{classes}"' if classes else ''
    return f"<{tag_name}{class_attr}>", f"</{tag_name}>"


def render_passage_html(rows, translation):
    """Render HTML for a list of verse rows from the database."""

    res_html = []
    current_path_tags = []
    current_para_md5 = None

    rendered_chapter = None
    rendered_verse = None
    is_first_span_in_para = True

    for row in rows:
        book_db = row['book']
        chapter_db = row['chapter']
        v_start_db = row['verse_start']
        v_end_db = row['verse_end']
        h3, h2, h4, h0 = row['h3'], row['h2'], row['h4'], row['h0']
        header_text = h3 or h2 or h4 or h0

        if header_text:
            while current_path_tags:
                res_html.append(current_path_tags.pop()[1])
            current_para_md5 = None

        path = row['path']
        class_attr = row['class_attr']
        span_text = row['span_text'] or header_text
        span_id = row['span_id'] or ""
        para_md5 = row['para_md5']

        target_tags = path.split('->') if path else []

        if para_md5 != current_para_md5:
            while current_path_tags:
                res_html.append(current_path_tags.pop()[1])
            current_para_md5 = para_md5
            is_first_span_in_para = True

        if "poetry" in path and not is_first_span_in_para:
            res_html.append("<br>")

        common_count = 0
        for i in range(min(len(current_path_tags), len(target_tags))):
            if current_path_tags[i][0] == target_tags[i]:
                common_count += 1
            else:
                break

        while len(current_path_tags) > common_count:
            res_html.append(current_path_tags.pop()[1])

        for i in range(common_count, len(target_tags)):
            tag_str = target_tags[i]
            open_tag, close_tag = parse_tag(tag_str)

            if "poetry" in open_tag:
                open_tag = open_tag.replace('>', ' style="margin-top: 15px; margin-bottom: 15px;">')
            elif open_tag.startswith("<p"):
                open_tag = open_tag.replace('>', ' style="margin-bottom: 10px;">')
            elif any(h in open_tag for h in ["<h1", "<h2", "<h3", "<h4"]):
                open_tag = open_tag.replace('>', ' style="margin-top: 20px; margin-bottom: 10px;">')

            res_html.append(open_tag)
            current_path_tags.append((tag_str, close_tag))

            if "span.indent-" in tag_str:
                level_match = re.search(r'indent-(\d+)', tag_str)
                if level_match:
                    level = int(level_match.group(1))
                    spaces = " " * (level * 4)
                    res_html.append(f'<span class="indent-{level}-breaks">{spaces}</span>')

        span_id_attr = f' id="{span_id}"' if span_id else ""

        is_header = bool(header_text) or any(h in path for h in ['h1', 'h2', 'h3', 'h4'])

        prefix = ""
        if not is_header and (chapter_db != rendered_chapter or v_start_db != rendered_verse):
            rendered_chapter = chapter_db
            rendered_verse = v_start_db
            verse_label = str(v_start_db) if v_start_db == v_end_db else f"{v_start_db}-{v_end_db}"

            if v_start_db == 1:
                prefix = f'<span class="chapternum" style="float: left; padding-right: 6px;">{chapter_db}</span>'
            else:
                prefix = f'<sup class="versenum">{verse_label} </sup>'

        span_html = f"<span{span_id_attr} class=\"{class_attr}\">{prefix}{span_text}</span>"
        res_html.append(span_html)

        is_first_span_in_para = False

    while current_path_tags:
        res_html.append(current_path_tags.pop()[1])

    inner_html = "".join(res_html)
    wrapped_html = (
        f'<div class="passage-text">'
        f'<div class="passage-content passage-class-0">'
        f'<div class="version-{translation} result-text-style-normal text-html">'
        f'{inner_html}'
        f'</div></div></div>'
    )
    return wrapped_html
