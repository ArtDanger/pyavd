import re
import os
import shlex
import subprocess
import time

from loguru import logger

# avd_cmd = "avdmanager"
# emulator_cmd = "emulator"
emulator_cmd = r'C:\Users\King\AppData\Local\Android\Sdk\tools\emulator.exe'
avd_cmd = r'C:\Users\King\AppData\Local\Android\Sdk\cmdline-tools\latest\bin\avdmanager.bat'


class Target:
    def __init__(self, id: int, id_alias: str, name: str, type: str, api_level: int, revision: int) -> None:
        self.id = id
        self.id_alias = id_alias
        self.name = name
        self.type = type
        self.api_level = api_level
        self.revision = revision

    def isEmpty(self) -> bool:
        return self.id == -1

    def __init__(self) -> None:
        self.id = -1


class Device:
    def __init__(self, id: int, id_alias: str, name: str, oem: str, tag: str = "") -> None:
        self.id = id
        self.id_alias = id_alias
        self.name = name
        self.oem = oem
        self.tag = tag

    def isEmpty(self) -> bool:
        return self.id == -1

    def __init__(self) -> None:
        self.id = -1
        self.tag = ""


class AVD:
    def __init__(self, name: str, device: Device, path: str, target: str, skin: str, sdcard_size: str, based_on: str,
                 abi: str) -> None:
        self.adb_name_emu = None
        self.name = name
        self._device = device
        # Check if path exists
        if not os.path.isfile(path):
            raise Exception("Path does not exist")
        self.path = path
        self.target = target
        self.skin = skin
        self.sdcard_size = sdcard_size
        self.based_on = based_on
        self.abi = abi
        self.process: subprocess.Popen | None = None

    def __init__(self) -> None:
        self._device = None
        self.name = "invalid"
        self.process: subprocess.Popen | None = None

    def isEmpty(self) -> bool:
        return self.name == "invalid"

    @property
    def device(self) -> Device | None:
        return self._device

    @device.getter
    def device(self) -> Device | None:
        return self._device

    @device.setter
    def device(self, device: str):
        # Remove everything inside the parentheses so we can actually compare it
        device = re.sub("[\(\[].*?[\)\]]", "", device).strip()
        # Find the corrent device to the string
        for d in get_devices():
            if d.id_alias == device:
                self._device = d
                return

    def delete(self) -> bool:
        """
        Delete the AVD
        """
        pattern = r"self.adb_name_emu"
        matches = True

        while matches:
            cmd_args = ['adb', 'devices']
            res = subprocess.run(
                cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if res.stdout:
                logger.info(res)
            else:
                logger.error(res.stderr)
                break

            matches = re.findall(pattern, res.stdout)  # return list

        try:
            cmd_args = [avd_cmd, "delete", "avd", "-n", self.name]
            res = subprocess.run(
                cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise Exception("Could not find avdmanager")
        return res.stdout and not res.stderr

    # def move(self, new_path: str) -> bool:
    #     """
    #     NOT IMPLEMENTED\n
    #     Move the AVD to a new path
    #
    #     Args:
    #         new_path (str): New path to move the AVD to
    #
    #     Raises:
    #         Exception: If avdmanager is not found
    #
    #     Returns:
    #         bool: True if the move was successful, False otherwise
    #     """
    #     raise NotImplementedError()
    #     return False

    def rename(self, new_name: str) -> bool:
        """
        Rename the AVD

        Args:
            new_name (str): New name for the AVD

        Raises:
            Exception: If avdmanager is not found

        Returns:
            bool: True if the rename was successful, False otherwise
        """
        cmd_args = [avd_cmd, "move", "avd", "-n", self.name, "-r", new_name]
        try:
            res = subprocess.run(
                cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise Exception("Could not find avdmanager")
        if res.stdout and not res.stderr:
            # Correct the filename and filepath to the new filename and path
            self.name = new_name
            self.path = os.path.join(os.path.dirname(
                os.path.abspath(self.path)), self.name + ".avd")
            return True
        return False

    def start(self, detach=False, config="") -> subprocess.Popen:
        """
        Start the AVD

        Args:
            detach (bool, optional): Detach process. Defaults to False.
            config (str, optional): Custom config string. Defaults to "".

        Raises:
            Exception: If emulator is not found
            e: If the emulator times out

        Returns:
            subprocess.Popen: The process of the emulator
        """
        proc = None

        cmd_args = [emulator_cmd, "-avd", self.name]
        if config:
            cmd_args += shlex.split(config)
            logger.info(cmd_args)
        try:
            proc = subprocess.Popen(
                cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # The emulator needs a second to load, so we wait a second if we want to detach
            if detach:
                proc.wait(1)
            else:
                proc.wait()
        except OSError:
            raise Exception("Could not find emulator")
        except subprocess.TimeoutExpired as e:
            if not detach:
                raise e
        self.process: subprocess.Popen = proc
        return proc

    def stop(self, port) -> bool:
        """
        Stop the AVD

        Returns:
            bool: True if the AVD was stopped, False otherwise
        """
        if not self.process:
            logger.error("AVD is not found")
            return False

        self.process.kill()
        # Wait for zombie process to exit
        self.process.wait()

        self.adb_name_emu = "emulator-" + port
        cmd_args = ['adb', '-s', self.adb_name_emu, 'emu', 'kill']
        logger.info(f'command for stop emulator {cmd_args}')
        try:
            res = subprocess.run(
                cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            logger.info(res)

        except OSError:
            raise Exception(f"Could not find {self.name}")

        self.process = None
        return True


def get_targets() -> list[Target]:
    """
    Get a list of all available targets

    Raises:
        Exception: If avdmanager is not found

    Returns:
        list[Target]: List of all available targets
    """
    cmd_args = [avd_cmd, "list", "target"]
    try:
        res = subprocess.run(
            cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise Exception("Could not find avdmanager")

    targets = []
    # Parse devices from output
    if res.stdout:
        current_target = Target()
        for line in res.stdout.decode("utf-8").split("\n"):
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # If "----------" is seen a new target definition begins
            # So we add the old current target and overwrite it
            if stripped_line == "----------":
                if not current_target.isEmpty():
                    targets.append(current_target)
                current_target = Target()
                continue

            # If there is no : in the line, its not a valid key value pair
            if ":" not in stripped_line:
                continue

            key, value = stripped_line.split(":")
            key = key.strip().upper()
            value = value.strip()
            if key == "id".upper():
                id, alias = value.split(" or ")
                current_target.id = int(id.strip())
                current_target.id_alias = alias.strip().replace('"', '')
            elif key == "Name".upper():
                current_target.name = value
            elif key == "Type".upper():
                current_target.type = value
            elif key == "API Level".upper():
                current_target.api_level = int(value)
            elif key == "Revision".upper():
                current_target.revision = int(value)

        # Add the last target
        if not current_target.isEmpty():
            targets.append(current_target)
    return targets


def get_devices() -> list[Device]:
    """
    Get a list of all available devices

    Raises:
        Exception: If avdmanager is not found

    Returns:
        list[Device]: List of all available devices
    """
    cmd_args = [avd_cmd, "list", "device"]
    try:
        res = subprocess.run(
            cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise Exception("Could not find avdmanager")

    devices = []
    # Parse devices from output
    if res.stdout:
        current_device = Device()
        for line in res.stdout.decode("utf-8").split("\n"):
            stripped_line = line.strip()
            if not stripped_line:
                continue
            # If "---------" is seen a new target definition begins
            # So we add the old current target and overwrite it
            if stripped_line == "---------":
                if not current_device.isEmpty():
                    devices.append(current_device)
                current_device = Device()
                continue

            # If there is no : in the line, its not a valid key value pair
            if ":" not in stripped_line or stripped_line.count(":") > 2:
                continue
            key, value = stripped_line.split(":")
            key = key.strip().upper()
            value = value.strip()

            if key == "id".upper():
                id, alias = value.split(" or ")
                current_device.id = int(id.strip())
                current_device.id_alias = alias.strip().replace('"', '')
            elif key == "Name".upper():
                current_device.name = value
            elif key == "OEM".upper():
                current_device.oem = value
            elif key == "Tag".upper():
                current_device.tag = value

        # Append last device
        if not current_device.isEmpty():
            devices.append(current_device)

    return devices


def get_avds() -> list[AVD]:
    """
    Get a list of all available AVDs

    Raises:
        Exception: If avdmanager is not found

    Returns:
        list[AVD]: List of all available AVDs
    """
    cmd_args = [avd_cmd, "list", "avd"]
    try:
        res = subprocess.run(
            cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise Exception("Could not find avdmanager")

    avds = []
    # Parse avds from output
    if res.stdout:
        current_avd = AVD()
        for line in res.stdout.decode("utf-8").split("\n"):
            stripped_line = line.strip()
            if not stripped_line:
                continue
            # If "---------" is seen a new target definition begins
            # So we add the old current target and overwrite it
            if stripped_line == "---------":
                if not current_avd.isEmpty():
                    avds.append(current_avd)
                current_avd = AVD()
                continue

            # If there is no : in the line, its not a valid key value pair
            if ":" not in stripped_line:
                continue

            key, value, *rest = stripped_line.split(":")
            key = key.strip().upper()
            value = value.strip()
            if key == "Name".upper():
                current_avd.name = value
            elif key == "Device".upper():
                current_avd.device = value
            elif key == "Path".upper():
                current_avd.path = value
            elif key == "Target".upper():
                current_avd.target = value
            elif key == "Skin".upper():
                current_avd.skin = value
            elif key == "Sdcard".upper():
                current_avd.sdcard_size = value
            elif key == "Based on".upper():
                # Based on: Android 12L (Sv2) Tag/ABI: google_apis/x86_64
                current_avd.based_on = value.replace("Tag/ABI", "").strip()
                current_avd.abi = rest[0].strip()

        # Append last avd
        if not current_avd.isEmpty():
            avds.append(current_avd)

    return avds


def get_avd_by_name(name: str) -> AVD:
    for avd in get_avds():
        if avd.name == name:
            return avd
    logger.error(f"AVD {name} not found")
    return None


def create_avd(name: str, package: str, device: Device, force: bool = False, sdcard: str = None, tag: str = None,
               skin: str = None, abi: str = None, path: str = None) -> AVD:
    """
    Create a new AVD with the given name and package

    Args:
        name (str): Name of the new AVD
        package (str): Package path of the system image for this AVD (e.g. 'system-images;android-19;google_apis;x86')
        device (str): The device which the emulator is based on
        force (bool, optional): Forces creation (overwrites an existing AVD). Defaults to False.
        sdcard (str, optional): Path to a shared SD card image, or size of a new sdcard for the new AVD. Defaults to None.
        tag (str, optional): The sys-img tag to use for the AVD. The default is to auto-select if the platform has only one tag for its system images. Defaults to None.
        skin (str, optional): Skin of the AVD. Defaults to None.
        abi (str, optional): The ABI to use for the AVD. The default is to auto-select the ABI if the platform has only one ABI for its system images. Defaults to None.
        path (str, optional): Directory where the new AVD will be created. Defaults to None.

    Raises:
        Exception: If avdmanager is not found

    Returns:
        AVD: The newly created AVD
    """
    inclusion_dict = {
        "--sdcard": sdcard,
        "--tag": tag,
        "--skin": skin,
        "--abi": abi,
        "--path": path,
    }
    cmd_args = [avd_cmd, "create", "avd", "-n",
                name, "--package", package, "--device", str(device.id)]
    for key, value in inclusion_dict.items():
        if value:
            cmd_args.append(key)
            cmd_args.append(str(value))

    if force:
        cmd_args += ["--force"]

    logger.info(cmd_args)
    try:
        subprocess.run(
            cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise Exception("Could not find avdmanager")
    return get_avd_by_name(name)
