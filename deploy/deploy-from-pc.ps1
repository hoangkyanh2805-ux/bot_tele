# Deploy config + start bot tren VPS tu may Windows (1 lenh)
param(
    [string]$VpsHost = "103.97.126.28",
    [int]$Port = 2018,
    [string]$User = "root",
    [string]$Password = "",
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent)
)

if (-not $Password) {
    $Password = Read-Host "Password VPS root" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
    $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

$envFile = Join-Path $ProjectRoot ".env"
$mapFile = Join-Path $ProjectRoot "mappings.json"
$finishSh = Join-Path $PSScriptRoot "finish-vps.sh"

if (-not (Test-Path $envFile)) { throw "Thieu .env" }
if (-not (Test-Path $mapFile)) { throw "Thieu mappings.json" }

$py = @"
import paramiko, sys
host, port, user, password = sys.argv[1:5]
env_path, map_path, finish_path = sys.argv[5:8]
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Ket noi {user}@{host}:{port} ...")
client.connect(host, port=int(port), username=user, password=password, timeout=30)
sftp = client.open_sftp()
for local, remote in [(env_path, "/opt/bot_tele/.env"), (map_path, "/opt/bot_tele/mappings.json")]:
    sftp.put(local, remote)
    print(f"Uploaded {remote}")
with sftp.file("/tmp/finish-vps.sh", "w") as f:
    f.write(open(finish_path, encoding="utf-8").read())
sftp.chmod("/tmp/finish-vps.sh", 0o755)
sftp.close()
_, out, err = client.exec_command("bash /tmp/finish-vps.sh", timeout=120)
print(out.read().decode("utf-8", "replace"))
e = err.read().decode("utf-8", "replace")
if e.strip():
    print(e, file=sys.stderr)
code = out.channel.recv_exit_status()
client.close()
sys.exit(code)
"@

$pyFile = Join-Path $env:TEMP "vps_deploy.py"
Set-Content -Path $pyFile -Value $py -Encoding UTF8
python $pyFile $VpsHost $Port $User $Password $envFile $mapFile $finishSh
