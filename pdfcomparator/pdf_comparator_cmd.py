import argparse
import logging
import os

from pdfcomparator.pdf_comparator import compare_pdf

def _parser(parser):
    parser.add_argument('file1', type=str)
    parser.add_argument('file2', type=str)
    parser.add_argument('output_folder', type=str)
    parser.add_argument('--image', action='store_true', help='Compare Image', default=True)
    parser.add_argument('--text', action='store_true', help='Compare Text', default=False)
    parser.add_argument('--cache', '-c', help='cache path', default=None)
    
def _execute(args):
    file1 = args.file1
    file2 = args.file2
    output_folder = args.output_folder
    is_compare_image = args.image
    is_compare_text = args.text
    cache_path = args.cache
    _init_cache_file(cache_path)
    compare_pdf(file1, file2, output_folder, is_compare_image, is_compare_text)

def _init_cache_file(cache_path: str):
    if not cache_path:
        cache_path = os.getcwd()
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        filename=os.path.join(cache_path, 'app.log'),
        filemode='w', 
        # encoding='utf-8',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args():
    parser = argparse.ArgumentParser(description="pdf comparator command line arguments")
    _parser(parser)
    args = parser.parse_known_args()
    _execute(args[0])