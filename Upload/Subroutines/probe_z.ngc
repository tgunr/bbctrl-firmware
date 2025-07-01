o<probe_z> sub

G21 G90                        ; Metric, absolute mode
F100                           ; Set feed rate
G38.2 Z[#<_z> - #<_probe_block_z>]        
G0 Z[#<_z> + 5] ; Retract 

F25
G38.2 Z[#<_z> - 6]           ; Probe down 3mm from current position
G10 L20 P1  Z[#<_probe_block_z>]
G0 Z[#<_probe_block_z> + 10] ; Retract 

o<globals> endsub
