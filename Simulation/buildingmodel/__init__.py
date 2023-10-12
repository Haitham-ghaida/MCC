# -*- coding: utf-8 -*-

from pathlib import Path

from environs import Env
from pkg_resources import resource_filename


# environ file variable
# Load environment file
BASE_DIR = Path(__file__).parent.expanduser().resolve()
log_dir = BASE_DIR / 'logs'
environ_path = BASE_DIR / ".env"
env = Env()
Env.read_env(environ_path)

# display plots in tests
plot = env.bool("plot", False)

