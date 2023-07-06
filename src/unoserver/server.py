import argparse
import logging
import os
import signal
import subprocess
import tempfile
import platform
from urllib import request

logger = logging.getLogger("unoserver")


class UnoServer:
    def __init__(self, interface="127.0.0.1", port="2002"):
        self.interface = interface
        self.port = port
        self.user_installation = ""

    def start(self, executable="libreoffice"):
        logger.info("Starting unoserver.")

        connection = (
            "socket,host=%s,port=%s,tcpNoDelay=1;urp;StarOffice.ComponentContext"
            % (self.interface, self.port)
        )

        # I think only --headless and --norestore are needed for
        # command line usage, but let's add everything to be safe.
        cmd = [
            executable,
            "--headless",
            "--invisible",
            "--nocrashreport",
            "--nodefault",
            "--nologo",
            "--nofirststartwizard",
            "--norestore",
            f"--accept={connection}",
        ]

        if (self.user_installation):
            cmd.append(f"-env:UserInstallation={self.user_installation}")


        logger.info("Command: " + " ".join(cmd))
        process = subprocess.Popen(cmd)

        def signal_handler(signum, frame):
            logger.info("Sending signal to LibreOffice")
            try:
                process.send_signal(signum)
            except ProcessLookupError as e:
                # 3 means the process is already dead
                if e.errno != 3:
                    raise

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Signal SIGHUP is available only in Unix systems
        if platform.system() != "Windows":
            signal.signal(signal.SIGHUP, signal_handler)

        return process

    def setUserInstallationPath(self, path):
        self.user_installation = "file://" + request.pathname2url(path)
        return

def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser("unoserver")
    parser.add_argument(
        "--interface", default="127.0.0.1", help="The interface used by the server"
    )
    parser.add_argument("--port", default="2002", help="The port used by the server")
    parser.add_argument("--daemon", action="store_true", help="Deamonize the server")
    parser.add_argument(
        "--executable",
        default="libreoffice",
        help="The path to the LibreOffice executable",
    )

    # Add UserInstallation flag
    with tempfile.TemporaryDirectory() as tmpuserdir:
        parser.add_argument("--user-installation", default=tmpuserdir, help="The path to the LibreOffice user profile")

    args = parser.parse_args()

    server = UnoServer(args.interface, args.port)

    # If run in standalone mode
    # Set the UserInstallation env
    server.setUserInstallationPath(args.user_installation)

    # If it's daemonized, this returns the process.
    # It returns 0 of getting killed in a normal way.
    # Otherwise it returns 1 after the process exits.
    process = server.start(executable=args.executable)
    pid = process.pid

    logger.info(f"Server PID: {pid}")

    if args.daemon:
        return process

    process.wait()

    try:
        # Make sure it's really dead
        os.kill(pid, 0)
        # It was killed
        return 0
    except OSError as e:
        if e.errno == 3:
            # All good, it was already dead.
            return 0
        raise


if __name__ == "__main__":
    main()
