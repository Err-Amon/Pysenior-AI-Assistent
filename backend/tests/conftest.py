import os

os.environ.setdefault("GITHUB_TOKEN", "test_github_token")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test_secret")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("MAX_FILE_SIZE_KB", "500")
