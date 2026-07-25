import os

from ruamel.yaml import CommentedMap
from src.facebook import ApiVersion, FacebookGraphAPI
from src.load_configs import load_and_validate
from src.summary_step import start_summary, add_summary_row, end_summary, Status
from src.logger import get_logger, set_timezone_offset
from src.console import parse_args
from dotenv import load_dotenv


logger = get_logger(__name__)
load_dotenv()


def main(argv: list[str] | None = None) -> None:
    """main function"""
    args = parse_args(argv)

    if args.fb_token:
        os.environ["FB_TOKEN"] = args.fb_token.strip()

    config: CommentedMap = load_and_validate()
    set_timezone_offset(config.get("timezone", 0))

    facebook_client = FacebookGraphAPI(
        access_token=os.environ["FB_TOKEN"], api_version=config.get("api_version", ApiVersion.V25_0)
    )

    start_summary()
    status, reson = facebook_client.validate_token()
    if not status:
        add_summary_row("FB_TOKEN", f"invalid or expired: {reson}", Status.ERROR)
        logger.error(f"Facebook token validation failed: {reson}")
        return

    add_summary_row("FB_TOKEN", "found and validated successfully", Status.SUCCESS)
    end_summary()


if __name__ == "__main__":
    main()
