# memory-bank.md

Building firmware for BuildBotics CNC controllers is a complex task that requires deep knowledge of the hardware and software components involved in the process.

## Guidelines
- You need root access for any files in /opt/chroot that need to be modified      
- check modified dates on built binaries to ensure they are up-to-date with their respective source files;
- after successful build, e.g. `make pkg` or `make ssh-update` or `build-camotics-arm`, commit the changes to repo
- keep memory-bank updated with findings and changes made