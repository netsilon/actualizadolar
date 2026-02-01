---
description: Creates a versioned zip backup of the current project (YYYY-MM-DD_versionXX.zip) in a _backup folder.
---

1. Create _backup directory
// turbo
powershell -Command "New-Item -ItemType Directory -Force -Path '_backup' | Out-Null"

2. Create the backup zip file
powershell -Command "$d = Get-Date -Format 'yyyy-MM-dd'; $existing = Get-ChildItem '_backup' -Filter \"$d`_version*.zip\" | Measure-Object; $v = $existing.Count + 1; $vStr = $v.ToString('00'); $name = \"_backup\$d`_version$vStr.zip\"; Write-Host \"Creating backup: $name\"; Get-ChildItem -Path * -Exclude '_backup' | Compress-Archive -DestinationPath $name -Force"
