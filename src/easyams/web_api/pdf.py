import os
import time
import requests
from packaging.version import Version

import pymupdf

class PDFDownloader():
    # just manually type the lastest one version
    #    can be obtained from the lastest pdf Chapter 3
    #    {Python API change log}
    last_versions = [
        "2.2.1", # auto generate -> "2.2.0",
        "2.1.4", # auto generate -> "2.1.3", "2.1.2", "2.1.1", "2.1.0",
        "2.0.4",
        "1.8.5",
        "1.7.6",
        "1.6.6",
        "1.5.5",
        # then is named PhotoScan, prefer stop here
        # "1.4.4",
        # "1.3.5",
        # "1.2.6",
        # "1.1.1",
        # "1.0.0",
        # "0.9.1",
        # "0.8.5"
    ]

    def __init__(self, output_dir="pdfs"):
        self.versions = []
        self.get_all_versions()

    def get_all_versions(self):
        for version_str in self.last_versions:
            version_obj = Version(version_str)
            for patch in range(version_obj.micro, -1, -1):
                version_minor = Version(f"{version_obj.major}.{version_obj.minor}.{patch}")
                self.versions.append(version_minor)

    def fetch_one_version(self, version_obj, overwrite=False):
        base_url = "https://www.agisoft.com/pdf/metashape_python_api_"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        ver_str = f"{version_obj.major}_{version_obj.minor}_{version_obj.micro}"
        pdf_url = f"{base_url}{ver_str}.pdf"
        pdf_filename = f"metashape_python_api_{ver_str}.pdf"

        # skip downloading if file exists
        if os.path.exists( os.path.join(self.output_dir, pdf_filename) ) and not overwrite:
            print(":: PDF file already exists")
            return True

        try:
            response = requests.get(pdf_url, stream=True, headers=headers)
            if response.status_code == 200: 
                
                filepath = os.path.join(self.output_dir, pdf_filename)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f":: Successfully downloaded: {pdf_filename}")
                return True
            else:
                response.raise_for_status()
                print(f":: Unexpected status {response.status_code} for {ver_str}")
                return False

        except requests.exceptions.RequestException as e:
            print(f":: Failed to download version {ver_str}: {e}")
            return False
        
    def fetch_all_versions(self):
        for version_obj in self.versions:
            self.fetch_one_version(version_obj)
            time.sleep(3) 

    def cmd_download(self):
        version_str = input(
            f"Available Metashape API documents versions:\n"
            f"{[str(i) for i in self.versions]+['ALL']}\n"
            f"Which version you want to download?\n"
            f">>> ")

        if version_str in ["ALL", 'all', "All", "A"]:
            self.fetch_all_versions()
        elif Version(version_str) in self.versions:
            self.fetch_one_version( Version(version_str) )
        else:
            print(f"Version [{version_str}] is not available")


class MetashapePDFParser():

    def __init__(self, pdf_path):
        self.doc = pymupdf.open(pdf_path)
        self.page_count = self.doc.page_count

        # remove headers and footers outside this range
        self.header_bottom = 46
        self.footer_top = 742

        # chapter infos
        self.heading_info = {}

        self.next_read_page = 0

    def parse_pages(self):
        self.parse_heading_page()
        self.parse_copyright_page()

    def parse_heading_page(self):
        page = self.doc[0]
        blocks = self.get_page_block_content(page, self.header_bottom, self.footer_top)

        self.heading_info["title"]   = self.get_block_lines(blocks[0])
        self.heading_info["version"] = self.get_block_lines(blocks[1])
        self.heading_info["company"] = self.get_block_lines(blocks[2])
        self.heading_info["date"]    = self.get_block_lines(blocks[3])
        
        self.next_read_page += 1

    def parse_copyright_page(self):
        while True:
            page = self.doc[self.next_read_page]
            self.next_read_page += 1

            if self.page_contains(page, "Copyright"):
                blocks = self.get_page_block_content(page, self.header_bottom, self.footer_top)
                self.heading_info['copyright'] = self.get_block_lines(blocks[0])
                return

    def parse_one_chapter_blocks(self, start_content="CHAPTER ONE", stop_content="CHAPTER TWO"):
        # Using Generator to save momory cost
        recording = False
        while True:
            page = self.doc[self.next_read_page]
            print("now_page: ", self.next_read_page)
            self.next_read_page += 1
            
            if self.page_contains(page, start_content):
                recording = True
                
            if self.page_contains(page, stop_content):
                recording = False
                self.next_read_page -= 1
                break

            if recording:
                blocks = self.get_page_block_content(page, self.header_bottom, self.footer_top)

                if len(blocks) > 0:
                    for block in blocks:
                        yield block
                else:
                    # meet the blank page, 
                    # In metashape documents, blank pages means prepare for new chapters
                    # stop reading for this chapter
                    print(f":: Getting blank page with blocks num = {len(blocks)}")
                    recording = False
                    return
                
    @staticmethod
    def get_page_block_content(page, header_y, footer_y):
        blocks = page.get_text("dict")["blocks"]

        keeped_blocks = []
        # remove header and footer
        for block in blocks:
            x0, y0, x1, y1 = block['bbox']

            max_y = max(y0, y1)
            min_y = min(y0, y1)

            if max_y > footer_y or min_y < header_y:
                # footer and header
                continue
            
            keeped_blocks.append(block)

        return keeped_blocks

    @staticmethod
    def get_block_lines(block):
        for line in block["lines"]:
            line_text = ''.join(span["text"] for span in line["spans"])
            return line_text

    @staticmethod
    def page_contains(page, text):
        areas = page.search_for(text)

        if len(areas) > 0:
            return True
        else:
            return False

    def close(self):
        if hasattr(self, "doc") and not self.doc.is_closed:
            self.doc.close()

    def __del__(self):
        self.close()


class BlockParser():
    
    def __init__(self):
        pass

    def parse_block(block_dict):
        """_summary_

        Parameters
        ----------
        block_dict : _type_
            _description_

        Notes
        -----
        Data Structures:
        - ParagraphBlock
            - Text
            - Bold
            - Code
            - Links
        - ListBlock
            - Item
        - CodeBlock
        - NotesBlock

        For each item, we have the following structure >>>
        {
            "type": plaintxt | notes | codes | bold | list | ref 
            "text": pure strings of text, but if mixed, text
        },

        For block item, it have the following structure >>> 
        {
            "type": block,
            "level": 0 - 5
            "child": [] list of each item
        }
        """
        pass
