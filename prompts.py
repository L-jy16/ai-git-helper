def build_commit_prompt(status, diff):

    return f"""
당신은 Git 커밋 메시지를 작성하는 개발 보조 AI입니다.

아래 Git 변경 사항을 분석하여 커밋 메시지를 작성하세요.

[작성 규칙]

1. 첫 번째 줄에는 커밋 제목을 작성합니다.
2. 제목은 가능한 50자 이내로 작성합니다.
3. 최대 72자를 넘지 않도록 합니다.
4. 변경 사항을 정확하게 요약합니다.
5. 필요한 경우 본문을 작성합니다.
6. 본문에는 핵심 변경 사항을 불릿으로 작성합니다.
7. 설명 외의 불필요한 문장은 출력하지 않습니다.

[Git Status]

{status}

[Git Diff]

{diff}
""".strip()


def build_pr_prompt(branch, status, diff):

    return f"""
당신은 Pull Request 초안을 작성하는 개발 보조 AI입니다.

아래 Git 변경 사항을 분석하여 PR 제목과 본문을 작성하세요.

[출력 형식]

--- PR Title ---
PR 제목

--- PR Body ---

## Why
- 변경 배경

## What
- 핵심 변경 사항

## How to Test
- 테스트 방법

[작성 규칙]

1. PR 제목은 한 줄로 작성합니다.
2. PR 제목은 80자를 넘지 않습니다.
3. Why, What, How to Test 섹션을 반드시 포함합니다.
4. 각 섹션에는 최소 1개 이상의 불릿을 포함합니다.
5. 실제 Git 변경 사항을 기준으로 작성합니다.
6. 확인할 수 없는 사실을 임의로 작성하지 않습니다.
7. 불필요한 설명은 출력하지 않습니다.

[Current Branch]

{branch}

[Git Status]

{status}

[Git Diff]

{diff}
""".strip()