import os
import pytest

from easyams import web_api

def test_copy_conf():

    conf_out_dir = "tests/outputs/docs/"

    conf_file = os.path.join( conf_out_dir, "conf.py")

    if not os.path.exists(conf_out_dir):
        os.makedirs(conf_out_dir)
    # clear cache conf.py
    if os.path.exists(conf_file):
        os.remove(conf_file)

    web_api.copy_sphinx_config(conf_out_dir)

    assert os.path.exists( conf_file )

def test_build_sphinx_html():

    source_dir = "tests/outputs/docs/"
    build_dir = os.path.join(source_dir, "_build")

    index_rst = os.path.join( source_dir, "index.rst" ) 
    os.remove(index_rst)
    with open(index_rst, 'w', encoding='utf-8') as f:
        f.write(".. EasyAMS documentation test file\n\n")
        f.write("Welcome to EasyAMS's documentation!\n")
        f.write("===================================\n\n")

    web_api.build_sphinx_html(source_dir, build_dir, rebuild=True)

    assert os.path.exists( os.path.join( build_dir, "html", "index.html") )

def test_load_pdf():
    pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
    test_pdf = web_api.MetashapePDFParser(pdf_path)

    assert test_pdf.page_count == 357

def test_get_page_block_content():
    pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
    test_pdf = web_api.MetashapePDFParser(pdf_path)

    header_bottom = 46
    footer_top = 742

    # using the copyright page as testing
    page = test_pdf.doc[4]
    blocks = page.get_text("dict")["blocks"]

    assert len(blocks) == 3

    assert test_pdf.get_block_lines(blocks[0]) == "Metashape Python Reference, Release 2.2.1"
    assert test_pdf.get_block_lines(blocks[1]) == "Copyright (c) 2025 Agisoft LLC."
    assert test_pdf.get_block_lines(blocks[2]) == "CONTENTS"

    keeped_blocks = test_pdf.get_page_block_content(page, header_bottom, footer_top)

    assert len(keeped_blocks) == 1
    assert test_pdf.get_block_lines(keeped_blocks[0]) == "Copyright (c) 2025 Agisoft LLC."

    # using the next page, empty contents with only header and footer
    page = test_pdf.doc[5]
    blocks = page.get_text("dict")["blocks"]

    assert len(blocks) == 2

    assert test_pdf.get_block_lines(blocks[0]) == "Metashape Python Reference, Release 2.2.1"
    assert test_pdf.get_block_lines(blocks[1]) == "2"
    # not sure why "CONTENTS" footer missing

    keeped_blocks = test_pdf.get_page_block_content(page, header_bottom, footer_top)

    assert len(keeped_blocks) == 0

def test_parse_heading_page():
    pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
    test_pdf = web_api.MetashapePDFParser(pdf_path)

    test_pdf.parse_heading_page()

    assert test_pdf.heading_info['title']   == "Metashape Python Reference"
    assert test_pdf.heading_info['version'] == "Release 2.2.1"
    assert test_pdf.heading_info['company'] == "Agisoft LLC"
    assert test_pdf.heading_info['date']    == "Apr 26, 2025"

    assert test_pdf.next_read_page == 1

    test_pdf.parse_copyright_page()

    assert test_pdf.heading_info['copyright']  == "Copyright (c) 2025 Agisoft LLC."

    assert test_pdf.next_read_page == 5

# def test_parse_block_lists():
#     pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
#     test_pdf = web_api.MetashapePDFParser(pdf_path)

#     # Chapter one contents
#     page = test_pdf.doc[6]
#     blocks = test_pdf.get_page_block_content(page, test_pdf.header_bottom, test_pdf.footer_top)

#     block_content = test_pdf.parse_block(blocks)

def test_parse_chapter_one_block_iterator():
    pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
    test_pdf = web_api.MetashapePDFParser(pdf_path)

    cp1_block_iter = test_pdf.parse_one_chapter_blocks(
        start_content="CHAPTER ONE", stop_content="CHAPTER TWO"
    )

    for block in cp1_block_iter:
        lines = test_pdf.get_block_lines(block) 
        print( f">>> {lines}" )

        if len(lines) < 5:
            print("block:", block)

    print("End testing print")