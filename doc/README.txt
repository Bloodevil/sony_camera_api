In this directory we attempt to record the capabilities of different cameras,
and would be grateful for user's contributions.


How To Log:
--
The examples directory contains a script 'dump_camera_capabilities.py', this
can be used as follows

$ python examples/dump_camera_capabilities.py -a

The '-a' instructs the script to report 'available' parameters, as behaviour
will change with the mode of the camera - for example when set to manual
vs. Intellegent Auto.


Modes:
--
The mode of the camera can often be set with a dial on it's body.

A record for each of the modes would be helpful:
	a5000_aperture.txt
	a5000_intellegent.txt
	a5000_manual.txt
	a5000_movie.txt
	a5000_program.txt 
	a5000_shutter.txt

If the dial is not available, the script allows the use of '-E' (Expose 
mode), '-S' (Shoot mode) and '-F' (Function mode) parameters.

For example:
$ python examples/dump_camera_capabilities.py -a -E 1


Authentication:
--
We have seen that some cameras do not perform correctly until the computer
has 'authenticated' itself.

Unfortunately some cameras seem to lock out the most basic functions, and 
this is often reported as 'camera doesn't work' or 'HTTP Error 403: Forbidden'.

For example with the QX10:
-
trying 'getAvailableCameraFunction()':
[ERROR] camera doesn't workHTTP Error 403: Forbidden
-

Sony has implemented a system where-by a developer can register for an account 
and can run functions on the camera not normally available.

The developers of this project HAVE NOT registered with Sony, but we have 
figured out how to authenticate with the camera(s), which can be done with:

$ python examples/authenticate.py

Once this action is performed, the camera is more 'co-operative'.
-
trying 'getAvailableCameraFunction()':
{'id': 1, 'result': ['Remote Shooting', ['Remote Shooting', 'Contents Transfer']]}
-


