from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from .config import AVAILABLE_MODELS, load_config, load_profile, set_model, update_profile
from .generation import composer, evaluate, runner
from .models import ComposeAndRunRequest, PlannerPlan, Profile
from .pipeline import auto_compose_and_run, compose_and_run
from .planning import planner


def _load_payload(args: argparse.Namespace, *, allow_empty: bool = False) -> Dict[str, Any]:
    data: str | None = None
    if getattr(args, "file", None):
        try:
            data = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - CLI filesystem guard
            raise SystemExit(f"파일을 읽을 수 없습니다: {exc}")
    elif getattr(args, "data", None):
        data = args.data
    else:
        data = sys.stdin.read().strip()

    if not data:
        if allow_empty:
            return {}
        raise SystemExit("입력 데이터가 없습니다. --file, --data 또는 STDIN을 확인하세요.")

    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"유효한 JSON이 아닙니다: {exc}")


def _print_response(response: Any, pretty: bool) -> None:
    if hasattr(response, "model_dump_json"):
        json_output = response.model_dump_json(indent=2, ensure_ascii=False) if pretty else response.model_dump_json()
    else:
        json_output = json.dumps(response, ensure_ascii=False, indent=2 if pretty else None)
    sys.stdout.write(json_output + "\n")


def _build_request(user_input: str, profile_payload: Dict[str, Any] | None = None) -> ComposeAndRunRequest:
    profile = load_profile()
    if profile_payload:
        profile = Profile(**profile_payload)
    return ComposeAndRunRequest(profile=profile, user_input=user_input)


def _load_plan(args: argparse.Namespace) -> PlannerPlan:
    payload = _load_payload(args)
    try:
        return PlannerPlan(**payload)
    except ValidationError as exc:
        raise SystemExit(f"플랜 스키마 오류: {exc}")


def _load_draft(args: argparse.Namespace) -> str:
    if getattr(args, "draft_file", None):
        try:
            return Path(args.draft_file).read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - CLI filesystem guard
            raise SystemExit(f"파일을 읽을 수 없습니다: {exc}")
    if getattr(args, "draft", None):
        return args.draft
    data = sys.stdin.read()
    if not data:
        raise SystemExit("평가할 텍스트가 없습니다.")
    return data


def handle_model(args: argparse.Namespace) -> int:
    if args.list:
        _print_response({"available": list(AVAILABLE_MODELS), "current": load_config().get("model")}, pretty=True)
        return 0

    if not args.name:
        _print_response({"current": load_config().get("model"), "hint": "--list 옵션으로 전체 목록 확인"}, pretty=args.pretty)
        return 0

    try:
        model_name, config = set_model(args.name)
    except ValueError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1

    _print_response({"selected": model_name, "config_path": str(Path.home() / ".promptchef_config.json")}, pretty=args.pretty)
    return 0


def handle_personal_setting(args: argparse.Namespace) -> int:
    payload = _load_payload(args)
    try:
        profile = update_profile(payload)
    except ValidationError as exc:
        sys.stderr.write(f"프로필 스키마 오류: {exc}\n")
        return 1
    _print_response(profile, pretty=args.pretty)
    return 0


def handle_plan(args: argparse.Namespace) -> int:
    request_model = _build_request(args.user_input, args.profile_override)
    plan = planner(request_model)
    _print_response(plan, pretty=args.pretty)
    return 0


def handle_generate(args: argparse.Namespace) -> int:
    plan = _load_plan(args)
    bundle = composer(plan, args.user_input)
    preview = runner(bundle)
    response = {"bundle": bundle.model_dump(), "preview": preview}
    _print_response(response, pretty=args.pretty)
    return 0


def handle_evaluate(args: argparse.Namespace) -> int:
    plan = _load_plan(args)
    draft = _load_draft(args)
    report = evaluate(draft, plan)
    _print_response(report, pretty=args.pretty)
    return 0


def handle_run_once(args: argparse.Namespace) -> int:
    if args.file or args.data:
        payload = _load_payload(args)
        try:
            request_model = ComposeAndRunRequest(**payload)
        except ValidationError as exc:
            sys.stderr.write(f"요청 스키마 오류: {exc}\n")
            return 1
    else:
        if not args.user_input:
            sys.stderr.write("user_input 인자가 필요합니다. 또는 JSON을 제공하세요.\n")
            return 1
        request_model = _build_request(args.user_input, args.profile_override)

    response = compose_and_run(request_model)
    _print_response(response, pretty=args.pretty)
    return 0


