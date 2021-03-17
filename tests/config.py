import configparser
import os

from molotov import global_setup, set_var


@global_setup()
def init_test(args):
    """Setup fixture."""
    env = os.getenv("AUTOPUSH_ENV", "stage")
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.getcwd(), "config.ini")
    config.read(ini_path)
    set_var("config", config[env])
