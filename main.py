import os

from dotenv import load_dotenv

from src.logger import get_logger

load_dotenv(".env")
logger = get_logger(__name__)














def main():
    print(os.getenv("FB_TOKEN"))












if __name__ == "__main__":
    main()