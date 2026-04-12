param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Username = "admin",
    [string]$Password = "changeme-demo-only"
)

$ErrorActionPreference = "Stop"

$Session = "smoke-{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 8))
$Npx = "npx.cmd"
$CliArgs = @("--yes", "--package", "@playwright/cli", "playwright-cli", "-s=$Session")

function Invoke-PlaywrightCli {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & $Npx @CliArgs @Arguments 2>&1 | Out-String
    if ($output) {
        Write-Host $output.TrimEnd()
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Playwright CLI command failed: $($Arguments -join ' ')"
    }
    if ($output -match "### Error") {
        throw "Playwright CLI reported an error: $($Arguments[0])"
    }

    return $output
}

function Write-Step {
    param([string]$Message)
    Write-Host "[smoke] $Message"
}

function Compress-JavaScript {
    param([string]$Source)

    return (($Source -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }) -join " ")
}

function ConvertTo-JsStringLiteral {
    param([string]$Value)

    $escaped = $Value.Replace('\', '\\').Replace("'", "\'")
    return "'$escaped'"
}

$JsBaseUrl = ConvertTo-JsStringLiteral $BaseUrl
$JsUsername = ConvertTo-JsStringLiteral $Username
$JsPassword = ConvertTo-JsStringLiteral $Password

$LoginAndOverviewCheck = Compress-JavaScript @"
async (page) => {
  const baseUrl = __BASE__;
  const username = __USER__;
  const password = __PASS__;

  await page.goto(baseUrl + '/dashboard/login', { waitUntil: 'networkidle' });
  await page.getByRole('textbox', { name: 'Username' }).fill(username);
  await page.getByRole('textbox', { name: 'Password' }).fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL('**/dashboard');
  const metricsText = await page.locator('main').textContent();
  if (!metricsText.includes('Premium control for listings, leads, and integrations.') || !metricsText.includes('Properties') || !metricsText.includes('10')) {
    throw new Error('Overview metrics did not render the expected property count.');
  }
  return 'Login and overview passed';
}
"@
$LoginAndOverviewCheck = $LoginAndOverviewCheck.Replace("__BASE__", $JsBaseUrl).Replace("__USER__", $JsUsername).Replace("__PASS__", $JsPassword)

$SettingsCheck = Compress-JavaScript @"
async (page) => {
  const baseUrl = __BASE__;
  const phone = '+1-555-777-' + String(Math.floor(Math.random() * 9000) + 1000);
  await page.goto(baseUrl + '/dashboard/settings', { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'Application Settings' }).waitFor();
  await page.getByRole('textbox', { name: 'Fixed Platform Contact Number' }).fill(phone);
  await page.getByRole('button', { name: 'Save Settings' }).click();
  await page.getByText('Global settings saved.').waitFor();

  const currentValue = await page.getByRole('textbox', { name: 'Fixed Platform Contact Number' }).inputValue();
  if (currentValue !== phone) {
    throw new Error('Settings form did not persist the updated contact number.');
  }

  return 'Settings save passed: ' + phone;
}
"@
$SettingsCheck = $SettingsCheck.Replace("__BASE__", $JsBaseUrl)

$PropertiesCheck = Compress-JavaScript @"
async (page) => {
  const baseUrl = __BASE__;
  await page.goto(baseUrl + '/dashboard/properties', { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'Properties', exact: true }).waitFor();
  await page.getByRole('textbox', { name: 'City' }).fill('Houston');
  await page.getByRole('spinbutton', { name: 'Bedrooms' }).fill('3');
  await page.getByRole('button', { name: 'Apply Filters' }).click();
  await page.waitForURL('**city=Houston**');
  const rows = page.locator('tbody tr');
  const rowCount = await rows.count();
  if (rowCount !== 2) {
    throw new Error('Expected exactly 2 filtered property rows, received ' + rowCount + '.');
  }
  const text = await page.locator('tbody').textContent();
  if (!text.includes('Westbury Family Home') || !text.includes('Rice Village Townhome Lease')) {
    throw new Error('Filtered property results did not include the expected listings.');
  }

  return 'Property filtering passed';
}
"@
$PropertiesCheck = $PropertiesCheck.Replace("__BASE__", $JsBaseUrl)

$IntegrationsCheck = Compress-JavaScript @"
async (page) => {
  const baseUrl = __BASE__;
  const note = 'verified via smoke script ' + Date.now();
  await page.goto(baseUrl + '/dashboard/integrations', { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'Integration Catalog' }).waitFor();
  await page.locator('article').filter({ hasText: 'Twilio Messaging and Voice' }).getByRole('link', { name: 'Open connector settings' }).click();
  await page.getByRole('heading', { name: 'Twilio Messaging and Voice' }).waitFor();

  const secretField = page.getByRole('textbox', { name: /Auth Token/i });
  const placeholder = await secretField.getAttribute('placeholder');
  if (placeholder !== 'Saved securely in demo storage') {
    throw new Error('Secret field masking is not behaving as expected.');
  }

  await page.getByRole('textbox', { name: 'Implementation Notes' }).fill(note);
  await page.getByRole('button', { name: 'Save Connector Settings' }).click();
  await page.getByText('Twilio Messaging and Voice settings saved.').waitFor();

  const savedNote = await page.getByRole('textbox', { name: 'Implementation Notes' }).inputValue();
  if (savedNote !== note) {
    throw new Error('Connector notes were not persisted.');
  }

  return 'Integration settings passed';
}
"@
$IntegrationsCheck = $IntegrationsCheck.Replace("__BASE__", $JsBaseUrl)

try {
    Write-Step "Opening browser session $Session"
    [void](Invoke-PlaywrightCli @("open", "$BaseUrl/dashboard/login"))

    Write-Step "Checking login and overview"
    [void](Invoke-PlaywrightCli @("run-code", $LoginAndOverviewCheck))

    Write-Step "Checking settings persistence"
    [void](Invoke-PlaywrightCli @("run-code", $SettingsCheck))

    Write-Step "Checking property filters"
    [void](Invoke-PlaywrightCli @("run-code", $PropertiesCheck))

    Write-Step "Checking integration configuration flow"
    [void](Invoke-PlaywrightCli @("run-code", $IntegrationsCheck))

    Write-Step "Smoke test completed successfully"
}
finally {
    try {
        [void](Invoke-PlaywrightCli @("close"))
    }
    catch {
        Write-Warning "Failed to close Playwright session $Session"
    }
}
