import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

import ai_client
import git_utils
import main
from safe_mode import sanitize_diff
from validators import validate_commit, validate_pr

PR = '--- PR Title ---\n변경 요약\n\n--- PR Body ---\n\n## Why\n- 변경 배경 확인 필요\n\n## What\n- 오류 처리 추가\n\n## How to Test\n- 테스트 실행 권장'


class ValidationTests(unittest.TestCase):
    # 정상 형식과 커밋 제목의 최대 길이 경계가 통과하는지 확인한다.
    def test_valid(self):
        self.assertEqual(validate_commit('fix: 오류 처리\n\n- 빈 값 처리'), [])
        self.assertEqual(validate_pr(PR), [])
        self.assertEqual(validate_commit('가' * 72), [])

    # 빈 메시지, 긴 제목, 불릿 없는 본문이 거부되는지 확인한다.
    def test_invalid_commit(self):
        for text in ('', '가' * 73, '제목\n\n불릿 없는 본문'):
            self.assertTrue(validate_commit(text))

    # 제목과 섹션을 하나씩 손상시켜 검증기가 각 오류를 잡는지 확인한다.
    def test_invalid_pr(self):
        for text in (PR.replace('변경 요약', ''), PR.replace('변경 요약', '가' * 81), PR.replace('변경 요약', '제목\n추가 제목'), PR.replace('- 변경 배경 확인 필요', ''), PR.replace('## Why', '## WhyWrong'), PR.replace('## What', '## Other')):
            self.assertTrue(validate_pr(text), text)

    # 마스킹 결과와 줄 수·파일 블록 수 제한을 확인한다.
    def test_safe_mode(self):
        self.assertNotIn('person@example.com', sanitize_diff('+person@example.com'))
        self.assertNotIn('abcdefghijk', sanitize_diff('+api_key=abcdefghijk'))
        self.assertEqual(len(sanitize_diff('\n'.join(['+line'] * 250)).splitlines()), 200)
        diff = '\n'.join(f'diff --git a/{i} b/{i}\n+line' for i in range(15))
        self.assertEqual(sanitize_diff(diff).count('diff --git'), 10)


class ApiTests(unittest.TestCase):
    # 실제 네트워크 대신 모의 응답이나 오류를 사용하여 API 클라이언트를 검사한다.
    def invoke(self, payload=None, error=None):
        opener = MagicMock()
        if error:
            opener.open.side_effect = error
        else:
            opener.open.return_value.__enter__.return_value.read.return_value = payload
        with patch.dict(os.environ, {}, clear=True), patch('ai_client.urllib.request.build_opener', return_value=opener):
            result = ai_client.call_ai('test-key', 'diff', 'model', 0.3, 1000)
        return result, opener

    # 전송할 JSON과 인증 헤더, 반환 텍스트가 예상대로 구성되는지 확인한다.
    def test_request_and_response(self):
        result, opener = self.invoke(json.dumps({'choices': [{'message': {'content': ' hello '}, 'finish_reason': 'stop'}]}).encode())
        self.assertEqual(result, 'hello')
        request = opener.open.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body['messages'][1]['content'], 'diff')
        self.assertEqual(body['max_completion_tokens'], 1000)
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')

    # 환경변수의 주소·모델·타임아웃과 모델별 요청 옵션을 확인한다.
    def test_codyssey_environment(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"ok"}}]}'
        env = {"LLM_BASE_URL": "https://copa.codyssey.kr/v1/", "LLM_MODEL": "gpt-5-mini", "LLM_TIMEOUT_SECONDS": "30"}
        with patch.dict(os.environ, env, clear=True), patch('ai_client.urllib.request.build_opener', return_value=opener):
            args = main.create_parser().parse_args(['commit'])
            self.assertEqual(args.model, 'gpt-5-mini')
            ai_client.call_ai('dummy', 'test', args.model, args.temperature, 4000)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://copa.codyssey.kr/v1/chat/completions')
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 30)
        body = json.loads(request.data)
        self.assertNotIn('temperature', body)
        self.assertEqual(body['max_completion_tokens'], 4000)

    # 잘못된 타임아웃과 지원하지 않는 옵션을 요청 전에 거부하는지 확인한다.
    def test_invalid_codyssey_options(self):
        for timeout in ('0', '-1', 'nan', 'bad'):
            with patch.dict(os.environ, {'LLM_TIMEOUT_SECONDS': timeout}, clear=True), self.assertRaises(RuntimeError):
                ai_client.call_ai('dummy', 'test', 'gpt-5-mini', None, 1000)
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, 'temperature'):
            ai_client.call_ai('dummy', 'test', 'gpt-5-mini', 0.3, 1000)

    # 잘못된 응답·인증 오류·연결 오류가 공통 RuntimeError로 전달되는지 확인한다.
    def test_failures(self):
        for payload in (b'no json', b'{}', b'null', b'{"choices": []}', b'{"choices": [{"message": {"content": ""}}]}', b'{"choices": [{"finish_reason": "length"}]}'):
            with self.assertRaises(RuntimeError):
                self.invoke(payload)
        for error in (urllib.error.URLError('offline'), TimeoutError(), urllib.error.HTTPError('https://test', 401, 'unauthorized', {}, None)):
            with self.assertRaises(RuntimeError):
                self.invoke(error=error)


