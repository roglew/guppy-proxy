import argparse
import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from .gui import GuppyWindow
from .proxy import ProxyClient, MessageError, ProxyThread
from .util import confirm


def load_certificates(client, path):
    client.load_certificates(os.path.join(path, "server.pem"),
                             os.path.join(path, "server.key"))


def generate_certificates(client, path):
    try:
        os.makedirs(path, 0o755)
    except os.error as e:
        if not os.path.isdir(path):
            raise e
    pkey_file = os.path.join(path, 'server.key')
    cert_file = os.path.join(path, 'server.pem')
    client.generate_certificates(pkey_file, cert_file)


def main():
    parser = argparse.ArgumentParser(description="Guppy debug flags. Don't worry about most of these")
    parser.add_argument("--binary", nargs=1, help="location of the backend binary")
    parser.add_argument("--attach", nargs=1, help="attach to an already running backend")
    parser.add_argument("--dbgattach", nargs=1, help="attach to an already running backend and also perform setup")
    parser.add_argument('--debug', help='run in debug mode', action='store_true')
    parser.add_argument('--dog', help='dog', action='store_true')
    args = parser.parse_args()

    if args.binary is not None and args.attach is not None:
        print("Cannot provide both a binary location and an address to connect to")
        exit(1)

    data_dir = os.path.join(os.path.expanduser('~'), '.guppy')

    if args.binary is not None:
        binloc = args.binary[0]
        msg_addr = None
    elif args.attach is not None or args.dbgattach:
        binloc = None
        if args.attach is not None:
            msg_addr = args.attach[0]
        if args.dbgattach is not None:
            msg_addr = args.dbgattach[0]
    else:
        msg_addr = None
        try:
            # Try to get the binary from GOPATH
            gopath = os.environ["GOPATH"]
            binloc = os.path.join(gopath, "bin", "puppy")
        except Exception:
            # Try to get the binary from ~/.guppy/puppy
            binloc = os.path.join(data_dir, "puppy")
            if not os.path.exists(binloc):
                print("Could not find puppy binary in GOPATH or ~/.guppy. Please ensure that it has been compiled, or pass in the binary location from the command line")
                exit(1)

    cert_dir = os.path.join(data_dir, "certs")

    with ProxyClient(binary=binloc, conn_addr=msg_addr, debug=args.debug) as client:
        try:
            load_certificates(client, cert_dir)
        except MessageError as e:
            print(str(e))
            if(confirm("Would you like to generate the certificates now?", "y")):
                generate_certificates(client, cert_dir)
                print("Certificates generated to {}".format(cert_dir))
                print("Be sure to add {} to your trusted CAs in your browser!".format(os.path.join(cert_dir, "server.pem")))
                load_certificates(client, cert_dir)
            else:
                print("Can not run proxy without SSL certificates")
                exit(1)
        try:
            # Only try and listen/set default storage if we're not attaching
            if args.attach is None:
                storage = client.add_in_memory_storage("")
                client.disk_storage = storage
                client.inmem_storage = client.add_in_memory_storage("m")
                client.set_proxy_storage(storage.storage_id)

            app = QApplication(sys.argv)
            window = GuppyWindow(client)
            window.setAttribute(Qt.WA_DeleteOnClose)
            try:
                app.exec_()
            finally:
                window.close()
        except MessageError as e:
            print(str(e))
    ProxyThread.waitall()


def start():
    main()


if __name__ == '__main__':
    main()