def handle_auto(args: argparse.Namespace) -> int:
    request_model = _build_request(args.user_input, args.profile_override)
    auto_response = auto_compose_and_run(
        request_model, max_rounds=args.max_rounds, target_score=args.target_score
    )
    _print_response(auto_response, pretty=args.pretty)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PromptChef 파이프라인 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    model_parser = subparsers.add_parser(
        "model",
        aliases=["/model"],
        help="사용할 생성형 모델을 선택하거나 조회합니다.",
    )
    model_parser.add_argument("name", nargs="?", help="선택할 모델 이름")
    model_parser.add_argument("--list", action="store_true", help="모델 목록과 현재 선택 확인")
    model_parser.add_argument("--pretty", action="store_true", help="출력을 읽기 좋게 표시")
    model_parser.set_defaults(func=handle_model)

    profile_parser = subparsers.add_parser(
        "personal_setting",
        aliases=["/personal_setting"],
        help="사용자 프로필 정보를 설정합니다.",
    )
    profile_parser.add_argument("-f", "--file", help="프로필 JSON 파일 경로")
    profile_parser.add_argument("-d", "--data", help="프로필 JSON 문자열")
    profile_parser.add_argument("--pretty", action="store_true", help="출력을 들여쓰기함")
    profile_parser.set_defaults(func=handle_personal_setting)

    plan_parser = subparsers.add_parser(
        "plan",
        aliases=["/plan"],
        help="사용자 입력을 받아 실행 계획을 생성합니다.",
    )
    plan_parser.add_argument("user_input", help="사용자 질문 또는 요청")
    plan_parser.add_argument(
        "--profile-override",
        dest="profile_override",
        type=json.loads,
        help="이 실행에만 사용할 프로필 JSON 문자열",
    )
    plan_parser.add_argument("--pretty", action="store_true", help="출력을 들여쓰기함")
    plan_parser.set_defaults(func=handle_plan)

    generate_parser = subparsers.add_parser(
        "generate",
        aliases=["/generate"],
        help="플랜을 기반으로 시스템/유저 프롬프트를 작성합니다.",
    )
    generate_parser.add_argument("user_input", help="원본 사용자 입력")
    generate_parser.add_argument("-f", "--file", help="PlannerPlan JSON 파일")
    generate_parser.add_argument("-d", "--data", help="PlannerPlan JSON 문자열")
    generate_parser.add_argument("--pretty", action="store_true")
    generate_parser.set_defaults(func=handle_generate)

    eval_parser = subparsers.add_parser(
        "evaluate",
        aliases=["/evaluate"],
        help="생성 결과를 평가합니다.",
    )
    eval_parser.add_argument("-f", "--file", help="PlannerPlan JSON 파일")
    eval_parser.add_argument("-d", "--data", help="PlannerPlan JSON 문자열")
    eval_parser.add_argument("--draft-file", help="평가할 텍스트 파일 경로")
    eval_parser.add_argument("--draft", help="평가할 텍스트 내용")
    eval_parser.add_argument("--pretty", action="store_true")
    eval_parser.set_defaults(func=handle_evaluate)

    run_parser = subparsers.add_parser(
        "run_once",
        aliases=["/run_and_compose", "pipeline"],
        help="플랜부터 생성/평가까지 한 번에 수행합니다.",
    )
    run_parser.add_argument("user_input", nargs="?", help="사용자 입력. JSON을 직접 넘기면 생략 가능")
    run_parser.add_argument("-f", "--file", help="ComposeAndRunRequest JSON 파일")
    run_parser.add_argument("-d", "--data", help="ComposeAndRunRequest JSON 문자열")
    run_parser.add_argument(
        "--profile-override",
        dest="profile_override",
        type=json.loads,
        help="실행 시 사용할 임시 프로필(JSON)",
    )
    run_parser.add_argument("--pretty", action="store_true")
    run_parser.set_defaults(func=handle_run_once)

    auto_parser = subparsers.add_parser(
        "auto_iterate",
        aliases=["/run_auto"],
        help="평가 결과에 따라 자동으로 재시도합니다.",
    )
    auto_parser.add_argument("user_input", help="사용자 입력")
    auto_parser.add_argument(
        "--profile-override",
        dest="profile_override",
        type=json.loads,
        help="실행 시 사용할 임시 프로필(JSON)",
    )
    auto_parser.add_argument("--max-rounds", type=int, default=3, help="최대 재시도 횟수")
    auto_parser.add_argument("--target-score", type=float, default=0.85, help="목표 평가 점수")
    auto_parser.add_argument("--pretty", action="store_true")
    auto_parser.set_defaults(func=handle_auto)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        return args.func(args)
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
