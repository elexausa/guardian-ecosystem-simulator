##################
## GES Commands ##
##################

class DaemonCommand:
    RUN = '{"command": "run"}'
    KILL = '{"command": "kill"}'
    SPAWN_VALVE = '{{"command": "spawn_valve_controller", "count": {count}}}'
    SPAWN_LEAK_DETECTOR = '{{"command": "spawn_leak_detector", "count": {count}}}'
    PAIR_LEAK_DETECTOR = '{{"command": "pair_leak_detector", "parent_uuid": "{parent}", "child_uuid": "{uuid}"}}'
    LIST = '{{"command": "list", "type": "{type}"}}'

