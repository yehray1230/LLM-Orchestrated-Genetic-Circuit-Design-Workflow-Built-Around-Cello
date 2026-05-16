$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputDir = Join-Path $root "cello-run\input"
$outputDir = Join-Path $root "cello-run\output"

New-Item -ItemType Directory -Force $inputDir | Out-Null
New-Item -ItemType Directory -Force $outputDir | Out-Null

$inputWsl = (wsl -d Ubuntu wslpath -a $inputDir).Trim()
$outputWsl = (wsl -d Ubuntu wslpath -a $outputDir).Trim()

$podmanArgs = @(
    "-d", "podman-yehray1230",
    "podman", "run", "--rm", "-i",
    "-v", "${inputWsl}:/root/input",
    "-v", "${outputWsl}:/root/output",
    "docker.io/cidarlab/cello-dnacompiler:latest",
    "java", "-classpath", "/root/app.jar",
    "org.cellocad.v2.DNACompiler.runtime.Main",
    "-inputNetlist", "/root/input/and.v",
    "-userConstraintsFile", "/root/input/Eco1C1G1T1.UCF.json",
    "-inputSensorFile", "/root/input/Eco1C1G1T1.input.json",
    "-outputDeviceFile", "/root/input/Eco1C1G1T1.output.json",
    "-pythonEnv", "python",
    "-outputDir", "/root/output"
)

wsl @podmanArgs
