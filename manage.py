import os
import sys
from django.core.management import execute_from_command_line
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "video2text.settings")

def main():
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
