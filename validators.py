"""AI 출력의 필수 형식을 검사한다. 의미의 정확성은 사용자가 검토한다."""
import re

SECTIONS = ("## Why", "## What", "## How to Test")


# 첫 줄을 제목으로 검사하고 본문이 있으면 내용 있는 불릿을 요구한다. 빈 목록은 통과다.
def validate_commit(text):
    lines = text.strip().splitlines()
    if not lines:
        return ["커밋 메시지가 비어 있습니다."]
    errors = []
    if len(lines[0].strip()) > 72:
        errors.append("커밋 제목은 최대 72자입니다.")
    body = [line for line in lines[1:] if line.strip()]
    if body and not any(re.match(r"^\s*[-*+]\s+\S", line) for line in body):
        errors.append("커밋 본문은 핵심 변경 사항을 불릿으로 작성하세요.")
    return errors


# 제목 길이와 필수 섹션의 개수·순서·불릿을 검사해 오류 설명 목록을 반환한다.
def validate_pr(text):
    lines = [line.strip() for line in text.strip().splitlines()]
    errors = []
    if lines.count("--- PR Title ---") != 1 or lines.count("--- PR Body ---") != 1:
        return ["PR Title/PR Body 구분선을 각각 한 번 포함하세요."]
    title_start = lines.index("--- PR Title ---")
    body_start = lines.index("--- PR Body ---")
    # 두 구분선 사이의 빈 줄을 제외한 내용이 정확히 한 줄인지 확인한다.
    title = [line for line in lines[title_start + 1:body_start] if line]
    if title_start != 0 or body_start <= title_start or len(title) != 1:
        errors.append("PR 제목은 비어 있지 않은 한 줄이어야 합니다.")
    elif len(title[0]) > 80:
        errors.append("PR 제목은 최대 80자입니다.")
    body = lines[body_start + 1:]
    positions = []
    for section in SECTIONS:
        if body.count(section) != 1:
            errors.append(f"{section} 헤더를 정확히 한 번 포함하세요.")
            continue
        start = body.index(section)
        positions.append(start)
        # 다음 헤더까지만 검사하여 다른 섹션의 불릿을 잘못 인정하지 않는다.
        end = next((i for i in range(start + 1, len(body)) if body[i].startswith('#')), len(body))
        if not any(re.match(r"^[-*+]\s+\S", line) for line in body[start + 1:end]):
            errors.append(f"{section} 섹션에 내용이 있는 불릿이 필요합니다.")
    if positions != sorted(positions):
        errors.append("섹션 순서는 Why, What, How to Test여야 합니다.")
    return errors
