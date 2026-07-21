# Route Planner E2E Benchmark Scenario를 실행하고 결과를 JSON으로 출력하는 CLI
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from ai.route_planner.benchmark.e2e_benchmark_runner import (
    RoutePlannerE2EBenchmarkRunner,
)
from ai.route_planner.benchmark.schemas import (
    RoutePlannerE2EBenchmarkScenarioDTO,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "고정 Matrix 기반 Route Planner "
            "E2E Benchmark 실행"
        )
    )

    parser.add_argument(
        "--fixture-path",
        required=True,
    )
    parser.add_argument(
        "--output-path",
    )

    return parser.parse_args()


def load_scenario(
    fixture_path: Path,
) -> RoutePlannerE2EBenchmarkScenarioDTO:
    try:
        payload = json.loads(
            fixture_path.read_text(
                encoding="utf-8"
            )
        )
    except OSError as error:
        raise ValueError(
            "E2E Benchmark Fixture 파일을 "
            "읽을 수 없습니다: "
            f"{fixture_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            "E2E Benchmark Fixture가 "
            "유효한 JSON이 아닙니다."
        ) from error

    return (
        RoutePlannerE2EBenchmarkScenarioDTO
        .model_validate(payload)
    )


def write_result(
    result_payload: dict,
    output_path: Path | None,
) -> None:
    serialized = json.dumps(
        result_payload,
        ensure_ascii=False,
        indent=2,
    )

    if output_path is None:
        print(serialized)
        return

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        serialized + "\n",
        encoding="utf-8",
    )

    print(
        "[Route Planner E2E Benchmark 성공]"
    )
    print(
        f"결과 저장 경로: {output_path}"
    )


def main() -> int:
    args = parse_args()

    try:
        scenario = load_scenario(
            Path(args.fixture_path)
        )

        result = (
            RoutePlannerE2EBenchmarkRunner()
            .run(scenario)
        )

        write_result(
            result_payload=result.model_dump(
                mode="json"
            ),
            output_path=(
                Path(args.output_path)
                if args.output_path
                else None
            ),
        )

        return 0
    except (
        ValidationError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            "[Route Planner E2E Benchmark 실패]",
            file=sys.stderr,
        )
        print(
            str(error),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
