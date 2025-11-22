from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from .models import ComposeAndRunRequest
from .pipeline import compose_and_run


def _load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.file:
        try:
            data = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - CLI filesystem guard
            raise SystemExit(f"파일을 읽을 수 없습니다: {exc}")
    elif args.data:
        data = args.data
    else:
        data = sys.stdin.read()

    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"유효한 JSON이 아닙니다: {exc}")


def _print_response(response: Any, pretty: bool) -> None:
    json_output = response.model_dump_json(indent=2, ensure_ascii=False) if pretty else response.model_dump_json()
    sys.stdout.write(json_output + "\n")


def handle_compose_and_run(args: argparse.Namespace) -> int:
    payload = _load_payload(args)
    try:
        request_model = ComposeAndRunRequest(**payload)
    except ValidationError as exc:
        sys.stderr.write(f"요청 스키마 오류: {exc}\n")
        return 1

    response = compose_and_run(request_model)
    _print_response(response, pretty=args.pretty)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PromptChef 파이프라인 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compose_parser = subparsers.add_parser(
        "compose_and_run",
        aliases=["/compose_and_run"],
        help="프로필과 사용자 입력을 받아 합성 파이프라인을 실행합니다.",
    )
    compose_parser.add_argument(
        "-f",
        "--file",
        metavar="PATH",
        help="ComposeAndRunRequest JSON이 담긴 파일 경로",
    )
    compose_parser.add_argument(
        "-d",
        "--data",
        metavar="JSON",
        help="직접 전달할 ComposeAndRunRequest JSON 문자열",
    )
    compose_parser.add_argument(
        "--pretty",
        action="store_true",
        help="응답을 들여쓰기된 JSON으로 출력",
    )
    compose_parser.set_defaults(func=handle_compose_and_run)

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
