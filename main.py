import os
import time

from dotenv import load_dotenv

from src.facebook import FacebookAPI
from src.frame_utils import frame_to_timestamp, get_frame, timestamp_to_frame
from src.load_configs import load_configs, save_configs
from src.logger import get_logger
from src.message import format_message
from src.poster import next_episode, post_frame, post_random_crop, post_subtitles
from src.subtitles import get_subtitle_for_frame
from src.workflow import get_workflow_execution_interval

logger = get_logger(__name__)
facebook = FacebookAPI(api_version="v21.0")




def main():

    CONFIGS          = load_configs()
    IN_PROGRESS      = CONFIGS.get("in_progress", {})
    POSTING          = CONFIGS.get("posting", {})
    EPISODES         = CONFIGS.get("episodes", {})
    GITHUB           = CONFIGS.get("github", {})

    SEASON           = IN_PROGRESS.get("season", 1) # current season
    CURRENT_EPISODE  = IN_PROGRESS.get("episode", 1) # 
    IMG_FPS          = EPISODES.get(CURRENT_EPISODE, {}).get("image_fps", 3.5) # frames per second of the image/video
    PREV_FRAME       = IN_PROGRESS.get("frame", 0) # last frame posted
    


    FPH                      = POSTING.get("fph", 15)  
    POSTING_INTERVAL         = POSTING.get("posting_interval", 2) # interval between posts in minutes (recomended: 2 or more) 
 
    LAST_FRAME               = PREV_FRAME + FPH  
    MAX_FRAMES               = EPISODES.get(CURRENT_EPISODE, {}).get("max_frames", 0) # total frames in the episode

    ALBUM_ID                 = EPISODES.get(CURRENT_EPISODE, {}).get("album_id", None)
    EPISODE_TITLE            = EPISODES.get(CURRENT_EPISODE, {}).get("title", None)
    POST_MSG                 = CONFIGS.get("post_msg", "")
    BIO_MSG                  = CONFIGS.get("bio_msg", "")   
    EXECUTION_INTERVAL       = get_workflow_execution_interval()


    placeholders = {
        "season_number": SEASON,
        "episode_number": CURRENT_EPISODE,
        "episode_title": EPISODE_TITLE,
        "max_frames": MAX_FRAMES,
        "img_fps": IMG_FPS,
        "execution_interval": EXECUTION_INTERVAL,
    }

    
    for frame_number in range(PREV_FRAME + 1, LAST_FRAME + 1):
        # se o frame for maior que o total de frames no episodio, pula para o proximo episodio
        if frame_number > MAX_FRAMES: 
            next_episode(CONFIGS)
            break

        # baixar o frame
        frame_path = get_frame(frame_number, CURRENT_EPISODE, GITHUB)
        if not frame_path:
            logger.error(f"Error while downloading frame {frame_number} from episode {CURRENT_EPISODE:02d}.")
            break
        
        # pegar o subtitle do frame
        subtitles = get_subtitle_for_frame(frame_number, CURRENT_EPISODE, IMG_FPS)

        # formatar a mensagem do post
        placeholders.update({
            "frame_number": frame_number,
            "timestamp": frame_to_timestamp(frame_number, IMG_FPS),
            "subtitles": subtitles or "",
        })
        message = format_message(POST_MSG, placeholders)

        if not message:
            logger.error(f"Error while formatting message for frame {frame_number} from episode {CURRENT_EPISODE:02d}.")
            break

        # postar o frame com a mensagem (placeholders apenas para formatar a mensagem no terminal)
        post_id = post_frame(message, frame_path, placeholders)
        if not post_id:
            logger.error(f"After several attempts, it was not possible to post frame {frame_number} of episode {CURRENT_EPISODE:02d}.")
            break

        # usar o id de resposta do post pra postar as legendas no comentarios
        post_subtitles(post_id, frame_number, CURRENT_EPISODE, subtitles, CONFIGS)
        # usar o id de resposta do post pra postar o random crop no comentarios
        post_random_crop(post_id, frame_path, CONFIGS)


        # savar o log do post no arquivo log.txt
        facebook.save_fb_log(post_id, frame_number, CURRENT_EPISODE)

        print(f"{'-' * 50}\n\n") # makes visualization better in CI/CD environments


        





    # atualizar a biografia do facebook com informações relevantes
    BIOGRAPHY_MESSAGE = format_message(BIO_MSG, placeholders)
    if not facebook.update_bio(BIOGRAPHY_MESSAGE):
        logger.error("Failed to update bio")
        return
    
    


    














if __name__ == "__main__":
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n",  flush=True) # makes visualization better in CI/CD environments
    main()
    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 +"\n\n",  flush=True) # makes visualization better in CI/CD environments
