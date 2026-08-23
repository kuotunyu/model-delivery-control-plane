from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import joblib

from mdcp.workload.dataset import load_uci_archive
from mdcp.workload.evaluation import QualityPolicy, evaluate_h1, paired_rows_from_frame
from mdcp.workload.splits import split_rows
from mdcp.workload.training import (
    create_training_receipt,
    load_model_config,
    train_fixture,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
DEFAULT_DATASET_CONTRACT = REPOSITORY_ROOT / "configs" / "workload" / "uci-bike-sharing-v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a frozen MDCP Bike fixture")
    subparsers = parser.add_subparsers(dest="command", required=True)
    train = subparsers.add_parser("train")
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--data", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    train.add_argument("--dataset-contract", type=Path, default=DEFAULT_DATASET_CONTRACT)
    evaluate = subparsers.add_parser("evaluate-h1")
    evaluate.add_argument("--stable-native", type=Path, required=True)
    evaluate.add_argument("--candidate-native", type=Path, required=True)
    evaluate.add_argument("--data", type=Path, required=True)
    evaluate.add_argument("--policy", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--dataset-contract", type=Path, default=DEFAULT_DATASET_CONTRACT)
    return parser


def _train(args: argparse.Namespace) -> int:
    dataset_contract = json.loads(args.dataset_contract.read_text(encoding="utf-8"))
    frame = load_uci_archive(args.data, dataset_contract["archive_sha256"])
    train_rows = split_rows(frame).train
    config = load_model_config(args.config)
    pipeline = train_fixture(config, train_rows)
    receipt = create_training_receipt(config, train_rows)

    args.output.mkdir(parents=True, exist_ok=False)
    joblib.dump(pipeline, args.output / "native-model.joblib", compress=3)
    (args.output / "training-receipt.json").write_text(
        json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def _evaluate_h1(args: argparse.Namespace) -> int:
    dataset_contract = json.loads(args.dataset_contract.read_text(encoding="utf-8"))
    frame = load_uci_archive(args.data, dataset_contract["archive_sha256"])
    h1 = split_rows(frame).h1
    stable = joblib.load(args.stable_native)
    candidate = joblib.load(args.candidate_native)
    rows = paired_rows_from_frame(h1, stable.predict(h1), candidate.predict(h1))
    policy = QualityPolicy.model_validate_json(args.policy.read_text(encoding="utf-8"))
    report = evaluate_h1(rows, policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"H1 {report.verdict.value} rows={report.paired_row_count}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "train":
        return _train(args)
    if args.command == "evaluate-h1":
        return _evaluate_h1(args)
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
