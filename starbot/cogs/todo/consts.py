from typing import Any, Dict, Final

__all__ = ["__author__", "__suggestors__", "__version__", "config_structure"]

__suggestors__ = ["Rosie"]
config_structure: Final[Dict[str, Any]] = {
    "todos": [],  # List[Dict[str, Any]] "task": str, "pinned": False
    "completed": [],  # List[str]
    "managers": [],  # List[int] Discord member id's
    "user_settings": {
        "autosorting": False,
        "colour": None,
        "combine_lists": False,
        "completed_emoji": None,
        "completed_category_emoji": None,
        "extra_details": False,
        "number_todos": True,
        "pretty_todos": False,
        "private": False,
        "reverse_sort": False,
        "todo_emoji": None,
        "todo_category_emoji": None,
        "use_embeds": True,
        "use_markdown": False,
        "use_timestamps": False,
    },
}
