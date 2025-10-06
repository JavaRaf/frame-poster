import os

from dotenv import load_dotenv

from src.logger import get_logger
from src.load_configs import load_configs
from src.subtitles import get_subtitle_for_frame



logger = get_logger(__name__)
load_dotenv(".env")



CONFIGS          = load_configs()
SEASON           = CONFIGS.get("in_progress", {}).get("season", 1)
CURRENT_EPISODE  = CONFIGS.get("in_progress", {}).get("episode", 1)
POSTING_INTERVAL = CONFIGS.get("posting", {}).get("posting_interval", 2)
FPH              = CONFIGS.get("posting", {}).get("fph", 15)

# last frame posted
PREV_FRAME = CONFIGS.get("in_progress", {}).get("frame", 0)


def main():
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n",  flush=True) # makes visualization better in CI/CD environments

    for frame_number in range(PREV_FRAME + 1, FPH + 1):
        # baixar a imagem
        # pegar o caminho da imagem
        # pegar a messagem do post

        # pegar o subtitulo
        

        # formatar a mensagem do post
        # postar a imagem

        # postar o subtitulo nos comentarios se o posting_subtitles for true


        # postar o random crop se o random_crop for true


    
    # atualizar o biografia do facebook com o numero de frames postados
    # update_facebook_bio(CONFIGS)
    

    # atualizar o in_progress
    # update_in_progress(CONFIGS)


    















    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 +"\n\n",  flush=True) # makes visualization better in CI/CD environments














if __name__ == "__main__":
    main()