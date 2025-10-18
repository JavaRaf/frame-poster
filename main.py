import os
import time


from src.facebook import FacebookAPI
from src.frame_utils import frame_to_timestamp, get_frame, timestamp_to_frame
from src.load_configs import load_configs, save_configs
from src.logger import get_logger
from src.message import format_message
from src.poster import post_frame, post_random_crop, post_subtitles
from src.subtitles import get_subtitle_for_frame
from src.workflow import get_workflow_execution_interval

logger = get_logger(__name__)
facebook = FacebookAPI(api_version="v21.0")




def main():

    CONFIGS                  = load_configs()
    IN_PROGRESS              = CONFIGS.get("in_progress", {})
    POSTING                  = CONFIGS.get("posting", {})
    EPISODES                 = CONFIGS.get("episodes", {})
    GITHUB                   = CONFIGS.get("github", {})



    SEASON                   = IN_PROGRESS.get("season", 1) # current season
    CURRENT_EPISODE          = IN_PROGRESS.get("episode", 1)
    PREV_FRAME               = IN_PROGRESS.get("frame", 0) # last frame posted
    CURRENT_EPISODE_ATTRS    = EPISODES.get(CURRENT_EPISODE, {}) # attributes of the current episode

    # validate if the current episode is configured and not empty
    if not CURRENT_EPISODE_ATTRS:
        logger.error(f"Current episode ({CURRENT_EPISODE}) is not configured or empty")
        return

    IMG_FPS                  = CURRENT_EPISODE_ATTRS.get("image_fps", 3.5) # frames per second of the image/video (necessary to know when to stop posting)
    ALBUM_ID                 = CURRENT_EPISODE_ATTRS.get("album_id", None)
    EPISODE_TITLE            = CURRENT_EPISODE_ATTRS.get("title", None)
    MAX_FRAMES               = CURRENT_EPISODE_ATTRS.get("max_frames", 0) # total frames in the episode (necessary to know when to stop posting)

    FPH                      = POSTING.get("fph", 15)  # frames per hour (necessary to know when to stop posting)
    LAST_FRAME               = PREV_FRAME + FPH  # last frame to post


    POST_MSG                 = CONFIGS.get("post_msg", "")
    BIO_MSG                  = CONFIGS.get("bio_msg", "")   
    EXECUTION_INTERVAL       = get_workflow_execution_interval()
    POSTING_INTERVAL         = POSTING.get("posting_interval", 2) # interval between posts in minutes (recomended: 2 or more) 



    # placeholders for the message
    placeholders = {
        "season_number": SEASON,
        "episode_number": CURRENT_EPISODE,
        "episode_title": EPISODE_TITLE,
        "max_frames": MAX_FRAMES,
        "img_fps": IMG_FPS,
        "fph": FPH,
        "execution_interval": EXECUTION_INTERVAL,
        "posting_interval": POSTING_INTERVAL,
    }

    
    for frame_number in range(PREV_FRAME + 1, LAST_FRAME + 1):
        # se o frame for maior que o total de frames no episodio, pula para o proximo episodio
        if frame_number > MAX_FRAMES: 
            logger.info(f"Episode {CURRENT_EPISODE} completed. Moving to next episode.", exc_info=True)
            CURRENT_EPISODE += 1
            
            
            # update configs with new episode and reset frame
            IN_PROGRESS["episode"]  = CURRENT_EPISODE
            IN_PROGRESS["frame"]    = 0
            CONFIGS["in_progress"]  = IN_PROGRESS
            save_configs(CONFIGS)
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

        
        # update progress after each successful post
        IN_PROGRESS["episode"]  = CURRENT_EPISODE
        IN_PROGRESS["frame"]    = frame_number
        CONFIGS["in_progress"]  = IN_PROGRESS
        save_configs(CONFIGS)
    
        
        facebook.repost_frame_to_album(message, frame_path, ALBUM_ID, CONFIGS)
        

        # usar o id de resposta do post pra postar as legendas no comentarios
        post_subtitles(post_id, frame_number, CURRENT_EPISODE, subtitles, CONFIGS)
        # usar o id de resposta do post pra postar o random crop no comentarios
        post_random_crop(post_id, frame_path, CONFIGS)


        

        # salva o id do post em um formato https://facebook.com/{id} criando um link direto para o post
        facebook.save_fb_log(post_id, frame_number, CURRENT_EPISODE)

        print(f"{'-' * 50}\n\n") # makes visualization better in CI/CD environments
        time.sleep(POSTING_INTERVAL * 60) # wait for the next posting interval



    # atualizar a biografia do facebook com informações relevantes
    BIOGRAPHY_MESSAGE = format_message(BIO_MSG, placeholders)
    if not facebook.update_bio(BIOGRAPHY_MESSAGE):
        logger.error("Failed to update bio")
    

    



    
    


    



if __name__ == "__main__":
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n",  flush=True) # makes visualization better in CI/CD environments
    main()
    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 +"\n\n",  flush=True) # makes visualization better in CI/CD environments
