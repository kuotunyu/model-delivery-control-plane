param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ValidateOnly')]
    [string]$Mode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$workflowPath = Join-Path $repositoryRoot '.github\workflows\release-ci.yml'
$lockPath = Join-Path $repositoryRoot 'constraints\github-actions.lock'
$before = @(git -C $repositoryRoot status --porcelain=v1 --untracked-files=all)
$previousLocation = Get-Location

try {
    Set-Location -LiteralPath $repositoryRoot
    $workflow = Get-Content -LiteralPath $workflowPath -Raw
    $lockLines = @(
        Get-Content -LiteralPath $lockPath |
            Where-Object { $_ -and -not $_.StartsWith('#') -and -not $_.StartsWith('oci.') }
    )
    if ($lockLines.Count -ne 5) {
        throw 'release action lock must contain exactly five action references'
    }
    foreach ($line in $lockLines) {
        $parts = $line.Split('=', 2)
        $sha = $parts[1].Split('#', 2)[0].Trim()
        if ($sha -notmatch '^[0-9a-f]{40}$') {
            throw 'release action reference is not a full commit SHA'
        }
        if ($workflow -notmatch [regex]::Escape("$($parts[0])@$sha")) {
            throw 'release action lock and workflow differ'
        }
    }

    $stageMatches = [regex]::Matches(
        $workflow,
        '(?m)^\s+id: (build_push|supply_chain|final_manifest|validate|seal)$'
    )
    $stages = @($stageMatches | ForEach-Object { $_.Groups[1].Value })
    $expectedStages = @('build_push', 'supply_chain', 'final_manifest', 'validate', 'seal')
    if (($stages -join ',') -ne ($expectedStages -join ',')) {
        throw 'release stages are missing or out of order'
    }

    & uv run pytest tests/publication/test_release_workflow.py -q
    if ($LASTEXITCODE -ne 0) {
        throw 'release workflow contract tests failed'
    }
}
finally {
    Set-Location -LiteralPath $previousLocation
}

$after = @(git -C $repositoryRoot status --porcelain=v1 --untracked-files=all)
if (($before -join "`n") -ne ($after -join "`n")) {
    throw 'ValidateOnly changed tracked or untracked repository state'
}

Write-Output 'RELEASE-CI LOCAL PASS evidence_class=dev/test mutations=0'
Write-Output 'stages=build_push,supply_chain,final_manifest,validate,seal actions_full_sha=5'
Write-Output 'formal_candidate=blocked_until_h1_pass_and_commit_bound_input'
