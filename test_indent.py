
import sys
import os

# Add the current directory to sys.path to import passage
sys.path.append(os.path.abspath('.'))

from bible_api.passage import render_passage_html

def test_indent():
    rows = [
        {
            'book': 'Rom',
            'chapter': 3,
            'verse_start': 16,
            'verse_end': 16,
            'h3': None,
            'h2': None,
            'h4': None,
            'h0': None,
            'path': 'poetry->span.indent-1',
            'class_attr': 'text Rom-3-16',
            'span_text': 'destruction and distress are in their paths,',
            'span_id': 'en-LEB-27991',
            'para_md5': 'para1'
        },
        {
            'book': 'Rom',
            'chapter': 3,
            'verse_start': 17,
            'verse_end': 17,
            'h3': None,
            'h2': None,
            'h4': None,
            'h0': None,
            'path': 'poetry->span.indent-1',
            'class_attr': 'text Rom-3-17',
            'span_text': 'and they have not known the way of peace.',
            'span_id': 'en-LEB-27992',
            'para_md5': 'para1'
        }
    ]
    
    html = render_passage_html(rows, 'LEB')
    print(html)

if __name__ == "__main__":
    test_indent()
