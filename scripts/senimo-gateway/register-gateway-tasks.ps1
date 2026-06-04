# Register MOBILMAJAK camera gateway scheduled tasks (ASCII only)
# Compatible with Windows PowerShell 5.1 / older Task Scheduler
# Main task: runs gateway supervisor
# Wake kick task: restarts main task after sleep / logon

function New-GatewayPeriodicTrigger {
    param(
        [int]$IntervalMinutes = 30
    )
    $start = (Get-Date).AddMinutes(1)
    $trigger = New-ScheduledTaskTrigger -Once -At $start
    $repClass = Get-CimClass -Namespace Root/Microsoft/Windows/TaskScheduler -ClassName MSFT_TaskRepetitionPattern
    $trigger.Repetition = New-CimInstance -CimClass $repClass -ClientOnly -Property @{
        Interval = "PT${IntervalMinutes}M"
        Duration = 'P3650D'
        StopAtDurationEnd = $false
    }
    return $trigger
}

function Register-MobilmajakGatewayTasks {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskName,
        [Parameter(Mandatory = $true)]
        [string]$RunScript,
        [Parameter(Mandatory = $true)]
        [string]$WakeKickScript,
        [string]$StartupDelay = 'PT30S'
    )

    $wakeKickTaskName = "$TaskName-WakeKick"

    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`""

    $triggers = @()

    $boot = New-ScheduledTaskTrigger -AtStartup
    $boot.Delay = $StartupDelay
    $triggers += $boot

    $triggers += New-ScheduledTaskTrigger -AtLogOn
    $triggers += New-GatewayPeriodicTrigger -IntervalMinutes 30

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
        -RestartInterval (New-TimeSpan -Minutes 5) `
        -RestartCount 999 `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $triggers `
        -Settings $settings `
        -RunLevel Highest `
        -Force | Out-Null

    $kickAction = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WakeKickScript`" -TaskName `"$TaskName`""

    $kickTriggers = @()
    $kickTriggers += New-ScheduledTaskTrigger -AtLogOn

    # Wake from sleep: Power-Troubleshooter event ID 1
    try {
        $wakeSub = @'
<QueryList>
  <Query Id="0" Path="System">
    <Select Path="System">*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]</Select>
  </Query>
</QueryList>
'@
        $eventClass = Get-CimClass -Namespace Root/Microsoft/Windows/TaskScheduler -ClassName MSFT_TaskEventTrigger
        $wakeEvent = New-CimInstance -CimClass $eventClass -ClientOnly -Property @{
            Subscription = $wakeSub
            Enabled = $true
        }
        $kickTriggers += $wakeEvent
    } catch {
        Write-Warning "Wake event trigger skipped (logon trigger still active): $_"
    }

    $kickSettings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $wakeKickTaskName `
        -Action $kickAction `
        -Trigger $kickTriggers `
        -Settings $kickSettings `
        -RunLevel Highest `
        -Force | Out-Null
}
