import argparse
import logging
import os

from pdfcomparator.pdf_comparator import compare_pdf

def _parser(parser):
    parser.add_argument('file1', type=str)
    parser.add_argument('file2', type=str)
    parser.add_argument('output_folder', type=str)
    parser.add_argument(
        '--log-dir', '--cache', '-c',
        dest='log_dir',
        help='directory used to write the CLI log file (legacy alias: --cache)',
        default=None,
    )
    
def _execute(args):
    file1 = args.file1
    file2 = args.file2
    output_folder = args.output_folder
    _init_logging(args.log_dir)
    compare_pdf(file1, file2, output_folder)

def _init_logging(log_dir: str):
    if not log_dir:
        log_dir = os.getcwd()
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(log_dir, 'app.log'),
        filemode='w', 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args():
    parser = argparse.ArgumentParser(description="Compare two PDF files and write visual diff results.")
    _parser(parser)
    args = parser.parse_args()
    _execute(args)
