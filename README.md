# ai-git-helper

Git 변경 사항을 AI로 분석하여 한국어 커밋 메시지 또는 PR 제목·본문 초안을 출력하는 Python CLI입니다. 필수 과제 범위만 구현합니다. 커밋, push, GitHub PR 생성은 자동으로 수행하지 않습니다.

## 설치

Python 3.10 이상, Git, 사용할 AI 서비스의 API 키가 필요합니다. 외부 Python 패키지는 없습니다.

```bash
git clone https://github.com/L-jy16/ai-git-helper.git
cd ai-git-helper
python3 --version
python3 -m pip install -r requirements.txt
```

다른 프로젝트에 적용하려면 해당 Git 프로젝트 루트에서 `python3 /도구의/절대경로/main.py commit`처럼 실행합니다. 하위 디렉토리나 Git 저장소 밖에서는 오류로 종료합니다.

## API 환경변수

```bash
export AI_API_KEY="본인의_API_KEY"
export AI_MODEL="gpt-4.1-mini"
```

키는 환경변수로만 읽으며 소스 코드에 넣지 않습니다. `.env` 파일은 자동으로 읽지 않습니다. 키를 채팅이나 저장소에 게시하지 마세요.

기본 주소는 `https://api.openai.com/v1/chat/completions`이며 기본 모델은 `gpt-4.1-mini`입니다. 다른 **OpenAI Chat Completions 호환 API**를 사용하면 다음 환경변수를 설정합니다. Gemini 등의 고유 API 형식을 직접 지원하지는 않습니다.

```bash
export AI_API_URL="https://your-provider.example/v1/chat/completions"
export AI_MODEL="서비스에서_지원하는_모델"
# 서비스가 기존 max_tokens 필드를 요구할 때만 설정
export AI_TOKEN_PARAMETER="max_tokens"
```

`AI_API_URL`은 전체 HTTPS 엔드포인트입니다. 기본 토큰 필드는 `max_completion_tokens`입니다. 모델은 `temperature`와 선택한 토큰 필드를 지원해야 합니다. 지원하지 않으면 HTTP 400 오류가 발생할 수 있습니다.

