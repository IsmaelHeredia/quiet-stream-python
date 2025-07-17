#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

def clean_emoji_from_string(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "\u200d"
        "\ufe0f"
        "]+", flags=re.UNICODE
    )
    cleaned_text = emoji_pattern.sub(r'', text).strip()
    return cleaned_text