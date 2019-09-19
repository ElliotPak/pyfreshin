#!/usr/bin/env python3

import argparse
import sys
import re
import platform
import json

def get_args():
    argsetup = argparse.ArgumentParser()
    argsetup.add_argument("-d", "--distro", help="Specify a different distro", action="store")
    argsetup.add_argument("-p", "--preview", help="Output commands instead of running them", action="store_true")
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
    repositories = {}
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
            'shell-installs': shell_installs,
            'repositories': repositories}

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

def install_command(ii, distro):
    if distro == "ubuntu":
        return "sudo apt-get -y -f install " + ii
    elif distro == "arch":
        return "sudo pacman -S " + ii

def setup_git_commands(ii, git_info):
    commands = []
    clone_dir = "/tmp/pyfreshin/" + ii # + unix timestamp
    if "install-dir" in git_info:
        clone_dir = git_info["install-dir"]
    commands.append("git clone " + git_info["repo"] + " " + clone_dir)
    commands.append("cd " + clone_dir)
    commands = commands + git_info["commands"]
    return commands

def setup_shell_commands(ii, shell_info):
    return shell_info["commands"]

def add_repo_command(repo, distro):
    if distro == "ubuntu":
        return "sudo add-apt-repository -u -y " + repo
    else:
        return ""

def convert_to_commands(args, info, distro, cat_to_install = None):
    commands = []
    installed = []
    categories = info["categories"]
    dependencies = info["dependencies"]
    git_installs = info["git-installs"]
    shell_installs = info["shell-installs"]
    install_as = info["install-as"]
    repositories = info["repositories"]

    def add_install(ii):
        commands = []

        if ii in repositories and distro in repositories[ii]:
            repo = repositories[ii][distro]
            commands.append(add_repo_command(repo, distro))

        if ii in install_as and distro in install_as[ii]:
            to_install_as = install_as[ii][distro]
            commands.append(install_command(to_install_as, distro))
        elif ii in install_as and "all" in install_as[ii]:
            to_install_as = install_as[ii]["all"]
            commands.append(install_command(to_install_as, distro))
        elif ii in git_installs and distro in git_installs[ii]:
            commands += setup_git_commands(ii, git_installs[ii][distro])
        elif ii in git_installs and "all" in git_installs[ii]:
            commands += setup_git_commands(ii, git_installs[ii]["all"])
        elif ii in shell_installs and distro in shell_installs[ii]:
            commands += setup_shell_commands(ii, shell_installs[ii][distro])
        elif ii in shell_installs and "all" in shell_installs[ii]:
            commands += setup_shell_commands(ii, shell_installs[ii]["all"])
        else:
            commands += [(install_command(ii, distro))]
        return commands

    if git_installs:
        installed.append("git")
        commands = commands + add_install("git")

    for cat in categories:
        if not cat_to_install or cat in cat_to_install:
            for ii in categories[cat]:
                if ii in dependencies and "all" in dependencies[ii]:
                    for jj in dependencies[ii]["all"]:
                        if not jj in installed:
                            commands = commands + add_install(jj)
                            installed.append(jj)
                elif ii in dependencies and distro in dependencies[ii]:
                    for jj in dependencies[ii][distro]:
                        if not jj in installed:
                            commands = commands + add_install(jj)
                            installed.append(jj)
                if not ii in installed:
                    commands = commands + add_install(ii)
                    installed.append(ii)

    return commands

def print_nice(ii):
    print(json.dumps(ii, sort_keys=True, indent=4, separators=(',', ': ')))

def determine_distro():
    # stubbed for now!
    return "ubuntu"

def main():
    args = get_args()
    distro = determine_distro()
    if args.distro:
        distro = args.distro
    info = parse_install_file(file_contents(args.file))
    commands = convert_to_commands(args, info, distro)
    if args.preview:
        for ii in commands:
            print(ii)

if __name__ == "__main__":
    main()
