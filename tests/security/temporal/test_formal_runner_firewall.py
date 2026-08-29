from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

import mdcp.temporal.cli as cli
import mdcp.temporal.run_evidence as run_evidence
import mdcp.temporal.runner as runner
import mdcp.temporal.search_identity as search_identity

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_TRUSTED_MODULES = (cli, run_evidence, runner, search_identity)
_EXPECTED_OWNED_SURFACES = {
    "mdcp.temporal.cli": ("build_parser", "main"),
    "mdcp.temporal.run_evidence": (
        "ClosedMetrics",
        "DevelopmentResultCheck",
        "FormalDevelopmentOutcome",
        "FormalDevelopmentRequest",
        "FormalDevelopmentSeal",
        "FormalRunConsumptionMarker",
        "FormalSealCheck",
        "PrivateBundleIdentity",
        "PrivateContainerCheck",
        "PrivateFoldEvidence",
        "PrivateRunBundle",
        "PublicDevelopmentResult",
        "PublicFoldReceipt",
        "PublicTrialReceipt",
        "_PrivateContainer",
        "_PrivateContainerEntry",
        "_PublicationError",
        "_RepositorySnapshot",
        "_SupervisorLaunch",
        "_WindowsDispositionInformation",
        "_WindowsFileInformation",
        "_WindowsIoStatusBlock",
        "_WindowsIoStatusValue",
        "_WindowsObjectAttributes",
        "_WindowsUnicodeString",
        "_WorkerLaunchFailed",
        "_WorkerProcessUnknown",
        "_accept_worker_response",
        "_canonical_base64_decoded_size",
        "_canonical_existing_path",
        "_canonical_private_container",
        "_canonical_windows_string",
        "_checked_in_schema",
        "_current_python_executable",
        "_exact_keys",
        "_failed_result",
        "_formal_worker_inventory",
        "_git_bytes",
        "_inventory_core",
        "_is_canonical_logical_path",
        "_is_windows_alias_component",
        "_manifest_core",
        "_private_container_failure",
        "_process_failure_outcome",
        "_read_private_container_once",
        "_read_private_container_posix",
        "_read_private_container_windows",
        "_read_supervisor_file",
        "_recovery_leaf",
        "_repository_snapshot",
        "_run_fixed_worker_transport",
        "_seal_check",
        "_supervisor_preflight",
        "_valid_fold_digest",
        "_valid_fold_document",
        "_valid_natural_container",
        "_valid_ranking_key",
        "_valid_sha256",
        "_valid_source_identity",
        "_valid_winner",
        "_validated_private_files",
        "_verified_search_freeze_topology",
        "_verified_search_source_inventory",
        "_verify_private_container_raw",
        "_windows_close_read_handle",
        "_windows_private_file_information",
        "_windows_read_private_file",
        "canonical_public_result_bytes",
        "execute_authorized_formal_development",
        "verify_development_result",
        "verify_formal_development_seal",
        "verify_private_container",
        "write_synthetic_bundle_no_clobber",
    ),
    "mdcp.temporal.runner": (
        "DevelopmentFitRequest",
        "DevelopmentFoldResult",
        "DevelopmentRunBundle",
        "DevelopmentRunError",
        "DevelopmentStateMachine",
        "FitBudgetError",
        "FitLedger",
        "FitPhase",
        "FitRecord",
        "_ProcessedFold",
        "_closed_metrics",
        "_evaluate_trial",
        "_fold_evidence_sha256",
        "_formal_groups",
        "_prediction_material",
        "_private_fold_evidence",
        "_process_fold",
        "_public_result",
        "_public_trial_receipt",
        "_qualification_digest",
        "_qualification_evidence",
        "_replay_digest",
        "_valid_fold_result",
        "_valid_sha256",
    ),
    "mdcp.temporal.search_identity": (
        "SearchFreezeCheck",
        "SearchIdentityInputs",
        "SearchSourceCheck",
        "_bound_digests_recompute",
        "_fail",
        "_git",
        "_has_exact_allowlisted_additions",
        "_has_exact_search_source_head_modes",
        "_has_exact_search_source_modes",
        "_has_regular_public_evidence",
        "_is_clean_checkout",
        "_is_placeholder_commit",
        "_parse_index",
        "_parse_receipt",
        "_publish_no_clobber",
        "_read_expected_public_file",
        "_read_regular_nonlink_file",
        "_source_fail",
        "_valid_sha256",
        "build_search_receipt",
        "build_search_source_inventory",
        "prepare_search_freeze",
        "verify_search_freeze",
        "verify_search_source_inventory",
    ),
}
_FORBIDDEN_RUNNER_AUTHORITIES = frozenset(
    {
        "_FormalDevelopmentInputs",
        "_DevelopmentRunState",
        "_DevelopmentExecutionPlan",
        "_checkpoint",
        "_execute_fit",
        "_run_development_core",
        "_build_formal_execution_plan",
        "_load_formal_execution_state",
        "_fit_formal_fold",
    }
)


