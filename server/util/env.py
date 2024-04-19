import os


def get_env(key, default=None):
    return os.environ.get(key, default)
