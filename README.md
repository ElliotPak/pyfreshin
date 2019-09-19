# pyfreshin

*pyfreshin* is a python script that auto-installs a bunch of packages based on
the provided file. It works with Python versions 2.7.15+, and Python 3 and
above. It can manage dependencies between packages, install via git or shell
scripts, and doesn't reinstall already installed packages by default. It can
(in theory) support multiple distributions of Linux as well (although currently
only installation commands for Ubuntu and Arch Linux have been specified, so
feel free to submit a pull request to add more).

## Usage

Usage: `python pyfreshin.py [-h] [-d DISTRO] [-p] [-f] file`  
With the following arguments:

- `-h`: Display help
- `-d DISTRO`: Specify the Linux distribution manually
- `-s`: Output commands instead of running them
- `-f`: Reinstall programs that are already installed

## Specifying the installation file

An installation file might look like the following:

```
category basic
    git vim zsh tmux python3

category other
    compton stack hindent

install-as arch python3 python

dependencies ubuntu compton
    libxcomposite-dev libxrender-dev libxrandr-dev libxinerama-dev libconfig-dev libdbus-1-dev
install-git ubuntu compton https://github.com/tryone144/compton
    make
    sudo make install MANPAGES= install

dependencies all stack
    curl
install-shell all stack
    curl -sSL https://get.haskellstack.org/ | sh

dependencies all haskell-tools
    stack
install-shell all haskell-tools
    stack install hindent
installs-executables all haskell-tools
    hindent
```

Note that in general:

- If a package is supplied somewhere (e.g. in a category or as a dependency),
  it will be installed through your distribution's package manager, unless
  specified otherwise.
- You can specify `all` in place of a distribution name to run it on all
  distributions.

Installation files can contain the following commands:

### `category`

```
category CATEGORY-NAME
    package1 package2 package3...
```

Specifies a category and the programs that it contains.

### `dependencies`

```
dependencies DISTRO PACKAGE_NAME
    package1 package2 package3...
```

Specifies a list of packages that are dependent on another package.

### `install-as`

```
install-as DISTRO PACKAGE_NAME INSTALL_AS_NAME
```

When installing `PACKAGE_NAME`, the package manager will install
`INSTALL_AS_NAME`.

### `repository`

```
repository PLATFORM PACKAGE-NAME REPO-INFO
```

Specifies a repository to add to your distribution's package manager before
installing.

### `install-shell`

```
install-shell PLATFORM PACKAGE_NAME [RUN_DIRECTORY]
    commands...
```

Installs the package on this distro by running shell commands instead of using
the package manager. You can optionally specify a directory to run these
commands in: by default they will run in the current working directory.

### `install-git`

```
install-git PLATFORM PACKAGE_NAME URL [INSTALL_DIRECTORY]
    commands...
```

Installs the package on this distro by cloning a git repository and running
shell commands in the cloned folder instead of using the package manager. You
can optionally specify a directory to clone to: by default it will clone to
`/tmp/pyfreshin/PACKAGE-NAME/`.

### `installs-executables`

```
installs-executables PLATFORM PACKAGE_NAME
    exe1 exe2 exe3...
```

This package is considered install on this distro if the specified executables
are installed on the machine, regardless of any other checks.
