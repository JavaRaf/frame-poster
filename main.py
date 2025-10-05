from src.logger import get_logger
from dotenv import load_dotenv
import os









load_dotenv(".env")
logger = get_logger(__name__)














def main():
    print(os.getenv("FB_TOKEN"))












if __name__ == "__main__":
    main()