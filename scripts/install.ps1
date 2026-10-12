# Installe (ou met à jour) NoteClaire sous Windows : télécharge la configuration, choisit un mot
# de passe, lance l'application. À relancer pour mettre à jour : rien n'est écrasé.
#
#   irm https://raw.githubusercontent.com/jogit/noteclaire/main/scripts/install.ps1 | iex
#
# Variables facultatives : NOTECLAIRE_DIR (dossier, ~\noteclaire par défaut), NOTECLAIRE_CHATGPT=oui|non
# (abonnement ChatGPT pour l'IA), NOTECLAIRE_RAW (adresse des fichiers).
# « Continue » : avec « Stop », Windows PowerShell 5 traite le moindre message d'erreur de Docker
# comme une exception, même quand la commande réussit.
$ErrorActionPreference = 'Continue'

$Raw = if ($env:NOTECLAIRE_RAW) { $env:NOTECLAIRE_RAW } else { 'https://raw.githubusercontent.com/jogit/noteclaire/main' }
$Dir = if ($env:NOTECLAIRE_DIR) { $env:NOTECLAIRE_DIR } else { Join-Path $HOME 'noteclaire' }

function Fail($message) {
    Write-Host ""
    Write-Host "X $message" -ForegroundColor Red
    throw $message
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker n'est pas installé. Installez Docker Desktop d'abord : https://docs.docker.com/desktop/setup/install/windows-install/"
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail "Il manque « docker compose » (version 2). Mettez Docker Desktop à jour." }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker est installé mais ne répond pas. Lancez Docker Desktop, attendez qu'il soit prêt, puis recommencez." }

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
Set-Location $Dir
Write-Host "Dossier de NoteClaire : $Dir"

$composeTemp = Join-Path $Dir "docker-compose.yml.tmp.$PID"
try {
    Invoke-WebRequest "$Raw/docker-compose.yml" -OutFile $composeTemp -UseBasicParsing -ErrorAction Stop
} catch {
    Remove-Item $composeTemp -Force -ErrorAction SilentlyContinue
    Fail "Téléchargement impossible : vérifiez la connexion à Internet."
}
$previousPassword = $env:APP_PASSWORD
try {
    $env:APP_PASSWORD = 'validation'
    docker compose -f $composeTemp config --quiet *> $null
    if ($LASTEXITCODE -ne 0) { throw 'configuration Compose invalide' }
    Move-Item $composeTemp 'docker-compose.yml' -Force -ErrorAction Stop
} catch {
    Remove-Item $composeTemp -Force -ErrorAction SilentlyContinue
    Fail "La configuration téléchargée est invalide ; l'ancienne installation est conservée."
} finally {
    $env:APP_PASSWORD = $previousPassword
}

function Ask($variable, $question) {
    $answer = [Environment]::GetEnvironmentVariable($variable)
    if (-not $answer) { $answer = Read-Host "$question [o/N]" }
    return $answer -match '^(o|oui|y|yes)$'
}

function New-Password {
    # RandomNumberGenerator.GetInt32 n'existe pas dans Windows PowerShell 5.1.
    $alphabet = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 32
    $result = New-Object System.Text.StringBuilder
    $limit = [Math]::Floor(256 / $alphabet.Length) * $alphabet.Length
    try {
        while ($result.Length -lt 12) {
            $generator.GetBytes($bytes)
            foreach ($byte in $bytes) {
                if ($byte -lt $limit) {
                    [void]$result.Append($alphabet[$byte % $alphabet.Length])
                    if ($result.Length -eq 12) { break }
                }
            }
        }
    } finally {
        $generator.Dispose()
    }
    return $result.ToString()
}

$Password = ''
$ChatGpt = $false
if (-not (Test-Path '.env')) {
    $Password = New-Password
    $lines = @('# Réglages de NoteClaire (voir .env.example pour les options).', "APP_PASSWORD=$Password")
    if (Ask 'NOTECLAIRE_CHATGPT' "Utiliser votre abonnement ChatGPT Plus ou Pro pour l'IA (sinon : clé OpenAI ou IA locale, à choisir ensuite) ?") {
        $lines += 'AI_PROVIDER=chatgpt'
        $ChatGpt = $true
    }
    # UTF-8 sans BOM : Docker lit mal un .env avec BOM.
    [System.IO.File]::WriteAllLines((Join-Path $Dir '.env'), $lines, (New-Object System.Text.UTF8Encoding $false))
} else {
    Write-Host 'Un fichier .env existe déjà : il est conservé (mise à jour).'
    $match = Select-String -Path '.env' -Pattern '^APP_PASSWORD=(.*)$' | Select-Object -First 1
    if ($match) { $Password = $match.Matches[0].Groups[1].Value }
    if (Select-String -Path '.env' -Pattern '^AI_PROVIDER=chatgpt\s*$' -Quiet) { $ChatGpt = $true }
}

Write-Host 'Téléchargement et démarrage (quelques minutes la première fois)...'
docker compose pull -q
if ($LASTEXITCODE -ne 0) { Write-Host '(images non téléchargées : utilisation de celles déjà présentes)' }
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Fail "Le démarrage a échoué. Si le message parle d'un port déjà utilisé, ajoutez HTTP_PORT=8081 dans $Dir\.env puis relancez cette commande."
}

$port = '8080'
$match = Select-String -Path '.env' -Pattern '^HTTP_PORT=(.*)$' | Select-Object -First 1
if ($match) { $port = $match.Matches[0].Groups[1].Value }

Write-Host 'Attente du démarrage...'
$ready = $false
for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
    try {
        Invoke-WebRequest "http://127.0.0.1:$port/api/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null
        $ready = $true
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) { Fail "NoteClaire ne répond pas. Voyez : cd $Dir ; docker compose logs" }

$url = "http://127.0.0.1:$port"
Write-Host ''
Write-Host "OK NoteClaire est prêt : $url" -ForegroundColor Green
if ($Password) { Write-Host "  Mot de passe : $Password   (gardé dans $Dir\.env)" }
if ($ChatGpt) {
    Write-Host "  Connexion ChatGPT : à faire une seule fois, depuis cet ordinateur et à l'adresse $url"
    Write-Host "  (OpenAI n'accepte que 127.0.0.1) ; ensuite tous les appareils de la maison l'utilisent."
}
Write-Host "  Mettre à jour : relancez cette commande. Arrêter : cd $Dir ; docker compose down"
Start-Process $url
