import os

from dotenv import load_dotenv

from src.logger import get_logger
from src.load_configs import load_configs, save_configs
from src.frame_utils import frame_to_timestamp, timestamp_to_frame
from src.subtitles import get_subtitle_for_frame
from src.message import format_message



logger = get_logger(__name__)
load_dotenv(".env")






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
    EPISODE_TOTAL_FRAMES     = EPISODES.get(CURRENT_EPISODE, {}).get("frames", 0) # total frames in the episode

    POST_MSG = CONFIGS.get("post_msg", "")

    
    for i in range(PREV_FRAME + 1, LAST_FRAME + 1):
        print(f"Posting frame {i} of {EPISODE_TOTAL_FRAMES}")

        # baixar o frame
        # salvar o frame e pegar o path

        # pegar o subtitle do frame
        # subtitle aqui


        # formatar a mensagem
        placeholders = {
            "season": SEASON,
            "episode": CURRENT_EPISODE,
            "frame": i,
            "total_frames": EPISODE_TOTAL_FRAMES,
            "timestamp": frame_to_timestamp(i, IMG_FPS),
            #"subtitles": SUBTITLES,
        }
        message = format_message(POST_MSG, placeholders)

        # postar o frame com a mensagem
        

        # usar o id de resposta do post pra postar as legendas no comentarios
        # usar o id de resposta do post pra postar o random crop no comentarios






    # atualizar o biografia do facebook com o numero de frames postados
    # update_facebook_bio(CONFIGS)
    




    


    














if __name__ == "__main__":
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n",  flush=True) # makes visualization better in CI/CD environments
    main()
    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 +"\n\n",  flush=True) # makes visualization better in CI/CD environments
