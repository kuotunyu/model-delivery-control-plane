[CmdletBinding()]
param(
    [ValidateSet('CgroupResource', 'LoadHarness', 'AtomicTransaction', 'StackBudget', 'All')]
    [string]$Gate = 'All',
    [string]$RuntimeRoot = 'D:\model-delivery-control-plane-runtime\wave0'
)

$ErrorActionPreference = 'Stop'
$projectName = 'mdcpwave0cgroup'
$composeFile = Join-Path $PSScriptRoot '..\compose.feasibility.yaml'
$versionsFile = Join-Path $PSScriptRoot '..\constraints\versions.env'

function Get-VersionMap {
    $versionMap = @{}
    foreach ($line in Get-Content -LiteralPath $versionsFile) {
        if (-not $line -or $line.StartsWith('#')) { continue }
        $key, $value = $line.Split('=', 2)
        $versionMap[$key] = $value
    }
    return $versionMap
}

function Get-JsonLine([object[]]$Lines, [string]$Label) {
    $jsonLine = $Lines | Where-Object { $_ -match '^\{.*\}$' } | Select-Object -Last 1
    if (-not $jsonLine) { throw "$Label did not emit JSON" }
    return $jsonLine
}

function Invoke-CgroupResourceGate {
    $existing = docker ps -a --filter "label=com.docker.compose.project=$projectName" --format '{{.ID}}'
    if ($existing) { throw 'FEAS-CGROUP-DIRTY: disposable project already exists' }
    $versions = Get-VersionMap
    $env:MDCP_PYTHON_IMAGE = $versions['PYTHON_IMAGE']
    $runStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
    $runDirectory = Join-Path $RuntimeRoot "cgroup-$runStamp"
    New-Item -ItemType Directory -Path $runDirectory | Out-Null
    $observationPath = Join-Path $runDirectory 'observation.json'
    $resetPath = Join-Path $runDirectory 'reset-capability.json'
    $resultPath = Join-Path $runDirectory 'cgroup-resource.json'

    try {
        docker compose --project-name $projectName --file $composeFile --profile cgroup build candidate
        if ($LASTEXITCODE -ne 0) { throw 'FEAS-CGROUP-BUILD' }
        docker compose --project-name $projectName --file $composeFile --profile cgroup up --detach --wait candidate
        if ($LASTEXITCODE -ne 0) { throw 'FEAS-CGROUP-CANDIDATE' }

        $candidateId = docker compose --project-name $projectName --file $composeFile ps --quiet candidate
        $candidateProcessId = docker inspect --format '{{.State.Pid}}' $candidateId
        $locatorOutput = docker run --rm --pid host --cgroupns host --network none --read-only --cap-drop ALL `
            --security-opt no-new-privileges:true --user 65534:65534 --entrypoint sh `
            $versions['PYTHON_IMAGE'] -c "cat /proc/$candidateProcessId/cgroup"
        if ($LASTEXITCODE -ne 0) { throw 'FEAS-CGROUP-LOCATOR' }
        $relativeCgroup = ($locatorOutput | Select-Object -Last 1).Split(':', 3)[2]
        $cgroupLeaf = $relativeCgroup.Trim().Split('/')[-1]
        if ($cgroupLeaf -ne $candidateId) { throw 'FEAS-CGROUP-IDENTITY-MISMATCH' }
        $env:MDCP_CGROUP_PATH = "/sys/fs/cgroup$($relativeCgroup.Trim())"

        $candidateLogs = docker compose --project-name $projectName --file $composeFile logs --no-color candidate
        $requiredPhases = @('container_start', 'model_load', 'warmup', 'scenario_end')
        foreach ($phase in $requiredPhases) {
            if (-not ($candidateLogs -match ('"phase":"' + [regex]::Escape($phase) + '"'))) {
                throw "FEAS-CGROUP-MISSING-PHASE:$phase"
            }
        }

        $resetOutput = docker compose --project-name $projectName --file $composeFile --profile cgroup `
            run --rm --no-deps reset-probe 2>&1
        [IO.File]::WriteAllLines((Join-Path $runDirectory 'reset-probe.log'), $resetOutput)
        if ($LASTEXITCODE -ne 0) { throw 'FEAS-CGROUP-RESET-PROBE' }
        $resetJson = Get-JsonLine $resetOutput 'reset probe'
        [IO.File]::WriteAllText($resetPath, $resetJson + [Environment]::NewLine)

        $observerOutput = docker compose --project-name $projectName --file $composeFile --profile cgroup `
            run --rm --no-deps observer 2>&1
        [IO.File]::WriteAllLines((Join-Path $runDirectory 'observer.log'), $observerOutput)
        if ($LASTEXITCODE -ne 0) { throw 'FEAS-CGROUP-OBSERVER' }
        $observationJson = Get-JsonLine $observerOutput 'observer'
        $observation = $observationJson | ConvertFrom-Json -AsHashtable
        $observation['fresh_candidate'] = $true
        $observation['captured_phases'] = $requiredPhases
        [IO.File]::WriteAllText(
            $observationPath,
            ($observation | ConvertTo-Json -Depth 4 -Compress) + [Environment]::NewLine
        )

        uv run python -m mdcp.feasibility.resource_probe `
            --observation $observationPath `
            --reset-capability $resetPath `
            --candidate-identity $candidateId `
            --route-revision 1 `
            --window-id wave0-cgroup-window `
            --out $resultPath
        if ($LASTEXITCODE -ne 0) { throw "FEAS-CGROUP-UNKNOWN result=$resultPath" }
        "EVIDENCE_PATH=$resultPath"
    }
    finally {
        docker compose --project-name $projectName --file $composeFile --profile cgroup `
            down --volumes --remove-orphans 2>$null | Out-Null
        Remove-Item Env:MDCP_CGROUP_PATH -ErrorAction SilentlyContinue
    }
}

switch ($Gate) {
    'CgroupResource' { Invoke-CgroupResourceGate }
    default { throw "FEAS-GATE-UNIMPLEMENTED:$Gate" }
}