구현 참고: [Chat Completions 공식 API 규격](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [GPT-4.1 mini 모델 문서](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## 사용 방법

프로젝트 루트에서 파일을 수정한 후 실행합니다. 신규 파일은 먼저 필요한 파일만 `git add`하세요. 미추적 파일은 목록에는 표시되지만 본문은 `git diff`에 없으므로 AI 분석에 포함되지 않습니다.

```bash
# 신규 파일을 분석에 포함할 때
# git add path/to/new_file.py

python3 main.py commit --safe-mode
python3 main.py pr --safe-mode
python3 main.py commit --model gpt-4.1-mini --temperature 0.2 --max-tokens 1200
python3 main.py --safe-mode --temperature 0.2 pr
python3 main.py --help
```

`-model`, `-temperature`, `-max-tokens`, `-safe-mode` 표기도 지원합니다. 옵션은 명령 앞이나 뒤에 둘 수 있습니다.

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `--model` | `AI_MODEL` 또는 `gpt-4.1-mini` | 호출할 모델 |
| `--temperature` | `0.3` | 0~2. 낮을수록 더 일관된 표현을 유도하고 높을수록 표현의 다양성이 커짐 |
| `--max-tokens` | `1000` | 양의 정수. 출력 토큰 상한. 너무 낮으면 결과가 잘릴 수 있음 |
| `--safe-mode` | 꺼짐 | 민감정보 패턴 마스킹 및 diff 전송량 제한 |

## 실행 흐름과 검증

1. Git 루트인지 확인하고 `git status --short --untracked-files=all`로 파일 목록을 출력합니다.
2. 변경이 없으면 키 없이도 안내 후 정상 종료합니다.
3. `git diff`와 `git diff --cached`를 수집하고 서로 구분해서 전달합니다. 둘 다 비어 있으면 API를 호출하지 않습니다.
4. 선택한 안전 모드를 적용하고 API를 한 번 호출합니다.
5. 커밋 제목 최대 72자(50자 권장), 본문이 있으면 내용 있는 불릿, PR 제목 한 줄·최대 80자, Why/What/How to Test 헤더와 각 섹션의 불릿을 검사합니다.
6. 형식 오류이면 오류 설명을 추가하여 한 번 재생성합니다. 다시 실패하면 완료 출력 없이 종료 코드 1로 끝납니다. 51~72자 커밋 제목은 권장 길이 안내만 출력합니다.
7. 성공 결과는 구분선과 함께 출력합니다. 생성된 내용을 검토한 뒤 직접 적용하세요.

동일 파일에 staged/unstaged 변경이 모두 있으면 두 diff는 서로 다른 시점의 변경입니다. 실제 커밋할 변경만 남기거나 스테이징한 뒤 결과를 검토하세요. PR 초안도 현재 작업 트리의 변경을 대상으로 하며, 이미 커밋된 브랜치 전체 이력을 분석하지 않습니다. 바이너리 파일 내부의 의미는 분석할 수 없습니다.

## 출력 예시

아래는 형식 설명용 예시이며 실제 API 실행 기록이 아닙니다. 내용은 변경 사항과 모델에 따라 달라집니다.

커밋 예시:

```text
[INFO] AI API 요청 중... (1/2)
[DONE] 검증된 초안 생성 완료 (내용을 검토한 후 적용하세요)

--- Commit Message ---
fix: 빈 입력에 대한 오류 처리 추가

- 입력값이 비어 있을 때 안내 메시지 출력
----------------------
[INFO] AI API 호출 횟수: 1
```

PR 예시:

```text
--- PR Title ---
fix: 빈 입력에 대한 오류 처리 추가

--- PR Body ---

## Why
- 빈 입력의 처리 방식을 명확히 하기 위한 변경입니다. 실제 배경은 작성자가 확인해야 합니다.

## What
- 입력값이 비어 있을 때 안내 메시지를 출력하도록 수정했습니다.

## How to Test
- 빈 문자열을 입력하고 안내 메시지가 출력되는지 확인하세요. 실제 실행 여부는 별도 확인이 필요합니다.
----------------------
```

## 오류 처리

| 상황 | 동작 |
| --- | --- |
| 변경 없음 | 안내, API 0회, 종료 코드 0 |
| 미추적 파일만 있음 | `git add <파일>` 안내, API 0회 |
| API 키 없음 | 환경변수 설정 안내, 종료 코드 1 |
| HTTP 401 / 403 | 인증 실패 / 접근 권한 안내 |
| HTTP 429 | 요청 한도 또는 잔액 안내 |
| 네트워크·인증서 오류 / 시간 초과 | 원인 범주 안내, 자동 재시도 없음 |
| 잘못된 JSON / 비어 있는 응답 | 오류 안내, 종료 코드 1 |
| 토큰 한도에 의한 출력 중단 | `--max-tokens` 증가 안내 |
| 재생성 후 형식 오류 | 오류 안내, 완료 처리하지 않음 |

요청 대기 시간은 30초입니다. 서버 응답의 원문 오류 본문은 민감정보 노출을 줄이기 위해 출력하지 않습니다.

## 안전 모드와 비용

- `--safe-mode`는 이메일과 `api_key`, `secret`, `token` 값 등의 일부 패턴을 마스킹합니다. 파일 목록과 브랜치 이름에도 같은 마스킹을 적용합니다.
- diff는 최대 10개 파일 블록, 최대 200줄로 제한합니다. 같은 파일의 staged/unstaged 블록도 각각 셉니다. 파일 목록은 제한하지 않습니다.
- 이 기능은 모든 비밀정보를 검출하지 않습니다. 전송 전에 `git diff`와 `git diff --cached`를 직접 확인하세요. `.gitignore`는 이미 추적 중인 파일을 제외하지 않습니다.
- 잘린 diff에는 변경 내용 일부가 빠지므로 결과의 정확성을 확인하세요.
- 정상 실행은 API 1회, 형식 재생성이 필요할 때만 최대 2회 호출하며 호출 횟수를 출력합니다. 변경이 없으면 0회입니다.
- 입력 diff와 출력 토큰에 따라 비용이 발생할 수 있습니다. 모델·토큰 상한을 확인하고 불필요한 반복 실행을 피하세요.
- 형식 검증은 요약 내용의 사실성을 보장하지 않습니다. 변경 배경과 테스트 방법은 사용자가 최종 검토합니다.

## 테스트 및 제출 확인

```bash
python3 -m unittest discover -s tests -v
```

자동 테스트는 실제 임시 Git 저장소와 모의 API 응답을 사용합니다. 외부 API를 호출하거나 비용을 발생시키지 않습니다. 실제 API의 계정 권한·과금·모델 접근은 검증하지 않습니다.

제출 전에는 유효한 API 키로 `commit`과 `pr`을 각각 실행하여 생성 결과를 확인하고, 소스와 README를 GitHub에 커밋·push해야 합니다. 이 프로그램은 해당 작업을 자동으로 수행하지 않습니다. 보너스인 실제 PR 작성, 팀 컨벤션 커스터마이징, 안전 모드 정책 고도화는 포함하지 않습니다.

## 파일 구성

- `main.py`: CLI 옵션, 실행 순서, 재생성 제한, 결과 출력
- `git_utils.py`: Git 루트 검사, 상태·diff·브랜치 수집
- `ai_client.py`: HTTPS REST 요청, 응답 파싱, 오류 처리
- `prompts.py`: 커밋·PR 작성 규칙과 Git 컨텍스트
- `validators.py`: 제목 길이, PR 섹션, 불릿 검사
- `safe_mode.py`: 기본 마스킹과 전송량 제한
- `tests/test_app.py`: 회귀 테스트
