#!/usr/bin/env python3

import argparse
import sys
import re
import platform
import json
import subprocess
import os
import os.path
from collections import OrderedDict

def get_args():
    argsetup = argparse.ArgumentParser()
    argsetup.add_argument("-d", "--distro", help="Specify a different distro", action="store")
    argsetup.add_argument("-s", "--show", help="Output commands instead of running them", action="store_true")
    argsetup.add_argument("-f", "--force", help="Install programs that are already installed", action="store_true")
    argsetup.add_argument("file", help="File to read dependencies from", action="store")
    args = argsetup.parse_args()
    if len(sys.argv) <= 1:
        argsetup.print_help()
    return args

def file_contents(filename):
    '''
    Return the contents of the file (if the file exists/can be read) and None
    otherwise.
    '''
    with open(filename, "r") as file:
        return file.read()
    return None

def parse_install_file(contents):
    '''
    Parse a string into a dictionary representation.
    '''
    categories = OrderedDict()
    dependencies = {}
    install_as = {}
    git_installs = {}
    shell_installs = {}
    repositories = {}
    installed_exes = {}
    lines = contents.splitlines()
    for index, line in enumerate(lines):
        segments = line.split()
        if len(segments) > 0 and not re.match(r'\s', line[0]):

            # category CATEGORY_NAME
            #     package1 package2 package3...
            if segments[0] == "category" and len(segments) > 1:
                cat = segments[1]
                categories[cat] = get_indented_packages(lines[index + 1])

            # dependencies PLATFORM PACKAGE_NAME
            #     package1 package2 package3...
            elif segments[0] == "dependencies" and len(segments) > 2:
                deps = get_indented_packages(lines[index + 1])
                if not segments[2] in dependencies:
                    dependencies[segments[2]] = {}
                dependencies[segments[2]][segments[1]] = deps

            # install-as PLATFORM PACKAGE_NAME INSTALL_AS_NAME
            elif segments[0] == "install-as" and len(segments) > 3:
                if not segments[2] in install_as:
                    install_as[segments[2]] = {}
                install_as[segments[2]][segments[1]] = segments[3]

            # repository PLATFORM PACKAGE-NAME REPO-INFO
            elif segments[0] == "repository" and len(segments) > 3:
                if not segments[2] in install_as:
                    repositories[segments[2]] = {}
                repositories[segments[2]][segments[1]] = segments[3]

            # install-shell PLATFORM PACKAGE_NAME [RUN_DIRECTORY]
            #     commands...
            elif segments[0] == "install-shell" and len(segments) > 2:
                inst = {'commands': get_indented_commands(lines, index)}
                if len(segments) > 3:
                    inst['run-dir'] = segments[3]
                if not segments[2] in shell_installs:
                    shell_installs[segments[2]] = {}
                shell_installs[segments[2]][segments[1]] = inst

            # install-git PLATFORM PACKAGE_NAME URL [INSTALL_DIRECTORY]
            #     post-install-commands...
            elif segments[0] == "install-git" and len(segments) > 3:
                inst = {'commands': get_indented_commands(lines, index),
                        'repo': segments[3]}
                if len(segments) > 4:
                    inst['install-dir'] = segments[4]
                if not segments[2] in git_installs:
                    git_installs[segments[2]] = {}
                git_installs[segments[2]][segments[1]] = inst

            # installs-executables PLATFORM PACKAGE_NAME
            #     package1 package2 package3...
            elif segments[0] == "installs-executables" and len(segments) > 2:
                exes = get_indented_packages(lines[index + 1])
                if not segments[2] in installed_exes:
                    installed_exes[segments[2]] = {}
                installed_exes[segments[2]][segments[1]] = exes

    return {'categories': categories,
            'dependencies': dependencies,
            'install-as': install_as,
            'git-installs': git_installs,
            'shell-installs': shell_installs,
            'repositories': repositories,
            'installed-exes': installed_exes}

def get_installed_packages(distro):
    '''
    Determine packages installed on this computer. Also includes executeables inside $PATH.
    '''
    installed = set()
    paths = os.environ["PATH"].split(os.pathsep)
    for path in paths:
        if os.path.isdir(path):
            for exe in os.listdir(path):
                if os.access(os.path.join(path, exe), os.X_OK):
                    installed.add(exe)
    if distro == "ubuntu":
        output = subprocess.check_output(["dpkg", "--get-selections"]).decode("utf-8")
        for ii in output.split('\n'):
            match = re.match(r'([A-Za-z0-9\-]+)(:\S+)?\s*install', ii)
            if match:
                installed.add(match.group(1))
    return installed

def get_indented_packages(line):
    '''
    Returns all whitespace-separated words in a line.
    '''
    return line.strip().split()

def get_indented_commands(lines, index):
    '''
    Get all lines that are indented after the specified index, terminating once
    a line no longer fits this criteria.
    '''
    trimmed_lines = lines[index + 1:]
    commands = []
    for ii in trimmed_lines:
        if re.match(r'\s', ii) and ii.strip():
            commands.append(ii.strip())
        else:
            return commands
    return commands

