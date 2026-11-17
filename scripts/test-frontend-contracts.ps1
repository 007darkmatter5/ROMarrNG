# Offline Windows contracts; package restore is completed by the previous step.
$ErrorActionPreference = 'Stop'
New-NetFirewallRule -DisplayName ROMarrUnitTests -Direction Outbound -Action Block -Enabled True | Out-Null
try {
  foreach ($framework in @('net11.0-windows', 'net10.0-windows')) {
    dotnet run --no-restore --framework $framework --project scripts/launchbox_proof/launchbox_proof.csproj -- scripts/frontend-fixture.xml
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  & (Join-Path $PSScriptRoot 'test-playnite-sync.ps1')
} finally {
  Remove-NetFirewallRule -DisplayName ROMarrUnitTests
}