class CliTests(unittest.TestCase):
    # Git과 API를 모의 객체로 대체하고 종료 코드·출력·호출 횟수를 수집한다.
    def run_cli(self, responses, command='commit', status=' M a.py\n', key='test-key'):
        output = io.StringIO()
        with patch.dict(os.environ, {'AI_API_KEY': key}, clear=True), patch('sys.argv', ['main.py', command, '--safe-mode']), patch.object(main, 'ensure_repository_root'), patch.object(main, 'get_git_status', return_value=status), patch.object(main, 'get_git_diff', return_value='diff --git a/a.py b/a.py\n+line'), patch.object(main, 'get_current_branch', return_value='main'), patch.object(main, 'call_ai', side_effect=responses) as api, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = main.main()
        return code, output.getvalue(), api.call_count

    # 변경이 없으면 API 키 없이도 정상 종료하고 API를 호출하지 않아야 한다.
    def test_clean_without_key(self):
        code, output, calls = self.run_cli([], status='', key='')
        self.assertEqual((code, calls), (0, 0))
        self.assertIn('변경 사항이 없습니다', output)

    # 변경이 있는데 키가 없으면 API 호출 없이 실패해야 한다.
    def test_missing_key(self):
        self.assertEqual(self.run_cli([], key='')[::2], (1, 0))

    # 첫 결과의 형식이 잘못되면 한 번 재생성하여 성공할 수 있어야 한다.
    def test_retry_success(self):
        self.assertEqual(self.run_cli(['x' * 73, 'fix: 수정'])[::2], (0, 2))

    # 두 번째 결과도 잘못되면 완료 문구 없이 실패해야 한다.
    def test_retry_failure(self):
        code, output, calls = self.run_cli(['x' * 73] * 2)
        self.assertEqual((code, calls), (1, 2))
        self.assertNotIn('[DONE]', output)

    # 정상 PR 초안은 API 한 번만으로 완료되어야 한다.
    def test_pr_success(self):
        self.assertEqual(self.run_cli([PR], command='pr')[::2], (0, 1))

    # 네트워크 오류에는 형식 재생성 절차를 적용하지 않아야 한다.
    def test_network_failure_no_retry(self):
        self.assertEqual(self.run_cli([RuntimeError('network')])[::2], (1, 1))

    # 옵션 위치에 관계없이 값을 읽고 잘못된 숫자는 거부하는지 확인한다.
    def test_options(self):
        parser = main.create_parser()
        for argv in (['--model', 'test', 'commit'], ['commit', '-model', 'test']):
            self.assertEqual(parser.parse_args(argv).model, 'test')
        for value in ('nan', 'inf', '-1', '3'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(['commit', '--temperature', value])


class GitTests(unittest.TestCase):
    # 임시 Git 저장소에서 미추적·staged·unstaged 상태와 루트 검사를 확인한다.
    def test_real_repository(self):
        # 사용자 저장소 대신 자동 정리되는 임시 폴더에서 Git 동작을 시험한다.
        with tempfile.TemporaryDirectory() as directory:
            original = Path.cwd()
            try:
                os.chdir(directory)
                def git(*args):
                    subprocess.run(['git', *args], check=True, capture_output=True)
                git('init')
                git_utils.ensure_repository_root()
                self.assertEqual(git_utils.get_git_status(), '')
                file = Path('sample.txt')
                file.write_text('new file\n')
                self.assertIn('?? sample.txt', git_utils.get_git_status())
                self.assertEqual(git_utils.get_git_diff(), '')
                git('add', 'sample.txt')
                self.assertIn('+new file', git_utils.get_git_diff())
                file.write_text('changed file\n')
                diff = git_utils.get_git_diff()
                self.assertIn('[Staged changes]', diff)
                self.assertIn('[Unstaged changes]', diff)
                Path('sub').mkdir()
                os.chdir('sub')
                with self.assertRaises(RuntimeError):
                    git_utils.ensure_repository_root()
            finally:
                os.chdir(original)


if __name__ == '__main__':
    unittest.main()
