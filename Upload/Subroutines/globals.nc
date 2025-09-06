o<globals> sub
#<_z_machine> = 163
#<_x_machine> = 1219
#<y_machine> = 816
#<_probe_block_z> = 15.444
#<_x_outer> = 62.925 ; Adjusted to give 3.175mm tool diameter with current measurements
#<_x_inner> = 54.01 ; actual measured X dimension of inner probe block
#<_y_inner> = 54.20 ; actual measured Y dimension of inner probe block (mm)
#<_y_outer> = 63.5
#<_probe_block_b> = 25    ; distance to move past block for probing (mm)
#<_fast_probe> = 100
#<_slow_probe> = 25
(LOG, GLOBALS X:#<_probe_block_x> Y:#<_probe_block_y> Z:#<_probe_block_z> B: #<_probe_block_b>)
(LOG, COORD: #<_coord_system>)
(LOG, TOOL: #<_tool_number>)
o<globals> endsub
