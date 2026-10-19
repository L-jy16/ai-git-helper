<!-- @format -->

# ai-git-helper

Git 변경 사항을 AI로 분석하여 한국어 커밋 메시지 또는 PR 제목·본문 초안을 출력하는 Python CLI입니다. 필수 과제 범위만 구현합니다. 커밋, push, GitHub PR 생성은 자동으로 수행하지 않습니다.

## 1. 설치와 실행 위치

Python 3.10 이상, Git, 사용할 AI 서비스의 API 키가 필요합니다. Python 표준 라이브러리만 사용하므로 외부 패키지 설치는 필요하지 않습니다.

아래 명령은 VS Code 등의 **일반 터미널**에서 입력합니다. 한 번 실행하면 결과를 출력하고 종료하는 프로그램입니다.

```bash
# 처음 내려받을 때만 실행합니다. 이미 프로젝트가 있으면 이 단계는 건너뜁니다.
git clone https://github.com/L-jy16/ai-git-helper.git
cd ai-git-helper

# Python 버전을 확인합니다. 3.10 이상이어야 합니다.
python3 --version

# 사용할 수 있는 명령과 옵션을 확인합니다.
python3 main.py --help
```

이미 프로젝트를 열었다면 터미널의 현재 위치가 `main.py`가 있는 프로젝트 루트인지 확인하세요. 경로에 공백이나 괄호가 있으면 `cd "프로젝트의 전체 경로"`처럼 따옴표로 감쌉니다.

다른 저장소에 적용할 때는 **분석할 Git 저장소의 루트**로 이동한 다음 `python3 "/도구의 전체 경로/main.py" commit`으로 실행합니다. Git 저장소 밖이나 하위 폴더에서는 오류로 종료합니다.

## 2. Codyssey 환경변수 설정

환경변수는 프로그램에 키·주소·모델 같은 실행 설정을 전달합니다. 프로젝트 루트의 `.env` 파일에 다음 내용을 작성하세요. **키 자리에는 본인이 발급받은 값을 넣고, 실제 키를 README나 Python 파일에 적지 않습니다.**

```bash
# API 인증에 사용할 키입니다. 아래 값은 설명용 자리표시자입니다.
export LLM_API_KEY='본인의_API_KEY'

# 기본 주소입니다. 코드는 뒤에 /chat/completions를 붙여 요청합니다.
export LLM_BASE_URL='https://copa.codyssey.kr/v1'

# 사용할 모델 이름입니다.
export LLM_MODEL='gpt-5-mini'

# API 요청의 타임아웃을 초 단위로 설정합니다.
export LLM_TIMEOUT_SECONDS=30
```

파일을 저장한 뒤, macOS의 zsh 또는 bash 터미널에서 불러옵니다.

```bash
# .env의 export 문장을 실행해 현재 터미널에 환경변수를 설정합니다.
source .env
```

`.env`는 자동으로 읽히지 않으므로 새 터미널을 열면 다시 불러와야 합니다. Git에서 제외되는 파일이며 저장소에 올리지 않습니다. 줄 앞의 `#`는 설명을 위한 주석이므로 실제 설정 줄에는 붙이지 마세요.

이 설정의 최종 요청 주소는 `https://copa.codyssey.kr/v1/chat/completions`입니다. `LLM_*` 설정은 기존 `AI_*`보다 우선합니다.

현재 구현은 `gpt-5-mini` 요청에서 `temperature`를 생략합니다. 이 모델을 사용할 때 `--temperature`를 명시하면 오류로 종료하므로 아래 기본 실습에서는 해당 옵션을 넣지 않습니다.

## 3. 변경 사항 준비하기

AI는 현재 Git 변경 내용을 읽습니다. 먼저 파일을 수정하고 저장하세요. 예를 들어 README 마지막에 실습 목적을 한 줄 추가할 수 있습니다.

```bash
# 변경된 파일과 상태를 확인합니다.
# M은 수정된 파일, ??는 Git이 아직 추적하지 않는 새 파일입니다.
git status --short

# 아직 스테이징하지 않은 파일의 실제 변경 내용을 확인합니다.
git diff

# 예: README를 스테이징합니다. 새 파일은 해당 파일 경로를 지정하세요.
# git add는 커밋을 만드는 명령이 아니라 다음 커밋에 포함할 변경을 준비하는 명령입니다.
git add README.md

# 스테이징한 변경 내용을 확인합니다.
git diff --cached
```

새 파일은 `git add` 전에는 목록에만 나타나고 내용은 AI 분석에 포함되지 않습니다. 이미 추적 중인 파일의 수정은 스테이징 전에도 분석됩니다. 민감한 파일까지 포함하지 않도록 필요한 파일을 지정하세요.

