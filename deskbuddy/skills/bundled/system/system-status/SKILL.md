---
name: system-status
description: Report the computer's health - battery, disk space, memory, uptime.
triggers: [battery, disk space, how much memory, system status, how is my pc, uptime]
---
# System status

When the user asks how their machine is doing, gather only what they asked for
(don't run everything). Use `run_shell` for each:

- Battery:   `cat /sys/class/power_supply/BAT*/capacity 2>/dev/null; acpi 2>/dev/null`
- Disk:      `df -h / | tail -1`
- Memory:    `free -h | awk 'NR==2{print $3 " used of " $2}'`
- Uptime:    `uptime -p`
- CPU load:  `cat /proc/loadavg | cut -d" " -f1-3`

Summarize in ONE friendly spoken sentence — you are being read aloud, so say
"you've got 42 gigs free and battery's at 80 percent", not a raw table.
