CONFIG = {
    "region": "all",
    "days": 10,
    "keywords": ["робот", "робототехника"],
    "exclude_words": []
}


def get_config():
    return CONFIG


def set_config(region=None, days=None, keywords=None, exclude_words=None):

    if region:
        CONFIG["region"] = region

    if days:
        CONFIG["days"] = days

    if keywords:
        CONFIG["keywords"] = keywords

    if exclude_words is not None:
        CONFIG["exclude_words"] = exclude_words


def print_config():
    print("\n📌 CONFIG:")
    print(CONFIG)