## 4. 명령어별 사용 방법

### commit: 커밋 메시지 초안 생성

```bash
# 변경 내용을 읽고 제목과 선택적 본문을 생성합니다.
# --safe-mode: 일부 민감정보 마스킹과 diff 전송량 제한을 적용합니다.
# --max-tokens 4000: 출력 토큰 상한을 지정합니다.
python3 main.py commit --safe-mode --max-tokens 4000
```

결과의 첫 줄은 커밋 제목입니다. 실제 변경을 정확히 설명하는지 확인한 뒤 복사해서 사용하세요. 이 명령은 **메시지를 출력하며 실제 Git 커밋을 만들지는 않습니다.**

### pr: PR 제목과 본문 초안 생성

```bash
# 같은 변경 사항에서 PR 제목과 Why / What / How to Test 본문을 생성합니다.
# commit 초안 명령 실행 후, 실제 git commit을 하기 전에 실습하세요.
python3 main.py pr --safe-mode --max-tokens 4000
```

PR 초안은 현재 작업 트리와 스테이징 영역의 변경을 대상으로 합니다. 이미 커밋된 브랜치 전체 이력을 비교하는 기능은 없습니다. 이 명령은 GitHub에 PR을 게시하지 않습니다.

### --help: 명령과 옵션 확인

```bash
# 프로그램 전체 도움말
python3 main.py --help

# commit 명령에서 사용할 수 있는 옵션
python3 main.py commit --help

# 옵션을 명령 앞에 적어도 동작합니다.
python3 main.py --safe-mode --max-tokens 4000 pr
```

| 옵션 | 기본값 | 역할과 주의점 |
| --- | --- | --- |
| `--model` | `LLM_MODEL` → `AI_MODEL` → `gpt-4.1-mini` 순서 | CLI에 직접 지정하면 환경변수보다 우선합니다. |
| `--temperature` | 일반 모델은 0.3, `gpt-5-mini`는 생략 | 0~2 사이 값. 현재 구현에서 `gpt-5-mini`에 직접 지정하면 오류입니다. |
| `--max-tokens` | 1000 | 양의 정수. 예시에서는 4000을 사용합니다. 결과가 잘리면 늘려 보세요. |
| `--safe-mode` | 꺼짐 | 일부 민감정보 마스킹, diff 최대 10개 파일 블록·200줄 제한 |

`-model`, `-temperature`, `-max-tokens`, `-safe-mode`처럼 하이픈 하나인 표기도 지원합니다. 모델에 따라 토큰 상한에 추론 토큰이 포함될 수 있어, 상한 전체가 화면에 보이는 텍스트 분량은 아닙니다.

## 5. 프로그램 내부 흐름과 검증

1. Git 루트인지 확인하고 `git status --short --untracked-files=all`로 파일 목록을 출력합니다.
2. 변경이 없으면 키 없이도 안내 후 정상 종료합니다.
3. `git diff`와 `git diff --cached`를 수집하고 서로 구분해서 전달합니다. 둘 다 비어 있으면 API를 호출하지 않습니다.
4. 선택한 안전 모드를 적용하고 API를 한 번 호출합니다.
5. 커밋 제목 최대 72자(50자 권장), 본문이 있으면 내용 있는 불릿, PR 제목 한 줄·최대 80자, Why/What/How to Test 헤더와 각 섹션의 불릿을 검사합니다.
6. 형식 오류이면 오류 설명을 추가하여 한 번 재생성합니다. 다시 실패하면 완료 출력 없이 종료 코드 1로 끝납니다. 51~72자 커밋 제목은 권장 길이 안내만 출력합니다.
7. 성공 결과는 구분선과 함께 출력합니다. 생성된 내용을 검토한 뒤 직접 적용하세요.

동일 파일에 staged/unstaged 변경이 모두 있으면 두 diff는 서로 다른 시점의 변경입니다. 실제 커밋할 변경만 남기거나 스테이징한 뒤 결과를 검토하세요. PR 초안도 현재 작업 트리의 변경을 대상으로 하며, 이미 커밋된 브랜치 전체 이력을 분석하지 않습니다. 바이너리 파일 내부의 의미는 분석할 수 없습니다.

## 6. 출력 예시

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

## 7. 오류가 나왔을 때

