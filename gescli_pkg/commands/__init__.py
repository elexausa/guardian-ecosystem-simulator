##################
## GES Commands ##
##################

class DaemonCommand:
    RUN = '{"command": "run"}'
    RUN_WITH_TIME_LIMIT = '{{"command": "run", "time":{time}}}'
    KILL = '{"command": "kill"}'
    SPAWN_VALVE = '{{"command": "spawn_valve_controller", "count": {number}}}'
    SPAWN_LEAK_DETECTOR = '{{"command": "spawn_leak_detector", "count": {number}}}'
    PAIR_LEAK_DETECTOR = '{{"command": "pair_leak_detector", "parent_uuid": "{parent}", "child_uuid": "{uuid}"}}'
    LIST = '{{"command": "list", "type": "{type}"}}'

