# Run locally in PowerShell. Password is prompted securely and sent only over SSH stdin.
$ErrorActionPreference = 'Stop'
$oliviaSecurePassword = Read-Host 'Passwort fuer olivia@liquisto.cloud (wird nicht angezeigt)' -AsSecureString
$oliviaPasswordPointer = [IntPtr]::Zero
$oliviaProcess = $null
try {
    $oliviaPasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($oliviaSecurePassword)
    $oliviaPayload = @{
        username = 'olivia@liquisto.cloud'
        password = [Runtime.InteropServices.Marshal]::PtrToStringUni($oliviaPasswordPointer)
    } | ConvertTo-Json -Compress
    $oliviaStartInfo = [Diagnostics.ProcessStartInfo]::new()
    $oliviaStartInfo.FileName = 'ssh'
    $oliviaStartInfo.UseShellExecute = $false
    $oliviaStartInfo.CreateNoWindow = $true
    $oliviaStartInfo.RedirectStandardInput = $true
    $oliviaStartInfo.RedirectStandardOutput = $true
    $oliviaStartInfo.RedirectStandardError = $true
    $oliviaStartInfo.StandardInputEncoding = [Text.UTF8Encoding]::new($false)
    foreach ($oliviaArgument in @('-o', 'BatchMode=yes', 'root@178.105.62.169',
        'python3 /opt/liquisto-memory/20261009-communication/provision_olivia_mail_secret.py')) {
        $oliviaStartInfo.ArgumentList.Add($oliviaArgument)
    }
    $oliviaProcess = [Diagnostics.Process]::new()
    $oliviaProcess.StartInfo = $oliviaStartInfo
    $null = $oliviaProcess.Start()
    $oliviaProcess.StandardInput.Write($oliviaPayload)
    $oliviaProcess.StandardInput.Close()
    $oliviaSafeResult = $oliviaProcess.StandardOutput.ReadToEnd()
    $null = $oliviaProcess.StandardError.ReadToEnd()
    $oliviaProcess.WaitForExit()
    if ($oliviaProcess.ExitCode -ne 0) { throw 'Geschuetzte Hinterlegung fehlgeschlagen. Kein Versand aktiviert.' }
    $oliviaResult = $oliviaSafeResult | ConvertFrom-Json
    if ($oliviaResult.credentials_provisioned -ne $true) { throw 'Hinterlegung nicht bestaetigt.' }
    Write-Host 'Passwort geschuetzt auf dem Server hinterlegt. Maildienst noch nicht aktiviert.'
} finally {
    if ($oliviaPasswordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeGlobalAllocUnicode($oliviaPasswordPointer)
    }
    $oliviaPayload = $null
    if ($null -ne $oliviaProcess) { $oliviaProcess.Dispose() }
    $oliviaSecurePassword.Dispose()
}
