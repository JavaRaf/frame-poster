import time

from src.frame_utils import frame_to_timestamp, get_frame, timestamp_to_frame
from src.load_configs import load_configs, save_configs
from src.logger import get_logger
from src.message import format_message
# Reuse the single FacebookAPI instance created in poster.py instead of
# spinning up a second client/token load just for repost/update_bio/save_log.
from src.poster import fb, post_frame, post_random_crop, post_subtitles
from src.subtitles import get_subtitle_for_frame
from src.workflow import get_workflow_execution_interval

logger = get_logger(__name__)




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
        logger.error(
            "Episode %s has no entry in configs.yml (episodes: section). "
            "Check in_progress.episode and the episodes mapping.",
            CURRENT_EPISODE,
        )
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
            # exc_info removed: we're not inside an except block, so attaching
            # a traceback would just log "NoneType: None" noise.
            logger.info("Episode %s completed; advancing to episode %s", CURRENT_EPISODE, CURRENT_EPISODE + 1)
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
            # get_frame already logged the HTTP/network cause; this line just
            # signals the main loop gave up on this cycle.
            logger.error("Aborting cycle: could not download frame %s of episode %02d", frame_number, CURRENT_EPISODE)
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
            logger.error(
                "Aborting cycle: empty message after formatting for frame %s of episode %02d",
                frame_number, CURRENT_EPISODE,
            )
            break

        # postar o frame com a mensagem (placeholders apenas para formatar a mensagem no terminal)
        post_id = post_frame(message, frame_path, placeholders)
        if not post_id:
            # post_frame already logged the Graph API response, so just note the loop is stopping.
            logger.error("Aborting cycle: frame %s of episode %02d was not posted", frame_number, CURRENT_EPISODE)
            break

        
        # update progress after each successful post
        IN_PROGRESS["episode"]  = CURRENT_EPISODE
        IN_PROGRESS["frame"]    = frame_number
        CONFIGS["in_progress"]  = IN_PROGRESS
        save_configs(CONFIGS)
    
        
        fb.repost_frame_to_album(message, frame_path, ALBUM_ID, CONFIGS)
        

        # usar o id de resposta do post pra postar as legendas no comentarios
        post_subtitles(post_id, frame_number, CURRENT_EPISODE, subtitles, CONFIGS)
        # usar o id de resposta do post pra postar o random crop no comentarios
        post_random_crop(post_id, frame_path, CONFIGS)


        

        # salva o id do post em um formato https://facebook.com/{id} criando um link direto para o post
        fb.save_fb_log(post_id, frame_number, CURRENT_EPISODE)

        print(f"{'-' * 50}\n\n") # makes visualization better in CI/CD environments
        time.sleep(POSTING_INTERVAL * 60) # wait for the next posting interval



    # atualizar a biografia do facebook com informações relevantes
    BIOGRAPHY_MESSAGE = format_message(BIO_MSG, placeholders)
    # update_bio already logs the HTTP status + response body, so no extra log here.
    fb.update_bio(BIOGRAPHY_MESSAGE)
    

    



    
    


    



if __name__ == "__main__":
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n",  flush=True) # makes visualization better in CI/CD environments
    main()
    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 +"\n\n",  flush=True) # makes visualization better in CI/CD environments
