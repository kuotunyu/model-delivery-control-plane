from __future__ import annotations

import ast
import inspect
from collections import deque
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import field as dataclass_field
from functools import partial
from pathlib import Path
from types import MappingProxyType, ModuleType

import pytest

import mdcp.temporal.cli as cli
import mdcp.temporal.run_evidence as run_evidence
import mdcp.temporal.runner as runner
import mdcp.temporal.search_identity as search_identity
from mdcp.temporal.run_evidence import FormalDevelopmentOutcome
from mdcp.temporal.trials import build_estimator
from mdcp.workload.dataset import load_uci_development_archive
from mdcp.workload.splits import split_development_rows

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
        "_WindowsDispositionInformation",
        "_WindowsFileInformation",
        "_WindowsIoStatusBlock",
        "_WindowsIoStatusValue",
        "_WindowsObjectAttributes",
        "_WindowsUnicodeString",
        "_canonical_base64_decoded_size",
        "_canonical_private_container",
        "_checked_in_schema",
        "_exact_keys",
        "_failed_result",
        "_inventory_core",
        "_is_canonical_logical_path",
        "_is_windows_alias_component",
        "_manifest_core",
        "_private_container_failure",
        "_read_private_container_once",
        "_read_private_container_posix",
        "_read_private_container_windows",
        "_recovery_leaf",
        "_seal_check",
        "_valid_fold_digest",
        "_valid_fold_document",
        "_valid_natural_container",
        "_valid_ranking_key",
        "_valid_sha256",
        "_valid_source_identity",
        "_valid_winner",
        "_validated_private_files",
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
        "DevelopmentRunBundle",
        "DevelopmentRunError",
        "FitBudgetError",
        "FitLedger",
        "FitPhase",
        "FitRecord",
        "_DevelopmentFoldResult",
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
_FORBIDDEN_NAMED_AUTHORITIES = frozenset(
    {
        "FormalRunPermit",
        "activate_formal_run",
        "canonical_natural_container",
        "claim_formal_run",
        "consume_formal_run_authorization",
        "consume_marker",
        "encode_natural",
        "formal_operation",
        "preflight_pair",
        "publish_private",
        "publish_terminal",
        "write_formal_bundle_no_clobber",
    }
)
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))
_EMPTY_DATACLASS_METADATA = dataclass_field().metadata
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
_FORBIDDEN_REACHABLE_CAPABILITIES = (
    load_uci_development_archive,
    split_development_rows,
    build_estimator,
)


def _native_type_metadata(value: type, name: str) -> object:
    descriptor = vars(type)[name]
    assert inspect.isgetsetdescriptor(descriptor)
    return descriptor.__get__(value, type(value))


def _native_builtin_descriptor_value(value: object, owner: type, name: str) -> object:
    descriptor = vars(owner)[name]
    assert inspect.isgetsetdescriptor(descriptor) or inspect.ismemberdescriptor(descriptor)
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


def _native_named_descriptor(value: object, name: str) -> object | None:
    for class_state in _native_type_metadata(type(value), "__mro__"):
        descriptor = vars(class_state).get(name)
        if inspect.isgetsetdescriptor(descriptor) or inspect.ismemberdescriptor(descriptor):
            return descriptor
    return None


def _named_identity(value: object) -> str | None:
    descriptor = _native_named_descriptor(value, "__name__")
    if descriptor is None:
        return None
    try:
        name = descriptor.__get__(value, type(value))
    except AttributeError:
        return None
    return name if isinstance(name, str) else None


