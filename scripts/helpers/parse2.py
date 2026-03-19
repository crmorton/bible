from py_mini_racer import py_mini_racer
import os

# 1. Read the content of the JavaScript file
def read_js_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

bcv_parser_code = read_js_file('../bible-scraper/utilities/openbibleinfo/en_bcv_parser.js')

ctx = py_mini_racer.MiniRacer()

ctx.eval(bcv_parser_code)
ctx.eval("bcv = new bcv_parser()")
ctx.eval("bcv.parse('Matthew 4:1-11').osis();")

bcv = "Matthew 4:1-11"
ctx.eval(f"bcv.parse('{bcv}').osis();")
