o<probe_z> sub

o<globals> call
o<log> call

#<start_z> = #<_z>
#<zworkoffset> = [#[5203 + #5220 * 20] + #5213 * #5210]
#<probe_len> = #<_z_machine> + #<zworkoffset>

(LOG, 5203: #5203 5220: #5220 5213: #5213 5210: #5210] W1: [5203 + #5220 * 20] W2: [ #5213 * #5210])
(LOG, ZO: #<zworkoffset> Z: #<_z> MZ: #<_machine_z> probe to: #<probe_len>)
;G38.2 G91 Z-55.83 F#<_fast_probe>              
;M2

G38.2 G91 Z-#<probe_len> F#<_fast_probe>              
; Back off 
G91 
G0 Z3
; Probe slow
G38.2 G91 Z-4 F#<_slow_probe>              
#<newZ> = #<_z>
G90
; Set Z to probe inset height
; G92 Z[#<_probe_block_z>]       
G10 L20 P1  Z[#<_probe_block_z>]
G0 Z[#<_probe_block_z> + 10] ; Retract 

o<probe_z> endsub
