#!/usr/bin.env python2

import argparse
import sys
import re
import platform

def get_args():
    argsetup = argparse.ArgumentParser()
    argsetup.add_argument("-d", "--distro", help="Specify a different distro", action="store")
    argsetup.add_argument("-s", "--silent", help="Output commands instead of running them", action="store_true")
    argsetup.add_argument("file", help="File to read dependencies from", action="store")
    args = argsetup.parse_args()
    if len(sys.argv) <= 1:
        argsetup.print_help()
    return args

def file_contents(filename):
    with open(filename, "r") as file:
        return file.read()
    return None

def parse_install_file(contents):
    categories = {}
    dependencies = {}
    install_as = {}
    git_installs = {}
    shell_installs = {}
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

            # install-as PACKAGE_NAME INSTALL_AS_NAME
            elif segments[0] == "install-as" and len(segments) > 3:
                if not segments[2] in install_as:
                    install_as[segments[2]] = {}
                install_as[segments[2]][segments[1]] = segments[3]

            # install-shell PLATFORM PACKAGE_NAME [RUN_DIRECTORY]
            #     commands...
            elif segments[0] == "install-shell" and len(segments) > 2:
                inst = {'commands': get_indented_commands(lines, index)}
                if len(segments) > 3:
                    inst['run-dir'] = segments[3]
                if not segments[2] in shell_installs:
                    shell_installs[segments[2]] = {}
                shell_installs[segments[2]][segments[1]] = inst

            # install-shell PLATFORM PACKAGE_NAME URL [INSTALL_DIRECTORY]
            #     post-install-commands...
            elif segments[0] == "install-git" and len(segments) > 3:
                inst = {'commands': get_indented_commands(lines, index),
                        'repo': segments[3]}
                if len(segments) > 4:
                    inst['install-dir'] = segments[4]
                if not segments[2] in git_installs:
                    git_installs[segments[2]] = {}
                git_installs[segments[2]][segments[1]] = inst
    return {'categories': categories,
            'dependencies': dependencies,
            'install-as': install_as,
            'git-installs': git_installs,
            'shell-installs': shell_installs}

def get_indented_packages(line):
    return line.strip().split()

def get_indented_commands(lines, index):
    trimmed_lines = lines[index + 1:]
    commands = []
    for ii in trimmed_lines:
        if re.match(r'\s', ii) and ii.strip():
            commands.append(ii.strip())
        else:
            return commands
    return commands

def determine_distro():
    return "ubuntu"

def main():
    args = get_args()
    distro = determine_distro()
    if args.distro:
        distro = args.distro
    info = parse_install_file(file_contents(args.file))
    print(info)
    # commands = convert_to_commands(info)

if __name__ == "__main__":
    main()
