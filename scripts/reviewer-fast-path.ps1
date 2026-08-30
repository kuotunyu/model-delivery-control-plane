Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$before = @(git -C $repositoryRoot status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) { throw 'unable to inspect repository state' }
$previousLocation = Get-Location
$previousBytecode = $env:PYTHONDONTWRITEBYTECODE
$commandFailure = $null
$stateFailure = $null

try {
    Set-Location -LiteralPath $repositoryRoot
    $env:PYTHONDONTWRITEBYTECODE = '1'

    & uv run --no-sync python scripts/verify-public-release.py --repository-root .
    if ($LASTEXITCODE -ne 0) {
        $commandFailure = 'public release verifier failed'
    }

    if ($null -eq $commandFailure) {
        & uv run --no-sync python scripts/reviewer-demo.py --repository-root .
        if ($LASTEXITCODE -ne 0) {
            $commandFailure = 'reviewer demo failed'
        }
    }

    if ($null -eq $commandFailure) {
        & uv run --no-sync pytest -p no:cacheprovider -q `
            tests/publication/test_public_release_surface.py `
            tests/publication/test_release_workflow.py `
            tests/contract/workload/test_serving_identity_isolation.py `
            tests/contract/workload/test_serving_identity_v2.py `
            tests/unit/temporal/test_formal_worker_protocol.py `
            tests/integration/temporal/test_formal_worker_process.py `
            tests/security/temporal/test_public_evidence_boundary.py
        if ($LASTEXITCODE -ne 0) {
            $commandFailure = 'curated reviewer tests failed'
        }
    }
}
catch {
    $commandFailure = 'reviewer fast path command failed'
}
finally {
    if ($null -eq $previousBytecode) {
        Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONDONTWRITEBYTECODE = $previousBytecode
    }
    Set-Location -LiteralPath $previousLocation

    try {
        $after = @(git -C $repositoryRoot status --porcelain=v1 --untracked-files=all)
        if ($LASTEXITCODE -ne 0) {
            $stateFailure = 'unable to inspect repository state'
        }
        elseif (($before -join "`n") -ne ($after -join "`n")) {
            $stateFailure = 'reviewer fast path changed repository state'
        }
    }
    catch {
        $stateFailure = 'unable to inspect repository state'
    }
}

if ($null -ne $stateFailure) { throw $stateFailure }
if ($null -ne $commandFailure) { throw $commandFailure }

Write-Output 'PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0'
