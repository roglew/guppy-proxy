# Guppy Proxy

gui version of pappy because all of you are too weak for the CLI

# Installation

Dependencies (make sure these commands are available):

* `python3`
* `pip`
* `virtualenv` (can be installed with pip)

Steps:

1. Clone this repo somewhere it won't get deleted: `git clone https://github.com/roglew/guppy-proxy.git`
1. `cd /path/to/guppy-proxy`
1. `./install.sh`
1. Test that it starts up and generate certs: `./start --lite` (keep it open and continue to test it works)
1. Copy/symlink the `start` script somewhere in your PATH (i.e. `~/bin` if you have that included)
1. Add the CA cert in `~/.guppy/certs` to your browser
1. Configure your browser to use `localhost:8080` as a proxy
1. Navigate to a site and look at the history in the main window

# Tutorial

Ask me directly for help since this is still a rough project
