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

    last_headers = {"h0": None, "h2": None, "h3": None, "h4": None}

    rendered_chapter = None
    rendered_verse = None
    is_first_span_in_para = True
    is_first_p = True

    for row in rows:
        book_db = row['book']
        chapter_db = row['chapter']
        v_start_db = row['verse_start']
        v_end_db = row['verse_end']
        h3, h2, h4, h0 = row['h3'], row['h2'], row['h4'], row['h0']
        path = row['path'] or ""
        class_attr = row['class_attr'] or ""
        span_text = row['span_text'] or ""
        span_id = row['span_id'] or ""
        para_md5 = row['para_md5']

        # Reset headers if chapter changes to ensure they reappear if needed (though usually they only appear at start)
        if rendered_chapter is not None and chapter_db != rendered_chapter:
            last_headers = {"h0": None, "h2": None, "h3": None, "h4": None}

        # Identify NEW headers in this row
        new_headers = []
        for h_key in ["h0", "h2", "h3", "h4"]:
            h_val = row[h_key]
            if h_val and h_val != last_headers[h_key]:
                # PREFERENCE: If the path already contains this header tag (e.g. h4.title),
                # we skip rendering the column-based header to avoid duplication.
                tag_type = h_key if h_key != "h0" else "h1"
                header_in_path = (path == tag_type or path.startswith(f"{tag_type}.") or 
                                 f"->{tag_type}." in path or f"->{tag_type}->" in path or path.endswith(f"->{tag_type}"))
                if header_in_path:
                    last_headers[h_key] = h_val
                    continue

                new_headers.append((h_key, h_val))
                last_headers[h_key] = h_val

        if new_headers:
            while current_path_tags:
                res_html.append(current_path_tags.pop()[1])
            current_para_md5 = None
            
            if len(new_headers) > 1:
                res_html.append('<hgroup style="margin-top: 20px; margin-bottom: 15px;">')
            
            for h_tag, h_val in new_headers:
                tag = h_tag if h_tag != "h0" else "h1"
                h_class = ' class="canto"' if h_tag == "h4" and translation == "ScottishPsalter" else ""
                style = ' style="margin-top: 20px; margin-bottom: 10px;"' if len(new_headers) == 1 else ""
                res_html.append(f'<{tag}{h_class}{style}>{h_val}</{tag}>')
                
            if len(new_headers) > 1:
                res_html.append('</hgroup>')

        path = row['path']
        class_attr = row['class_attr']
        span_text = row['span_text'] or ""
        span_id = row['span_id'] or ""
        para_md5 = row['para_md5']

        # Determine if this row is JUST a title (to avoid duplication in standard translations)
        is_title_row = False
        # If the path itself is a header, then this span IS the header, so we always render it.
        # However, column headers like h3/h4 are often duplicates of what's in span_text.
        path_is_header = any(h in path for h in ["h0", "h1", "h2", "h3", "h4"])
        if span_text and not path_is_header:
            for h_val in last_headers.values():
                if h_val == span_text:
                    is_title_row = True
                    break
        
        if is_title_row:
            # Skip rendering the span if it just repeats a header
            continue

        target_tags = path.split('->') if path else []

        if para_md5 != current_para_md5:
            while current_path_tags:
                res_html.append(current_path_tags.pop()[1])
            current_para_md5 = para_md5
            is_first_span_in_para = True

        just_added_br = False
        if "poetry" in path and not is_first_span_in_para:
            res_html.append("<br>")
            just_added_br = True

        common_count = 0
        for i in range(min(len(current_path_tags), len(target_tags))):
            if current_path_tags[i][0] == target_tags[i]:
                common_count += 1
            else:
                break

        while len(current_path_tags) > common_count:
            res_html.append(current_path_tags.pop()[1])

        newly_opened_levels = []
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
                    newly_opened_levels.append(int(level_match.group(1)))

        span_id_attr = f' id="{span_id}"' if span_id else ""

        prefix = ""
        # Number the FIRST non-title row of the verse/chapter
        if not path_is_header:
            if (chapter_db != rendered_chapter or v_start_db != rendered_verse):
                rendered_chapter = chapter_db
                rendered_verse = v_start_db
                verse_label = str(v_start_db) if v_start_db == v_end_db else f"{v_start_db}-{v_end_db}"

                if v_start_db == 1:
                    prefix = f'<span class="chapternum">{chapter_db}&nbsp;</span>'
                else:
                    prefix = f'<sup class="versenum">{verse_label}&nbsp;</sup>'

        # Identify indents to apply to this row
        breaks_html = ""
        needed_levels = []
        if is_first_span_in_para or just_added_br:
            # Apply all currently active indents at the start of a line/paragraph
            for tag_str in target_tags:
                if "span.indent-" in tag_str:
                    m = re.search(r'indent-(\d+)', tag_str)
                    if m:
                        level = int(m.group(1))
                        if level not in needed_levels:
                            needed_levels.append(level)
        else:
            # Otherwise, only apply levels that were newly opened in this row
            needed_levels = newly_opened_levels

        for level in needed_levels:
            spaces = "&nbsp;" * (level * 4)
            breaks_html += f'<span class="indent-{level}-breaks">{spaces}</span>'

        span_html = f"<span{span_id_attr} class=\"{class_attr}\">{prefix}{breaks_html}{span_text}</span>"
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
