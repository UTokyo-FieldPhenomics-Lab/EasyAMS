import pytest

from easyams import web_api

@pytest.fixture
def prepare_test_pdf():
    pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
    test_pdf = web_api.PDFParser(pdf_path)

    return test_pdf

def test_load_pdf():
    pdf_path = "tests/pdfs/metashape_python_api_2_2_1.pdf"
    test_pdf = web_api.PDFParser(pdf_path)

    assert test_pdf.page_count == 357

def test_get_page_block_content(prepare_test_pdf):
    test_pdf = prepare_test_pdf

    header_bottom = 46
    footer_top = 742

    # using the copyright page as testing
    page = test_pdf.doc[4]
    blocks = page.get_text("dict")["blocks"]

    assert len(blocks) == 3

    assert web_api.get_block_lines(blocks[0]) == "Metashape Python Reference, Release 2.2.1"
    assert web_api.get_block_lines(blocks[1]) == "Copyright (c) 2025 Agisoft LLC."
    assert web_api.get_block_lines(blocks[2]) == "CONTENTS"

    keeped_blocks = web_api.get_page_block_content(page, header_bottom, footer_top)

    assert len(keeped_blocks) == 1
    assert web_api.get_block_lines(keeped_blocks[0]) == "Copyright (c) 2025 Agisoft LLC."

    # using the next page, empty contents with only header and footer
    page = test_pdf.doc[5]
    blocks = page.get_text("dict")["blocks"]

    assert len(blocks) == 2

    assert web_api.get_block_lines(blocks[0]) == "Metashape Python Reference, Release 2.2.1"
    assert web_api.get_block_lines(blocks[1]) == "2"
    # not sure why "CONTENTS" footer missing

    keeped_blocks = web_api.get_page_block_content(page, header_bottom, footer_top)

    assert len(keeped_blocks) == 0

def test_parse_heading_page(prepare_test_pdf):
    test_pdf = prepare_test_pdf

    test_pdf.parse_heading_page()

    assert test_pdf.heading_info['title']   == "Metashape Python Reference"
    assert test_pdf.heading_info['version'] == "Release 2.2.1"
    assert test_pdf.heading_info['company'] == "Agisoft LLC"
    assert test_pdf.heading_info['date']    == "Apr 26, 2025"

    assert test_pdf.now_page == 1

    test_pdf.parse_copyright_page()

    assert test_pdf.heading_info['copyright']  == "Copyright (c) 2025 Agisoft LLC."

    assert test_pdf.now_page == 5