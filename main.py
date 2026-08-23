import os

from dotenv import load_dotenv
from ruamel.yaml import CommentedMap

from src.console import parse_args
from src.facebook import ApiVersion, FacebookGraphAPI
from src.load_configs import load_and_validate
from src.logger import get_logger, set_timezone_offset
from src.random_post import random_post
from src.sequencial_post import sequencial_post

# define logger for registre errors in code
logger = get_logger(__name__)

load_dotenv()


def main(argv: list[str] | None = None) -> None:
    """main function"""

    # ---------------------------------------Ambient config---------------------------------------
    # Parse arguments of the command line
    args = parse_args(argv)

    if args.fb_token:
        os.environ["FB_TOKEN"] = args.fb_token.strip()

    config: CommentedMap = load_and_validate()
    set_timezone_offset(config.get("timezone", 0))

    facebook_client = FacebookGraphAPI(
        access_token=os.environ["FB_TOKEN"],
        api_version=config.get("facebook_api_version", ApiVersion.V25_0),
    )

    # ---------------------------------------------------------------------------------------------
    # Validate Facebook token and add to a github action summary
    # start_summary()
    # status, reson = facebook_client.validate_token()
    # if not status:
    #     add_summary_row("FB_TOKEN", f"invalid or expired: {reson}", Status.ERROR)
    #     logger.error(f"Facebook token validation failed: {reson}")
    #     return

    # add_summary_row("FB_TOKEN", "found and validated successfully", Status.SUCCESS)
    # end_summary()

    # ---------------------------------------------------------------------------------------------

    # define if the post will be random or sequential
    post_mode: bool = config.get("posting", {}).get("random_post", False)

    if not post_mode:
        sequencial_post(facebook_client, config)  # follow the order in the config file "progress"

    else:
        random_post(facebook_client, config)  # post random frames


if __name__ == "__main__":
    main()
