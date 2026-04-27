$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
uv --directory $root run freshdesk-mcp