def install_command(ii, distro):
    '''
    Get the command to install a program in the specified distro.
    '''
    if distro == "ubuntu":
        return "sudo apt-get -y -f install " + ii
    elif distro == "arch":
        return "sudo pacman -S " + ii

def setup_git_commands(ii, git_info):
    '''
    Given a package and git info, creates the commands to install it.
    '''
    commands = []
    clone_dir = "/tmp/pyfreshin/" + ii # + unix timestamp
    if "install-dir" in git_info:
        clone_dir = git_info["install-dir"]
    commands.append("git clone " + git_info["repo"] + " " + clone_dir)
    commands.append("cd " + clone_dir)
    commands = commands + git_info["commands"]
    return commands

def setup_shell_commands(ii, shell_info):
    '''
    Given a package and shell info, creates the commands to install it.
    '''
    return shell_info["commands"]

def repo_command(repo, distro):
    '''
    Get the command to add a package manager's repository in the specified
    distro.
    '''
    if distro == "ubuntu":
        return "sudo add-apt-repository -u -y " + repo
    else:
        return ""

def distro_or_all(distro, ii, dictionary):
    '''
    Return the distro-specific or general entry from the dictionary, given a
    package.
    '''
    if ii in dictionary and distro in dictionary[ii]:
        return dictionary[ii][distro]
    elif ii in dictionary and "all" in dictionary[ii]:
        return dictionary[ii]["all"]
    else:
        return []

def convert_to_commands(args, info, distro, preinstalled):
    commands = OrderedDict()
    installed = set()
    categories = info["categories"]
    dependencies = info["dependencies"]
    git_installs = info["git-installs"]
    shell_installs = info["shell-installs"]
    install_as = info["install-as"]
    repositories = info["repositories"]
    installed_exes = info["installed-exes"]

    def install_commands(ii):
        '''
        Generate the commands required to install a package.
        '''
        commands = []

        if ii in repositories and distro in repositories[ii]:
            repo = repositories[ii][distro]
            commands.append(repo_command(repo, distro))

        install_as_commands = distro_or_all(distro, ii, install_as)
        shell_install_commands = distro_or_all(distro, ii, shell_installs)
        git_install_commands = distro_or_all(distro, ii, git_installs)
        if install_as_commands:
            commands.append(install_as_commands)
        elif git_install_commands:
            commands += setup_git_commands(ii, git_install_commands)
        elif git_install_commands:
            commands += setup_shell_commands(ii, shell_install_commands)
        else:
            commands.append(install_command(ii, distro))
        installed.add(ii)
        return commands

    def not_installed(ii):
        '''
        Returns true if a package is not installed.
        '''
        if not ii in installed_exes:
            return not ii in preinstalled
        elif distro in installed_exes[ii]:
            return not all([jj in preinstalled for jj in installed_exes[ii][distro]])
        elif "all" in installed_exes[ii]:
            return not all([jj in preinstalled for jj in installed_exes[ii]["all"]])

    def ensure_installed(ii):
        '''
        Get the commands to install all of a package's dependencies and then
        the package itself.
        '''
        commands = []
        if not_installed(ii):
            if ii in dependencies and distro in dependencies[ii]:
                for jj in dependencies[ii][distro]:
                    if not jj in installed:
                        commands += ensure_installed(jj)
            elif ii in dependencies and "all" in dependencies[ii]:
                for jj in dependencies[ii]["all"]:
                    if not jj in installed:
                        commands += ensure_installed(jj)
            commands += install_commands(ii)
        return commands

    if git_installs:
        ensure_installed("git")

    for cat in categories:
        for ii in categories[cat]:
            inst_commands = ensure_installed(ii)
            if inst_commands:
                commands[ii] = inst_commands

    return commands

def filter_commands(commands, categories, cat_to_install = None, package_to_install = None):
    '''
    Filter out commands that either not meant to be installed or that belong to
    categories that are not meant to be installed.
    '''
    filtered = OrderedDict()
    for cat in categories:
        if (not cat_to_install or cat in cat_to_install):
            for ii in categories[cat]:
                if (not package_to_install or ii in package_to_install) and ii in commands:
                    filtered[ii] = commands[ii]
    return filtered

def print_commands(commands):
    '''
    Print commands in a pretty way.
    '''
    for cc in commands:
        if len(commands[cc]) == 0:
            print(cc + " (no commands)")
        elif len(commands[cc]) == 1:
            print(cc + ": " + commands[cc][0])
        else:
            print(cc + ":")
            for dd in commands[cc]:
                print("    " + dd)

def determine_distro():
    '''
    Determine the distro of your machine. Stubbed for now! Specify it in the
    command line arguments.
    '''
    return "ubuntu"

def main():
    '''
    The main function.
    '''
    args = get_args()
    distro = determine_distro()
    if args.distro:
        distro = args.distro
    if args.force:
        installed = set()
    else:
        installed = get_installed_packages(distro)
    info = parse_install_file(file_contents(args.file))
    commands = convert_to_commands(args, info, distro, installed)
    commands_filtered = filter_commands(commands, info["categories"])
    if args.show:
        print_commands(commands_filtered)

if __name__ == "__main__":
    main()
