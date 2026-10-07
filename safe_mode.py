import re


MAX_FILES = 10
MAX_LINES = 200


def mask_sensitive_data(text):

    # 이메일 마스킹
    text = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[MASKED_EMAIL]",
        text
    )

    # 일반적인 API Key / Secret 형태
    text = re.sub(
        r'(?i)(api[_-]?key|secret|token)'
        r'\s*[:=]\s*["\']?'
        r'[A-Za-z0-9_\-]{8,}',
        r'\1=[MASKED_SECRET]',
        text
    )

    return text


def limit_diff(diff):

    lines = diff.splitlines()

    result = []

    file_count = 0

    for line in lines:

        if line.startswith("diff --git"):
            file_count += 1

            if file_count > MAX_FILES:
                break

        result.append(line)

        if len(result) >= MAX_LINES:
            break

    return "\n".join(result)


def sanitize_diff(diff):

    diff = mask_sensitive_data(diff)

    diff = limit_diff(diff)

    return diff