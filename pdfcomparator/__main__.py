import sys
import platform
from pdfcomparator.pdf_comparator_cmd import parse_args


def main() -> None:
    if sys.version_info < (3, 8):
        print(f"What requires Python 3.8+, you are using {platform.python_version()}. Please install a higher Python version.")
        sys.exit(1)
    parse_args()

if __name__ == "__main__":
    main()