def _native_type_metadata(value: type, name: str) -> object:
    descriptor = vars(type)[name]
    assert inspect.isgetsetdescriptor(descriptor)
    return descriptor.__get__(value, type(value))


def _owned_surface(module: object) -> tuple[str, ...]:
    module_name = module.__name__
    return tuple(
        sorted(
            name
            for name, value in vars(module).items()
            if (inspect.isfunction(value) or inspect.isclass(value))
            and (
                value.__module__
                if inspect.isfunction(value)
                else _native_type_metadata(value, "__module__")
            )
            == module_name
        )
    )


def _module_level_invoked_parameters(source: str) -> tuple[tuple[str, str], ...]:
    tree = ast.parse(source)
    invoked: list[tuple[str, str]] = []
    for function in (
        node for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ):
        parameters = {
            argument.arg
            for argument in (
                *function.args.posonlyargs,
                *function.args.args,
                *function.args.kwonlyargs,
            )
        }
        invoked.extend(
            (function.name, node.func.id)
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in parameters
        )
    return tuple(invoked)


def _assert_single_factory_and_cli_edge(run_source: str, cli_source: str) -> None:
    run_tree = ast.parse(run_source)
    cli_tree = ast.parse(cli_source)
    factories = [
        node
        for node in run_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_make_evidence_mutation_surface"
    ]
    assert len(factories) == 1
    factory = factories[0]
    assert not any(isinstance(node, ast.Global) for node in ast.walk(factory))
    assert not any(isinstance(node, ast.Nonlocal) for node in ast.walk(factory))

    nested_functions = {
        node.name
        for node in factory.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert "write_synthetic" in nested_functions
    assert {"execute", "formal_operation", "encode_natural"}.isdisjoint(nested_functions)
    factory_returns = [node for node in factory.body if isinstance(node, ast.Return)]
    assert len(factory_returns) == 1
    returned = factory_returns[0].value
    assert isinstance(returned, ast.Name)
    assert returned.id == "write_synthetic"

    factory_assignment = [
        node
        for node in run_tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "_make_evidence_mutation_surface"
    ]
    assert len(factory_assignment) == 1
    target = factory_assignment[0].targets
    assert len(target) == 1 and isinstance(target[0], ast.Name)
    assert target[0].id == "write_synthetic_bundle_no_clobber"
    deleted = {
        target.id
        for node in run_tree.body
        if isinstance(node, ast.Delete)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert {"_make_evidence_mutation_surface", "_MUTATION_BINDINGS"}.issubset(deleted)

    for node in ast.walk(factory):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        defaults = (*node.args.defaults, *(item for item in node.args.kw_defaults if item))
        referenced = {
            child.id
            for default in defaults
            for child in ast.walk(default)
            if isinstance(child, ast.Name)
        }
        assert referenced.isdisjoint(nested_functions)
    for class_node in (node for node in factory.body if isinstance(node, ast.ClassDef)):
        assigned_names = {
            child.id
            for statement in class_node.body
            for child in ast.walk(statement)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
        }
        assert assigned_names.isdisjoint(nested_functions)

    factory_parents = {
        child: parent for parent in ast.walk(factory) for child in ast.iter_child_nodes(parent)
    }
    for reference in (
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id in nested_functions
    ):
        parent = factory_parents[reference]
        direct_callee = isinstance(parent, ast.Call) and parent.func is reference
        exact_factory_return = parent is factory_returns[0] and reference.id == "write_synthetic"
        assert direct_callee or exact_factory_return

    dispatches = [
        node
        for node in ast.walk(cli_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute_authorized_formal_development"
    ]
    assert len(dispatches) == 1
    formal_operation_references = [
        node
        for node in ast.walk(cli_tree)
        if isinstance(node, ast.Attribute) and node.attr == "execute_authorized_formal_development"
    ]
    assert formal_operation_references == [dispatches[0].func]
    imported_operation_aliases = [
        alias
        for node in ast.walk(cli_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name in {"execute_authorized_formal_development", "*"}
    ]
    assert imported_operation_aliases == []
    main = next(
        node for node in cli_tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    assert dispatches[0] in tuple(ast.walk(main))


def test_post_import_callable_and_type_surface_is_exact() -> None:
    assert {
        module.__name__: _owned_surface(module) for module in _TRUSTED_MODULES
    } == _EXPECTED_OWNED_SURFACES


def test_finite_process_boundary_has_exact_public_function_surfaces() -> None:
    import mdcp.temporal.formal_worker as formal_worker
    import mdcp.temporal.formal_worker_protocol as protocol

    def public_functions(module: object) -> tuple[str, ...]:
        return tuple(
            sorted(
                name
                for name, value in vars(module).items()
                if inspect.isfunction(value)
                and value.__module__ == module.__name__
                and not name.startswith("_")
            )
        )

    assert public_functions(cli) == ("build_parser", "main")
    assert public_functions(formal_worker) == ("main",)
    assert public_functions(protocol) == (
        "encode_formal_worker_request",
        "encode_formal_worker_response",
        "formal_worker_inventory_sha256",
        "launch_profile_sha256",
        "parse_formal_worker_request",
        "parse_formal_worker_response",
        "search_source_inventory_sha256",
        "worker_request_sha256",
    )


def test_dedicated_worker_and_supervisor_have_exact_direct_capability_edges() -> None:
    import mdcp.temporal.formal_worker as formal_worker

    supervisor_tree = ast.parse(inspect.getsource(run_evidence))
    worker_tree = ast.parse(inspect.getsource(formal_worker))

    def imported_edges(tree: ast.Module) -> set[tuple[str, str | None]]:
        edges: set[tuple[str, str | None]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                edges.update((alias.name, None) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                edges.update((node.module or "", alias.name) for alias in node.names)
        return edges

    supervisor_edges = imported_edges(supervisor_tree)
    supervisor_calls = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(supervisor_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name | ast.Attribute)
    }
    assert supervisor_edges.isdisjoint(
        {
            ("mdcp.temporal.formal_worker", None),
            ("mdcp.temporal.trials", "build_estimator"),
            ("mdcp.workload.dataset", "load_uci_development_archive"),
            ("mdcp.workload.dataset", "load_uci_archive"),
            ("mdcp.workload.splits", "split_development_rows"),
            ("mdcp.workload.splits", "open_h2"),
        }
    )
    assert supervisor_calls.isdisjoint(
        {
            "_encode_natural",
            "_execute_natural_run",
            "_fit_natural_request",
            "_publish_private",
            "build_estimator",
            "load_uci_archive",
            "load_uci_development_archive",
            "open_h2",
            "split_development_rows",
        }
    )

    worker_edges = imported_edges(worker_tree)
    assert all(
        not module.startswith(
            (
                "asyncio",
                "docker",
                "importlib",
                "multiprocessing",
                "socket",
                "subprocess",
                "torch",
            )
        )
        for module, _name in worker_edges
    )
    assert worker_edges.isdisjoint(
        {
            ("mdcp.temporal.cli", None),
            ("mdcp.temporal.run_evidence", "execute_authorized_formal_development"),
            ("mdcp.temporal.search_identity", None),
            ("mdcp.workload.dataset", "load_uci_archive"),
            ("mdcp.workload.splits", "open_h2"),
        }
    )


def test_finite_process_boundary_runner_exposes_no_named_execution_authority() -> None:
    assert _FORBIDDEN_RUNNER_AUTHORITIES.isdisjoint(vars(runner))


def test_runner_has_no_module_level_callback_invocation() -> None:
    source = (REPOSITORY_ROOT / "src/mdcp/temporal/runner.py").read_text(encoding="utf-8")
    assert _module_level_invoked_parameters(source) == ()


def test_pure_runner_has_no_open_execution_or_io_capability_surface() -> None:
    forbidden_fragments = {
        "callback",
        "path",
        "file",
        "loader",
        "estimator",
        "model",
        "builder",
        "module",
        "registry",
        "subprocess",
        "publish",
        "executor",
        "factory",
    }
    owned = (
        runner.DevelopmentFitRequest,
        runner.DevelopmentFoldResult,
        runner.DevelopmentStateMachine,
    )
    for value in owned:
        for name, member in vars(value).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            lowered = name.lower()
            assert not any(fragment in lowered for fragment in forbidden_fragments)
            if inspect.isfunction(member):
                signature = inspect.signature(member)
                for parameter in signature.parameters.values():
                    assert not any(
                        fragment in parameter.name.lower() for fragment in forbidden_fragments
                    )
                    assert parameter.default is inspect.Parameter.empty

    constructor = inspect.signature(runner.DevelopmentStateMachine)
    assert tuple(constructor.parameters) == ()
    assert not hasattr(runner, "_DevelopmentExecutionPlan")
    assert not hasattr(runner, "run_development")


def test_finite_process_boundary_rejects_direct_runner_callback_call() -> None:
    source = (REPOSITORY_ROOT / "src/mdcp/temporal/runner.py").read_text(encoding="utf-8")
    mutated = source + "\ndef pure_runner(callback):\n    return callback()\n"

    assert _module_level_invoked_parameters(mutated) == (("pure_runner", "callback"),)


def test_factory_state_and_single_cli_dispatch_are_structurally_closed() -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    _assert_single_factory_and_cli_edge(run_source, cli_source)


def test_launch_profile_keeps_process_and_git_imports_supervisor_private() -> None:
    source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            modules = (
                {alias.name for alias in node.names}
                if isinstance(node, ast.Import)
                else {node.module or ""}
            )
            top_level_modules.update(modules)
            assert modules.isdisjoint({"subprocess", "time"})
    assert "mdcp.temporal.formal_worker" not in top_level_modules


def test_finite_process_boundary_rejects_a_second_cli_dispatch() -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    mutated = (
        cli_source
        + "\ndef second_dispatch(request):\n"
        + "    return run_evidence.execute_authorized_formal_development(request)\n"
    )
    try:
        _assert_single_factory_and_cli_edge(run_source, mutated)
    except AssertionError:
        pass
    else:  # pragma: no cover - makes the mutation-test intent explicit
        raise AssertionError("SECOND_FORMAL_DISPATCH_ACCEPTED")


def test_finite_process_boundary_rejects_an_alias_cli_dispatch() -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    mutated = cli_source.replace(
        '    if outcome.verdict == "PASS":\n',
        "    dispatch = run_evidence.execute_authorized_formal_development\n"
        "    unused = dispatch(request)\n"
        '    if outcome.verdict == "PASS":\n',
        1,
    )
    assert mutated != cli_source
    try:
        _assert_single_factory_and_cli_edge(run_source, mutated)
    except AssertionError:
        pass
    else:  # pragma: no cover - makes the mutation-test intent explicit
        raise AssertionError("ALIASED_FORMAL_DISPATCH_ACCEPTED")


def test_finite_process_boundary_rejects_an_imported_alias_cli_dispatch() -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    mutated = cli_source.replace(
        "from mdcp.temporal import run_evidence  # noqa: E402\n",
        "from mdcp.temporal import run_evidence  # noqa: E402\n"
        "from mdcp.temporal.run_evidence import (  # noqa: E402\n"
        "    execute_authorized_formal_development as second_dispatch,\n"
        ")\n",
        1,
    ).replace(
        '    if outcome.verdict == "PASS":\n',
        '    unused = second_dispatch(request)\n    if outcome.verdict == "PASS":\n',
        1,
    )
    assert mutated != cli_source
    try:
        _assert_single_factory_and_cli_edge(run_source, mutated)
    except AssertionError:
        pass
    else:  # pragma: no cover - makes the mutation-test intent explicit
        raise AssertionError("IMPORTED_ALIAS_FORMAL_DISPATCH_ACCEPTED")


def test_finite_process_boundary_rejects_a_relative_imported_alias_cli_dispatch() -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    mutated = cli_source.replace(
        "from mdcp.temporal import run_evidence  # noqa: E402\n",
        "from mdcp.temporal import run_evidence  # noqa: E402\n"
        "from .run_evidence import (  # noqa: E402\n"
        "    execute_authorized_formal_development as second_dispatch,\n"
        ")\n",
        1,
    ).replace(
        '    if outcome.verdict == "PASS":\n',
        '    unused = second_dispatch(request)\n    if outcome.verdict == "PASS":\n',
        1,
    )
    assert mutated != cli_source
    try:
        _assert_single_factory_and_cli_edge(run_source, mutated)
    except AssertionError:
        pass
    else:  # pragma: no cover - makes the mutation-test intent explicit
        raise AssertionError("RELATIVE_IMPORTED_ALIAS_FORMAL_DISPATCH_ACCEPTED")


@pytest.mark.parametrize("module", ("mdcp.temporal.run_evidence", ".run_evidence"))
def test_finite_process_boundary_rejects_wildcard_cli_dispatch(module: str) -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    mutated = cli_source.replace(
        "from mdcp.temporal import run_evidence  # noqa: E402\n",
        "from mdcp.temporal import run_evidence  # noqa: E402\n"
        f"from {module} import *  # noqa: E402,F403\n",
        1,
    ).replace(
        '    if outcome.verdict == "PASS":\n',
        "    unused = execute_authorized_formal_development(request)  # noqa: F405\n"
        '    if outcome.verdict == "PASS":\n',
        1,
    )
    assert mutated != cli_source
    try:
        _assert_single_factory_and_cli_edge(run_source, mutated)
    except AssertionError:
        pass
    else:  # pragma: no cover - makes the mutation-test intent explicit
        raise AssertionError("WILDCARD_FORMAL_DISPATCH_ACCEPTED")


def test_named_public_functions_do_not_combine_raw_natural_content_and_destination() -> None:
    content_parameters = {"bytes", "content", "natural", "payload", "raw"}
    destination_parameters = {"destination", "output", "path", "root"}
    for module in _TRUSTED_MODULES:
        for value in vars(module).values():
            if (
                not inspect.isfunction(value)
                or getattr(value, "__module__", None) != module.__name__
                or value.__name__.startswith("_")
            ):
                continue
            if value is search_identity._publish_no_clobber:
                assert str(inspect.signature(value)) == "(path: 'Path', raw: 'bytes') -> 'None'"
                continue
            parameters = {name.lower() for name in inspect.signature(value).parameters}
            has_content = any(
                fragment in parameter for fragment in content_parameters for parameter in parameters
            )
            has_destination = any(
                fragment in parameter
                for fragment in destination_parameters
                for parameter in parameters
            )
            assert not (has_content and has_destination), value.__qualname__


def test_allowed_factory_results_are_only_the_two_closed_wrappers() -> None:
    wrappers = (
        run_evidence.write_synthetic_bundle_no_clobber,
        run_evidence.execute_authorized_formal_development,
    )
    assert tuple(function.__name__ for function in wrappers) == (
        "write_synthetic",
        "execute_authorized_formal_development",
    )
    assert tuple(function.__qualname__ for function in wrappers) == (
        "_make_evidence_mutation_surface.<locals>.write_synthetic",
        "execute_authorized_formal_development",
    )
    assert tuple(str(inspect.signature(function)) for function in wrappers) == (
        "(destination: 'ClosurePath', bundle: 'PrivateRunBundle') -> 'PrivateBundleIdentity'",
        "(request: 'FormalDevelopmentRequest') -> 'FormalDevelopmentOutcome'",
    )


def test_forbidden_worker_capability_has_no_command_callback_or_retry_surface() -> None:
    import mdcp.temporal.formal_worker as formal_worker

    for name in ("main", "_execute_worker_request", "_execute_natural_run"):
        function = getattr(formal_worker, name)
        parameters = set(inspect.signature(function).parameters)
        assert parameters.isdisjoint(
            {
                "callback",
                "command",
                "executor",
                "factory",
                "loader",
                "module",
                "registry",
                "retry",
                "stream",
            }
        )
