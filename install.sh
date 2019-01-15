#!/bin/bash

prompt_yn() {
    read -p "$1 (yN) " yn;
    case $yn in
        [Yy]* ) return 0;;
        * ) return 1;;
    esac
}

require() {
    if ! $@; then
        echo "Error running $@, exiting...";
        exit 1;
    fi
}

GO="$(which go)"
BUILDFLAGS=""
PUPPYREPO="https://github.com/roglew/puppy.git"
PUPPYVERSION="tags/0.2.6"

INSTALLDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMPGOPATH="$INSTALLDIR/gopath"
DATADIR="$HOME/.guppy"
VIRTUALENVNAME="guppyenv"

while getopts "g:f:r:dph" opt; do
    case $opt in
        g)
            GO="$OPTARG"
            ;;
        f)
            BUILDFLAGS="${OPTARG}"
            ;;
        r)
            PUPPYREPO="${OPTARG}"
            DEV="yes"
            ;;
        d)
            DEV="yes"
            ;;
        p)
            DOPUPPY="yes"
            ;;
        h)
            echo -e "Build script flags:"
            echo -e "-p\tCompile puppy from source rather than using pre-built binaries"
            echo -e "-g [path to go]\tUse specific go binary to compile puppy"
            echo -e "-f [arguments]\tArguments to pass to \"go build\". ie -f \"-ldflags -s\""
            echo -e "-r [git repository link]\t download puppy from an alternate repository"
            echo -e "-d\tinstall puppy in development mode by using \"pip install -e\" to install puppy"
            echo -e "-h\tprint this help message"
            echo -e ""
            exit 0;
            ;;

        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1;
            ;;
    esac
done

if ! type "python3" > /dev/null; then
    echo "python3 not installed. Please install python3 and try again"
    exit 1;
fi

if ! type "pip" > /dev/null; then
    if ! type "easy_install" > /dev/null; then
        echo "pip not available. Please install pip then try again."
        exit 1;
    fi

    if prompt_yn "Installation requires pip. Install pip using \"sudo easy_install pup\"?"; then
        require sudo easy_install pip;
    else
        echo "Please install pip and try the installation again"
        exit 1;
    fi
fi

cd "$INSTALLDIR"
mkdir -p $DATADIR

if [ $DOPUPPY ]; then
    # Compile puppy from source

    if [ ! $GO ]; then
        if ! type "go" > /dev/null; then
            echo "go not installed. Please install go and try again"
            exit 1;
        fi
    fi

    # Set up fake gopath
    export GOPATH="$TMPGOPATH";
    require mkdir -p "$GOPATH/src"

    # Clone the repo
    REPODIR="$GOPATH/src/puppy";
    if [ ! -d "$REPODIR" ]; then
        # Clone the repo if it doesn't exist
        require mkdir -p "$REPODIR";
        echo git clone "$PUPPYREPO" "$REPODIR";
        require git clone "$PUPPYREPO" "$REPODIR";
    fi
    
    # Check out the correct version
    cd "$REPODIR";
    if [ $DEV ] || [ $REPODIR ]; then
        # If it's development, get the most recent version of puppy
        require git pull;
    else
        # if it's not development, get the specified version
        require git checkout "$PUPPYVERSION";
    fi
    cd "$INSTALLDIR"
    
    # Get dependencies
    cd "$REPODIR";
    echo "Getting puppy dependencies..."
    require "$GO" get ./...;
    
    # Build puppy into the data dir
    echo "Building puppy into $DATADIR/puppy...";
    require mkdir -p "$DATADIR";
    require "$GO" build -o "$DATADIR"/puppy $BUILDFLAGS "puppy/cmd/main";
else
    # copy the pre-compiled binary
    UNAME="$(uname -s)"
    PUPPYFILE=""
    if [ "$UNAME" = "Darwin" ]; then
        echo "copying mac version of pre-built puppy to $DATADIR/puppy"
        PUPPYFILE="puppy.osx"
    elif [ "$UNAME" = "Linux" ]; then
        if [ "$(uname -m)" = "x86_64" ]; then
            echo "copying 64-bit linux version of pre-built puppy to $DATADIR/puppy"
            PUPPYFILE="puppy.linux64"
        else
            echo "copying 32-bit linux version of pre-built puppy to $DATADIR/puppy"
            PUPPYFILE="puppy.linux32"
        fi
    else
        echo "could not detect system type. Please use -p to compile puppy from source (requires go installation)"
        exit 1;
    fi
    cp "$INSTALLDIR/puppyrsc/$PUPPYFILE" "$DATADIR/puppy"
fi

# Clear out old .pyc files
require find "$INSTALLDIR/guppyproxy" -iname "*.pyc" -exec rm -f {} \;

# Set up the virtual environment
if ! type "virtualenv" > /dev/null; then
    if prompt_yn "\"virtualenv\" not installed. Install using pip?"; then
        require sudo pip install virtualenv
    else
        exit 1;
    fi
fi

VENVDIR="$DATADIR/venv";
require mkdir -p "$VENVDIR";
require virtualenv -p "$(which python3)" "$VENVDIR";
cd "$VENVDIR";
require source bin/activate;
cd "$INSTALLDIR";

if [ -z $DEV ]; then
    require pip install -e .
else
    require pip install .
fi

echo -e "#!/bin/bash\nsource \"$VENVDIR/bin/activate\";\nguppy \$@ || killall puppy;\n" > start
chmod +x start;

echo ""
echo "Guppy installed. Run guppy by executing the generated \"start\" script."