| 상황                             | 동작                             |
| -------------------------------- | -------------------------------- |
| 변경 없음                        | 안내, API 0회, 종료 코드 0       |
| 미추적 파일만 있음               | `git add <파일>` 안내, API 0회   |
| API 키 없음                      | 환경변수 설정 안내, 종료 코드 1  |
| HTTP 401 / 403                   | 인증 실패 / 접근 권한 안내       |
| HTTP 429                         | 요청 한도 또는 잔액 안내         |
| 네트워크·인증서 오류 / 시간 초과 | 원인 범주 안내, 자동 재시도 없음 |
| 잘못된 JSON / 비어 있는 응답     | 오류 안내, 종료 코드 1           |
| 토큰 한도에 의한 출력 중단       | `--max-tokens` 증가 안내         |
| 재생성 후 형식 오류              | 오류 안내, 완료 처리하지 않음    |

요청 대기 시간은 `LLM_TIMEOUT_SECONDS`로 설정하며 기본 30초입니다. 서버 응답의 원문 오류 본문은 민감정보 노출을 줄이기 위해 출력하지 않습니다.

## 8. 안전 모드와 비용

- `--safe-mode`는 이메일과 `api_key`, `secret`, `token` 값 등의 일부 패턴을 마스킹합니다. 파일 목록과 브랜치 이름에도 같은 마스킹을 적용합니다.
- diff는 최대 10개 파일 블록, 최대 200줄로 제한합니다. 같은 파일의 staged/unstaged 블록도 각각 셉니다. 파일 목록은 제한하지 않습니다.
- 이 기능은 모든 비밀정보를 검출하지 않습니다. 전송 전에 `git diff`와 `git diff --cached`를 직접 확인하세요. `.gitignore`는 이미 추적 중인 파일을 제외하지 않습니다.
- 잘린 diff에는 변경 내용 일부가 빠지므로 결과의 정확성을 확인하세요.
- 정상 실행은 API 1회, 형식 재생성이 필요할 때만 최대 2회 호출하며 호출 횟수를 출력합니다. 변경이 없으면 0회입니다.
- 입력 diff와 출력 토큰에 따라 비용이 발생할 수 있습니다. 모델·토큰 상한을 확인하고 불필요한 반복 실행을 피하세요.
- 형식 검증은 요약 내용의 사실성을 보장하지 않습니다. 변경 배경과 테스트 방법은 사용자가 최종 검토합니다.

## 9. 테스트와 제출 전 확인

```bash
# tests 폴더의 자동 테스트를 실행합니다. 실제 API는 호출하지 않습니다.
python3 -m unittest discover -s tests -v
```

마지막에 `OK`가 표시되면 테스트를 통과한 것입니다. 실제 API 연결 성공 여부는 별도로 확인해야 합니다.

자동 테스트는 실제 임시 Git 저장소와 모의 API 응답을 사용합니다. 외부 API를 호출하거나 비용을 발생시키지 않습니다. 실제 API의 계정 권한·과금·모델 접근은 검증하지 않습니다.

제출 전에는 유효한 API 키로 `commit`과 `pr`을 각각 실행하여 생성 결과를 확인하고, 소스와 README를 GitHub에 커밋·push해야 합니다. 이 프로그램은 해당 작업을 자동으로 수행하지 않습니다. 보너스인 실제 PR 작성, 팀 컨벤션 커스터마이징, 안전 모드 정책 고도화는 포함하지 않습니다.

## 10. 파일별 역할

- `main.py`: CLI 옵션, 실행 순서, 재생성 제한, 결과 출력
- `git_utils.py`: Git 루트 검사, 상태·diff·브랜치 수집
- `ai_client.py`: HTTPS REST 요청, 응답 파싱, 오류 처리
- `prompts.py`: 커밋·PR 작성 규칙과 Git 컨텍스트
- `validators.py`: 제목 길이, PR 섹션, 불릿 검사
- `safe_mode.py`: 기본 마스킹과 전송량 제한
- `tests/test_app.py`: 회귀 테스트

## 부록: 다른 OpenAI 호환 API를 사용할 때

Codyssey 설정 대신 사용할 때는 현재 터미널의 우선 설정을 먼저 해제합니다. 이후 `source .env`를 실행하면 Codyssey 설정이 다시 적용됩니다.

```bash
# 기존 LLM 설정을 해제해 아래 AI 설정이 적용되도록 합니다.
unset LLM_API_KEY LLM_BASE_URL LLM_MODEL

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

`AI_API_URL`은 전체 HTTPS 엔드포인트입니다. 기본 토큰 필드는 `max_completion_tokens`입니다. 선택한 모델과 API가 코드에서 보내는 요청 필드를 지원해야 합니다. 지원하지 않으면 HTTP 400 오류가 발생할 수 있습니다.

<!-- 구현 참고: [Chat Completions 공식 API 규격](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [GPT-4.1 mini 모델 문서](https://developers.openai.com/api/docs/models/gpt-4.1-mini). -->

