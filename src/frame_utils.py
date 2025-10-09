from src.logger import get_logger

logger = get_logger(__name__)





def timestamp_to_frame(timestamp: str, fps: (int, float) = 3.5) -> int | None:
    """
    Converts a timestamp (H:MM:SS.CC) from .ass subtitle format to a frame number.
    Example: "0:01:02.50" → 1 minute, 2.5 seconds → calculated frame.

    Args:
        timestamp (str): Example: "0:01:02.50"
        fps (int, float): Frames per second. Example: 2

    Returns:
        int: Rounded frame number. Or None if error occurs.
    """
    try:
        hours, minutes, seconds = timestamp.split(":")
        seconds, centiseconds = seconds.split(".")
        total_seconds = (
            int(hours) * 3600
            + int(minutes) * 60
            + int(seconds)
            + int(centiseconds) / 100
        )
        return round(total_seconds * fps)
    except Exception as error:
        logger.error(f"Error while converting timestamp '{timestamp}' to frame: {error}", exc_info=True)
        return None


def timestamp_to_seconds(time_str: str) -> float | None:
    """
    Converts a timestamp (H:MM:SS.CC) to total seconds (float).
    Example: "0:01:02.50" → 1 minute, 2.5 seconds → 62.5 seconds.

    Args:
        time_str (str): Example: "0:01:02.50"

    Returns:
        float: Total seconds. Or None if error occurs.
    """
    try:
        h, m, s = time_str.split(":")
        s, cc = s.split(".")
        cc = cc.ljust(2, "0")  # ensure two digits
        total_seconds = (
            int(h) * 3600
            + int(m) * 60
            + int(s)
            + int(cc) / 100
        )
        return total_seconds
    except Exception as error:
        logger.error(f"Error while converting timestamp '{time_str}' to seconds: {error}", exc_info=True)
        return None



def frame_to_timestamp(current_frame: int, img_fps: (int | float)) -> str | None:
    """Converts frame number to timestamp in .ass format (H:MM:SS.CC).

    Args:
        current_frame (int): Current frame number.
        img_fps (int | float): Frames per second of the video.

    Returns:
        str | None: Timestamp in the format 'H:MM:SS.CC', or None if error occurs.
    """

    try:
        total_seconds = current_frame / img_fps

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        centiseconds = int(round((seconds % 1) * 100))
        seconds = int(seconds)

        # Rounding that can generate carry-over (ex: 59.999s -> 1:00.00)
        if centiseconds == 100:
            centiseconds = 0
            seconds += 1
            if seconds == 60:
                seconds = 0
                minutes += 1
                if minutes == 60:
                    minutes = 0
                    hours += 1
        return f"{int(hours)}:{int(minutes):02}:{int(seconds):02}.{centiseconds:02}"
        
    except Exception as error:
        logger.error(f"Error while converting frame to timestamp: {error}", exc_info=True)
        return None
