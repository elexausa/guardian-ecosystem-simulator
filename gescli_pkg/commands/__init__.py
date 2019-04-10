##################
## GES Commands ##
##################

class DaemonCommand:
    RUN = '{"command": "run"}'
    KILL = '{"command": "kill"}'
    SPAWN = '{{"command": "spawn", "type": "{type}", "count": {count}, "data": "{data}"}}'
    LIST = '{{"command": "list", "type": "{type}"}}'

