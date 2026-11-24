import os
import re
import pwd
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def get_topic_file():
    username = os.environ.get("SUDO_USER")

    if username:
        home = Path(pwd.getpwnam(username).pw_dir)
    else:
        home = Path.home()

    return home / ".config/neurodrive/ntfy_topic"


def send_notification(title, message, priority=4, tags="warning"):
    topic_file = get_topic_file()

    if not topic_file.exists():
        raise RuntimeError(f"Topic file not found: {topic_file}")

    topic = topic_file.read_text().strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", topic):
        raise ValueError("Invalid ntfy topic")

    request = Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": str(priority),
            "Tags": tags,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print("Notification error:", exc)
        return False
