import pythonmonkey as pm
import os

# 1. Read the content of the JavaScript file
def read_js_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

bcv_parser_code = read_js_file('../bible-scraper/utilities/openbibleinfo/en_bcv_parser.js')

pm.eval(bcv_parser_code)
pm.eval("bcv = new bcv_parser()")
pm.eval('bcv.set_options({ "consecutive_combination_strategy": "separate", "osis_compaction_strategy": "bc", "sequence_combination_strategy": "separate" });')

bcv = "Matthew 4:1-5:18"
pm.eval(f"bcv_parsed_entities = bcv.parse('{bcv}').parsed_entities();")
pm.eval("""
bcv_parsed_entities.map(entity => {
    return {
        osis: entity.osis,
        indices: entity.indices,
        book: entity.start ? entity.start.b : null,
        chapter_start: entity.start ? entity.start.c : null,
        chapter_end: entity.end ? entity.end.c : null,
        verse_start: entity.start ? entity.start.v : null,
        verse_end: entity.end ? entity.end.v : null
    };
});
""")