def _named_reachability(roots: tuple[object, ...]) -> tuple[object, ...]:
    """Traverse named state, deliberately excluding function closure cells."""
    pending: deque[object] = deque(roots)
    visited: dict[int, object] = {}
    while pending:
        value = pending.popleft()
        identity = id(value)
        if identity in visited:
            continue
        visited[identity] = value
        if inspect.ismodule(value):
            if any(value is module for module in _TRUSTED_MODULES):
                pending.extend(vars(value).values())
            continue
        if inspect.ismethod(value):
            pending.append(value.__self__)
            pending.append(value.__func__)
            continue
        if inspect.isfunction(value):
            pending.extend(value.__defaults__ or ())
            pending.extend((value.__kwdefaults__ or {}).values())
            pending.append(value.__annotations__)
            pending.extend(vars(value).values())
            continue
        if isinstance(value, property):
            pending.extend(
                accessor
                for accessor in (
                    _native_builtin_descriptor_value(value, property, "fget"),
                    _native_builtin_descriptor_value(value, property, "fset"),
                    _native_builtin_descriptor_value(value, property, "fdel"),
                )
                if accessor is not None
            )
            continue
        if isinstance(value, staticmethod | classmethod):
            owner = staticmethod if isinstance(value, staticmethod) else classmethod
            pending.append(_native_builtin_descriptor_value(value, owner, "__func__"))
            continue
        if inspect.isclass(value):
            for class_state in _native_type_metadata(value, "__mro__"):
                pending.extend(vars(class_state).values())
            continue
        if isinstance(value, dict):
            mapping_items = tuple(dict.items(value))
            pending.extend(key for key, _ in mapping_items)
            pending.extend(item for _, item in mapping_items)
            continue
        if type(value) is _MAPPING_PROXY_TYPE:
            if value is _EMPTY_DATACLASS_METADATA:
                continue
            raise AssertionError("UNINSPECTABLE_MAPPING_PROXY")
        container_owner = next(
            (owner for owner in (list, tuple, set, frozenset, deque) if isinstance(value, owner)),
            None,
        )
        if container_owner is not None:
            pending.extend(container_owner.__iter__(value))
            continue
        if type(value) in {str, bytes, int, float, complex, bool, type(None)}:
            continue
        instance_state = None
        instance_dict_descriptor = _native_named_descriptor(value, "__dict__")
        if instance_dict_descriptor is not None:
            with suppress(AttributeError):
                instance_state = instance_dict_descriptor.__get__(value, type(value))
        if isinstance(instance_state, Mapping):
            pending.append(instance_state)
        inspectable_mapping_state = isinstance(instance_state, Mapping)
        for class_state in _native_type_metadata(type(value), "__mro__"):
            class_values = vars(class_state)
            pending.extend(class_values.values())
            for slot_descriptor in class_values.values():
                if not inspect.ismemberdescriptor(slot_descriptor):
                    continue
                with suppress(AttributeError):
                    pending.append(slot_descriptor.__get__(value, type(value)))
                    inspectable_mapping_state = True
        if isinstance(value, Mapping) and not inspectable_mapping_state:
            raise AssertionError("UNINSPECTABLE_MAPPING_STATE")
    return tuple(visited.values())


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
    nonlocal_names = {
        name for node in ast.walk(factory) if isinstance(node, ast.Nonlocal) for name in node.names
    }
    assert nonlocal_names == {"exit_attempted", "pre_seal_attempted"}

    nested_functions = {
        node.name
        for node in factory.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert {"write_synthetic", "execute", "formal_operation"}.issubset(nested_functions)
    factory_returns = [node for node in factory.body if isinstance(node, ast.Return)]
    assert len(factory_returns) == 1
    returned = factory_returns[0].value
    assert isinstance(returned, ast.Tuple)
    assert tuple(element.id for element in returned.elts if isinstance(element, ast.Name)) == (
        "write_synthetic",
        "execute",
    )
    assert len(returned.elts) == 2

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
    assert len(target) == 1 and isinstance(target[0], ast.Tuple)
    assert tuple(element.id for element in target[0].elts if isinstance(element, ast.Name)) == (
        "write_synthetic_bundle_no_clobber",
        "execute_authorized_formal_development",
    )
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
        exact_factory_return = (
            isinstance(parent, ast.Tuple)
            and factory_parents.get(parent) is factory_returns[0]
            and reference.id in {"write_synthetic", "execute"}
        )
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


def test_runner_exposes_no_module_reachable_execution_authority() -> None:
    assert _FORBIDDEN_RUNNER_AUTHORITIES.isdisjoint(vars(runner))


def test_named_reachability_rejects_callback_loader_and_fit_capabilities() -> None:
    reachable = _named_reachability(
        (
            runner,
            run_evidence.write_synthetic_bundle_no_clobber,
            run_evidence.execute_authorized_formal_development,
        )
    )
    reachable_names = {name for value in reachable if (name := _named_identity(value)) is not None}
    assert _FORBIDDEN_RUNNER_AUTHORITIES.isdisjoint(reachable_names)
    reachable_identities = {id(value) for value in reachable}
    assert all(
        id(capability) not in reachable_identities
        for capability in _FORBIDDEN_REACHABLE_CAPABILITIES
    )


@pytest.mark.parametrize("sink", ("alias", "default", "class", "registry"))
def test_reachability_proof_detects_actual_fit_capability_through_named_sinks(
    sink: str,
) -> None:
    def holder(default: object = build_estimator) -> object:
        return default

    class ReturnedState:
        fit = build_estimator

    roots = {
        "alias": ({"natural_fit": build_estimator},),
        "default": (holder,),
        "class": (ReturnedState(),),
        "registry": ({"registry": {"fit": build_estimator}},),
    }[sink]
    assert build_estimator in _named_reachability(roots)


def test_runner_has_no_module_level_callback_invocation() -> None:
    source = (REPOSITORY_ROOT / "src/mdcp/temporal/runner.py").read_text(encoding="utf-8")
    assert _module_level_invoked_parameters(source) == ()


def test_callback_invocation_proof_rejects_spelling_independent_mutation() -> None:
    source = (REPOSITORY_ROOT / "src/mdcp/temporal/runner.py").read_text(encoding="utf-8")
    mutated = source + "\ndef transformed(action):\n    return action()\n"
    assert _module_level_invoked_parameters(mutated) == (("transformed", "action"),)


def test_named_reachability_has_no_intermediate_or_raw_publication_authority() -> None:
    invalid_outcome = run_evidence.execute_authorized_formal_development(object())
    parser = cli.build_parser()
    reachable = _named_reachability((*_TRUSTED_MODULES, invalid_outcome, parser))
    reachable_names = {name for value in reachable if (name := _named_identity(value)) is not None}
    assert reachable_names.isdisjoint(_FORBIDDEN_NAMED_AUTHORITIES)
    assert not hasattr(run_evidence, "_make_evidence_mutation_surface")
    assert not hasattr(run_evidence, "_MUTATION_BINDINGS")
    assert invalid_outcome == FormalDevelopmentOutcome(
        verdict="FAIL",
        reason_codes=("FORMAL_RUN_REQUEST_INVALID",),
        private_identity=None,
        seal_record_sha256=None,
        repository_inventory_sha256=None,
        authorization_sha256="0" * 64,
        consumption_marker_sha256=None,
        fit_count=0,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def test_reachability_proof_traverses_function_attribute_registries() -> None:
    def publish_private() -> None:
        return None

    def holder() -> None:
        return None

    holder.registry = {"writer": publish_private}  # type: ignore[attr-defined]
    reachable_names = {
        name
        for value in _named_reachability((holder,))
        if (name := getattr(value, "__name__", None)) is not None
    }
    assert "publish_private" in reachable_names


def test_reachability_proof_traverses_function_annotations() -> None:
    def publish_private() -> None:
        return None

    def holder() -> None:
        return None

    holder.__annotations__["writer"] = publish_private
    assert publish_private in _named_reachability((holder,))


def test_reachability_proof_rejects_opaque_mapping_proxy_registries() -> None:
    def publish_private() -> None:
        return None

    registry = MappingProxyType({"writer": publish_private})
    with pytest.raises(AssertionError, match="UNINSPECTABLE_MAPPING_PROXY"):
        _named_reachability((registry,))


def test_reachability_proof_does_not_execute_mapping_proxy_backing_code() -> None:
    backing_calls: list[str] = []

    class TrapMapping(Mapping[str, object]):
        def __getitem__(self, key: str) -> object:
            backing_calls.append(f"getitem:{key}")
            raise KeyError(key)

        def __iter__(self) -> object:
            backing_calls.append("iter")
            return iter(("writer",))

        def __len__(self) -> int:
            backing_calls.append("len")
            return 1

    registry = MappingProxyType(TrapMapping())
    with pytest.raises(AssertionError, match="UNINSPECTABLE_MAPPING_PROXY"):
        _named_reachability((registry,))
    assert backing_calls == []


def test_reachability_proof_bypasses_dict_subclass_overrides() -> None:
    def publish_private() -> None:
        return None

    override_calls: list[str] = []

    class TrapDict(dict[str, object]):
        def items(self) -> object:
            override_calls.append("items")
            raise RuntimeError("DICT_ITEMS_OVERRIDE_EXECUTED")

    registry = TrapDict(writer=publish_private)
    assert publish_private in _named_reachability((registry,))
    assert override_calls == []


@pytest.mark.parametrize("container_type", (list, tuple, set, frozenset, deque))
def test_reachability_proof_bypasses_builtin_container_subclass_iterators(
    container_type: type,
) -> None:
    def publish_private() -> None:
        return None

    override_calls: list[str] = []

    class TrapContainer(container_type):
        def __iter__(self) -> object:
            override_calls.append("iter")
            raise RuntimeError("CONTAINER_ITER_OVERRIDE_EXECUTED")

    container = TrapContainer((publish_private,))
    assert publish_private in _named_reachability((container,))
    assert override_calls == []


def test_reachability_proof_does_not_execute_custom_dict_descriptors() -> None:
    class Trap:
        @property
        def __dict__(self) -> object:
            raise RuntimeError("DICT_DESCRIPTOR_EXECUTED")

    _named_reachability((Trap(),))


def test_named_identity_does_not_execute_custom_name_descriptors() -> None:
    class Trap:
        @property
        def __name__(self) -> str:
            raise RuntimeError("NAME_DESCRIPTOR_EXECUTED")

    assert _named_identity(Trap()) is None


def test_reachability_proof_bypasses_property_subclass_overrides() -> None:
    def publish_private() -> None:
        return None

    override_calls: list[str] = []

    class TrapProperty(property):
        @property
        def fget(self) -> object:
            override_calls.append("fget")
            raise RuntimeError("FGET_EXECUTED")

    class ReturnedState:
        writer = TrapProperty(publish_private)

    assert publish_private in _named_reachability((ReturnedState(),))
    assert override_calls == []


@pytest.mark.parametrize("descriptor_kind", ("staticmethod", "classmethod"))
def test_reachability_proof_bypasses_callable_descriptor_subclass_overrides(
    descriptor_kind: str,
) -> None:
    def publish_private() -> None:
        return None

    override_calls: list[str] = []

    class TrapStaticmethod(staticmethod):
        @property
        def __func__(self) -> object:
            override_calls.append("staticmethod")
            raise RuntimeError("FUNC_EXECUTED")

    class TrapClassmethod(classmethod):
        @property
        def __func__(self) -> object:
            override_calls.append("classmethod")
            raise RuntimeError("FUNC_EXECUTED")

    descriptor = {
        "staticmethod": TrapStaticmethod(publish_private),
        "classmethod": TrapClassmethod(publish_private),
    }[descriptor_kind]

    class ReturnedState:
        writer = descriptor

    assert publish_private in _named_reachability((ReturnedState(),))
    assert override_calls == []


def test_reachability_proof_bypasses_hostile_metaclass_mro_access() -> None:
    def publish_private() -> None:
        return None

    class HostileMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name == "__mro__":
                raise RuntimeError("MRO_DESCRIPTOR_EXECUTED")
            return super().__getattribute__(name)

    class ReturnedState(metaclass=HostileMeta):
        writer = publish_private

    assert publish_private in _named_reachability((ReturnedState,))


def test_owned_surface_bypasses_hostile_metaclass_module_access() -> None:
    class HostileMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name == "__module__":
                raise RuntimeError("MODULE_DESCRIPTOR_EXECUTED")
            return super().__getattribute__(name)

    class ReturnedState(metaclass=HostileMeta):
        pass

    module = ModuleType("external_test_module")
    type.__setattr__(ReturnedState, "__module__", module.__name__)
    module.ReturnedState = ReturnedState
    assert _owned_surface(module) == ("ReturnedState",)


def test_reachability_proof_does_not_read_untrusted_module_names() -> None:
    class TrapModule(ModuleType):
        def __getattribute__(self, name: str) -> object:
            if name == "__name__":
                raise RuntimeError("MODULE_NAME_EXECUTED")
            return super().__getattribute__(name)

    _named_reachability((TrapModule("untrusted_test_module"),))


def test_reachability_proof_traverses_parser_and_default_objects() -> None:
    def publish_private() -> None:
        return None

    parser = cli.build_parser()
    parser.set_defaults(writer=publish_private)

    class DefaultState:
        pass

    state = DefaultState()
    state.writer = publish_private

    def holder(default: object = state) -> object:
        return default

    for root in (parser, holder):
        reachable_names = {
            name
            for value in _named_reachability((root,))
            if (name := getattr(value, "__name__", None)) is not None
        }
        assert "publish_private" in reachable_names


def test_reachability_proof_traverses_returned_object_class_attributes() -> None:
    def publish_private() -> None:
        return None

    class ReturnedState:
        writer = publish_private

    reachable_names = {
        name
        for value in _named_reachability((ReturnedState(),))
        if (name := getattr(value, "__name__", None)) is not None
    }
    assert "publish_private" in reachable_names


def test_reachability_proof_traverses_directly_returned_external_classes() -> None:
    def publish_private() -> None:
        return None

    class ReturnedState:
        writer = publish_private

    ReturnedState.__module__ = "external_test_module"
    assert publish_private in _named_reachability((ReturnedState,))


@pytest.mark.parametrize("kind", ("slotted", "inherited"))
def test_reachability_proof_traverses_slotted_and_inherited_class_state(kind: str) -> None:
    def publish_private() -> None:
        return None

    class BaseState:
        writer = publish_private

    class SlottedState:
        __slots__ = ()
        writer = publish_private

    class InheritedState(BaseState):
        pass

    returned = SlottedState() if kind == "slotted" else InheritedState()
    reachable_names = {
        name
        for value in _named_reachability((returned,))
        if (name := getattr(value, "__name__", None)) is not None
    }
    assert "publish_private" in reachable_names


@pytest.mark.parametrize("primitive", (int, str))
def test_reachability_proof_traverses_primitive_subclass_state(primitive: type) -> None:
    def publish_private() -> None:
        return None

    class PrimitiveState(primitive):
        writer = publish_private

    returned = PrimitiveState()
    reachable_names = {
        name
        for value in _named_reachability((returned,))
        if (name := getattr(value, "__name__", None)) is not None
    }
    assert "publish_private" in reachable_names


def test_reachability_proof_traverses_returned_object_slot_values() -> None:
    def publish_private() -> None:
        return None

    class ReturnedState:
        __slots__ = ("writer",)

    returned = ReturnedState()
    returned.writer = publish_private
    assert publish_private in _named_reachability((returned,))


def test_reachability_proof_traverses_name_mangled_slot_values() -> None:
    def publish_private() -> None:
        return None

    class ReturnedState:
        __slots__ = ("__writer",)

        def __init__(self) -> None:
            self.__writer = publish_private

    assert publish_private in _named_reachability((ReturnedState(),))


def test_reachability_proof_traverses_c_level_member_descriptors() -> None:
    def publish_private() -> None:
        return None

    assert publish_private in _named_reachability((partial(publish_private),))


@pytest.mark.parametrize("descriptor_kind", ("property", "staticmethod", "classmethod"))
def test_reachability_proof_traverses_descriptor_owned_callables(
    descriptor_kind: str,
) -> None:
    def publish_private() -> None:
        return None

    descriptor = {
        "property": property(publish_private),
        "staticmethod": staticmethod(publish_private),
        "classmethod": classmethod(publish_private),
    }[descriptor_kind]

    class ReturnedState:
        writer = descriptor

    assert publish_private in _named_reachability((ReturnedState(),))


def test_factory_state_and_single_cli_dispatch_are_structurally_closed() -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    _assert_single_factory_and_cli_edge(run_source, cli_source)


def test_structural_proof_rejects_a_second_cli_dispatch() -> None:
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


def test_structural_proof_rejects_an_alias_cli_dispatch() -> None:
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


def test_structural_proof_rejects_an_imported_alias_cli_dispatch() -> None:
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


def test_structural_proof_rejects_a_relative_imported_alias_cli_dispatch() -> None:
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
def test_structural_proof_rejects_wildcard_cli_dispatch(module: str) -> None:
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


@pytest.mark.parametrize(
    "escape",
    (
        '    attempt_states["writer"] = publish_private\n',
        "    execute.publisher = publish_private\n",
        "    leaked_writer = publish_private\n",
        '    setattr(execute, "publisher", publish_private)\n',
        '    attempt_states.update({"writer": publish_private})\n',
        "    def leaked_writer():\n        return publish_private\n",
    ),
)
def test_factory_escape_proof_rejects_registry_attribute_and_alias_sinks(escape: str) -> None:
    run_source = (REPOSITORY_ROOT / "src/mdcp/temporal/run_evidence.py").read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "src/mdcp/temporal/cli.py").read_text(encoding="utf-8")
    needle = "    return write_synthetic, execute\n"
    assert run_source.count(needle) == 1
    mutated = run_source.replace(needle, f"{escape}{needle}", 1)
    try:
        _assert_single_factory_and_cli_edge(mutated, cli_source)
    except AssertionError:
        pass
    else:  # pragma: no cover - makes the mutation-test intent explicit
        raise AssertionError("FACTORY_AUTHORITY_ESCAPE_ACCEPTED")


def test_named_public_functions_do_not_combine_raw_natural_content_and_destination() -> None:
    content_parameters = {"bytes", "content", "natural", "payload", "raw"}
    destination_parameters = {"destination", "output", "path", "root"}
    for module in _TRUSTED_MODULES:
        for value in vars(module).values():
            if (
                not inspect.isfunction(value)
                or getattr(value, "__module__", None) != module.__name__
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
    assert tuple(function.__name__ for function in wrappers) == ("write_synthetic", "execute")
    assert tuple(function.__qualname__ for function in wrappers) == (
        "_make_evidence_mutation_surface.<locals>.write_synthetic",
        "_make_evidence_mutation_surface.<locals>.execute",
    )
    assert tuple(str(inspect.signature(function)) for function in wrappers) == (
        "(destination: 'ClosurePath', bundle: 'PrivateRunBundle') -> 'PrivateBundleIdentity'",
        "(request: 'FormalDevelopmentRequest') -> 'FormalDevelopmentOutcome'",
    )
