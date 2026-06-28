from config import get_config, print_config
from pipeline.runner import run_pipeline
import os

token = os.getenv("GIGACHAT_TOKEN")

if __name__ == "__main__":

    print_config()

    config = get_config()

    run_pipeline(config, token)