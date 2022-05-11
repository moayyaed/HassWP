"""
Run Home Assistant natively in Windows. Tested with:

Version 1:

- Windows 10 x64 (19044.1466)
- Python 3.9.10 x64
- Home Assistant 2022.2.0 (default_config)

Version 2:

- Windows 7 x64
- WinPython v3.8.9 x32
- Home Assistant 2021.12.10 (default_config)
"""
import os
import subprocess
import sys
from logging import FileHandler
from logging.handlers import BaseRotatingHandler

# noinspection PyPackageRequirements
from atomicwrites import AtomicWriter
from homeassistant import __main__, const, requirements, setup
from homeassistant.helpers import signal
from homeassistant.util import package

if __name__ == "__main__":
    if "--runner" not in sys.argv:
        # Run a simple daemon runner process on Windows to handle restarts
        if sys.argv[0].endswith(".py"):
            sys.argv.insert(0, "python")

        sys.argv.append("--runner")

        while True:
            try:
                subprocess.check_call(sys.argv)
                sys.exit(0)
            except KeyboardInterrupt:
                sys.exit(0)
            except subprocess.CalledProcessError as exc:
                if exc.returncode != __main__.RESTART_EXIT_CODE:
                    sys.exit(exc.returncode)

    elif (const.MAJOR_VERSION, const.MINOR_VERSION) >= (2022, 2):
        # runner arg supported only on old Hass versions
        sys.argv.remove("--runner")


def wrap_utf8(func):
    def wrap(*args, **kwargs):
        if len(args) == 5:
            return func(args[0], args[1], args[2], args[3] or "utf-8", args[4])
        kwargs["encoding"] = "utf-8"
        return func(*args, **kwargs)

    return wrap


def wrap_requirements(func):
    async def wrapper(hass, name, requirements_):
        result = await func(hass, name, requirements_)

        if name == "zha":
            # noinspection PyPackageRequirements
            from serial.urlhandler import protocol_socket

            class Serial(protocol_socket.Serial):
                out_waiting = 1

            protocol_socket.Serial = Serial

        return result

    return wrapper


def wrap_setup(func):
    async def wrapper(hass, domain, config):
        if domain == "dhcp":
            return True

        return await func(hass, domain, config)

    return wrapper


# fix timezone for Python 3.8
if not package.is_installed("tzdata"):
    package.install_package("tzdata")

# remove python version warning
# noinspection PyFinal
const.REQUIRED_NEXT_PYTHON_HA_RELEASE = None

# fix Windows encoding
AtomicWriter.__init__ = wrap_utf8(AtomicWriter.__init__)
FileHandler.__init__ = wrap_utf8(FileHandler.__init__)
BaseRotatingHandler.__init__ = wrap_utf8(BaseRotatingHandler.__init__)

# fix Windows depended core bugs
__main__.validate_os = lambda: None  # Hass v2022.2+
os.fchmod = lambda *args: None
signal.async_register_signal_handling = lambda *args: None

# fix socket for ZHA
requirements.async_process_requirements = wrap_requirements(
    requirements.async_process_requirements
)
# fix DHCP and FFmpeg components bugs
setup.async_setup_component = wrap_setup(setup.async_setup_component)

# move dependencies to main python libs folder
package.is_virtual_env = lambda: True

if __name__ == "__main__":
    sys.exit(__main__.main())