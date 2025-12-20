param(
	[string]$VenvPath = ".\venv",
	[string]$SpecFile = "WimPyAmp.spec",
	[string]$DistDir = ".\dist"
)

# resolve paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
# project root is parent of the winscripts folder
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
Push-Location $projectRoot
try {
	# resolve venv and spec relative to the project root
	$venvFull = Resolve-Path -LiteralPath (Join-Path $projectRoot $VenvPath) -ErrorAction SilentlyContinue
	if (-not $venvFull) {
		Write-Error "Virtualenv not found at $VenvPath relative to project root $projectRoot"
		exit 1
	}
	$python = Join-Path $venvFull "Scripts\python.exe"
	if (-not (Test-Path $python)) {
		Write-Error "Python not found at $python. Create/activate venv and install dependencies including pyinstaller."
		exit 1
	}

	$specFull = Resolve-Path -LiteralPath (Join-Path $projectRoot $SpecFile) -ErrorAction SilentlyContinue
	if (-not $specFull) {
		Write-Error "Spec file not found: $SpecFile (checked under project root)"
		exit 1
	}

	# clean previous build outputs
	if (Test-Path ".\build") { Remove-Item .\build -Recurse -Force }
	if (Test-Path ".\dist") { Remove-Item .\dist -Recurse -Force }
	if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }

	# ensure pyinstaller is available in the venv
	& $python -m pip show pyinstaller > $null 2>&1
	if ($LASTEXITCODE -ne 0) {
		Write-Output "PyInstaller not found in venv. Installing..."
		& $python -m pip install --upgrade pip
		& $python -m pip install pyinstaller
		if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install PyInstaller"; exit $LASTEXITCODE }
	}

	# run pyinstaller using the spec
	& $python -m PyInstaller --noconfirm --clean $specFull
	if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit $LASTEXITCODE }

	# move artifacts to DistDir
	New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
	Get-ChildItem -Path .\dist -File | ForEach-Object { Copy-Item $_.FullName -Destination $DistDir -Force }

	# create dated archive of contents (with retry to avoid transient file locks)
	$baseName = Split-Path -Leaf $projectRoot
	$ts = Get-Date -Format yyyyMMdd
	$archive = Join-Path $DistDir ("$baseName-$ts.zip")
	$maxAttempts = 5
	$attempt = 0
	while ($true) {
		try {
			Compress-Archive -Path (Join-Path $DistDir '*') -DestinationPath $archive -Force
			Write-Output "Created $archive"
			break
		} catch {
			$attempt++
			if ($attempt -ge $maxAttempts) {
				Write-Error "Failed to create archive after $attempt attempts: $_"
				exit 1
			}
			Write-Output "Compress-Archive failed (attempt $attempt), retrying in 2s..."
			Start-Sleep -Seconds 2
		}
	}
} finally {
	Pop-Location
}
