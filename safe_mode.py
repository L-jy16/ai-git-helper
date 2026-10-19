import re


MAX_FILES = 10
MAX_LINES = 200


# 일부 민감정보 패턴을 대체한다. 모든 종류의 비밀정보를 찾아내는 것은 아니다.
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


# 파일 블록 수와 전체 줄 수 중 어느 한도든 도달하면 이후 내용을 제외한다.
def limit_diff(diff):

    lines = diff.splitlines()

    result = []

    file_count = 0

    for line in lines:

        # diff --git은 파일별 변경 블록의 시작이다. 같은 파일도 블록마다 센다.
        if line.startswith("diff --git"):
            file_count += 1

            if file_count > MAX_FILES:
                break

        result.append(line)

        if len(result) >= MAX_LINES:
            break

    return "\n".join(result)


# 민감정보를 먼저 마스킹한 다음 전송량 제한을 적용한다.
def sanitize_diff(diff):

    diff = mask_sensitive_data(diff)

    diff = limit_diff(diff)

    return diff