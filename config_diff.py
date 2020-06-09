"""
Config_diff is a configuration diff tool which helps to collect output of specified
commands during two stages `pre-change`,`post-change` and produces HTML diff files
highlighting the differences in command output.
Required access to network devices and uses Netmiko to connect to device and 
execute command.

Supported platforms:
Tested platforms:
"""

import argparse
import os
import yaml
import re
import difflib
import sys
import getpass

from colorama import Fore, init
from netmiko import ConnectHandler
from netmiko.ssh_exception import (
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
    SSHException,
)

# Auto-reset colorama colours back after each print statement
init(autoreset=True)

# defines a custom args parser
class CustomParser(argparse.ArgumentParser):
    """
    Overrides default CLI parser's print_help and error methods
    """
    # Print our help message
    def print_help(self):
        print(
            "\n Usage examples: To capture command output"
            + "\n               change_diff.py --capture pre-change --device-list <device_file>.yaml"
            + "\n               change_diff.py -c post-change -dl <device_file.yaml\n"
            + "\n Usage example: To compute difference"
            + "\n                change_diff.py -dl <device_file>.yaml -d\n"
            + "\n Device information should be in the following format and stored with a .yaml extention:"
            + "\n                - hostname: Router1"
            + "\n                  ip: 192.168.1.191"
            + "\n                  os: cisco_ios"
            + "\n                  command_list:"
            + "\n                    - show ip interface brief"
            + "\n                    - sh ip bgp summary"
        )

    def error(self, message):
        print("error: {}\n".format(message))
        print(" Use --help or -h for help")
        sys.exit(2)


# defines the arguments that need to be passed when executing the script
def parse_args():
    """Parse arguments."""
    parser = CustomParser()
    # Defines mutually exclusive args -c and -d
    # The execution is either - c (capturing data) or -d (finding the differences)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-c",
        "--capture",
        help="Capture window {pre-change or post-change}",
        choices=["pre-change", "post-change"],
    )

    group.add_argument(
        "-d",
        "--diff",
        help="Compute Difference between pre-change and post-change",
        action="store_true",
    )

    # defines the args to pass list of devices from a file
    parser.add_argument(
        "-dl", "--device-list", help="File name of device list file", required=True
    )
    return parser.parse_args()


# Function to execute command on device and wite to file.
def execute_command_write_to_file(capture_window, device_list, uname, pword):
    """
    Executes IOS commands using Netmiko.
    Writes raw output to a report file.

    :param capture_window: pre-change or post-change capture
    :param device_list: contains device IP addresses, type and commands to execute
    :param uname: Username used to authenticate to device
    :param pword: Password used to authenticate to device
    """
    # loops through list of devices
    error = "False"
    for device in device_list:
        # defines a hostname paramater used later while computing the file name
        hostname = device["hostname"]
        print(Fore.CYAN + "***** Processing Host: {} *****".format(hostname))
        # Defines Netmiko connection parameters
        a_device = {
            "device_type": device["os"],
            "host": device["ip"],
            "username": uname,
            "password": pword,
        }
        # Try to connect to device and raise exception if unsuccessful
        # and exit program
        try:
            remote_conn = ConnectHandler(**a_device)
        # Raise exception if Username or Password is wrong
        except NetMikoAuthenticationException as error:
            print(
                Fore.RED
                + "===> Authentication Exception host `{}` \n".format(a_device["host"]),
                str(error),
            )
            error = "True"
        # Raise exception if connection times out
        except NetMikoTimeoutException as error:
            print(
                Fore.RED
                + " ===> WARNING : Timeout while connecting"
                + "to: {}, error: {} Skipping.".format(a_device["host"], str(error))
            )
            error = "True"
        # Raise SSH exception
        except SSHException as error:
            print(
                Fore.RED
                + " ===> WARNING : SSH2 protocol negotiation or logic errors while"
                + "connecting to: {}, error: {}  Skipping.".format(
                    a_device["host"], str(error)
                )
            )
            error = "True"
        # Raise ValueError(' ===> Skipping - Failed to execute due to %s', error)
        except Exception as error:
            print(
                Fore.RED
                + " ===> WARNING : Unhandled exception while connecting"
                + "to: {}, error: {}  Skipping.".format(a_device["host"], str(error))
            )
            error = "True"

        # if SSH to device was successful
        else:
            # loop through the list of commands
            for command in device["command_list"]:
                print("Command: `{}`".format(command))
                # defines the file name - a combination of host name and command
                filename = hostname + "_" + re.sub("\s", "_", command)
                # print (filename)
                # set path of the file that will be created.
                # dependes on the capture_window paramater
                file = os.path.join(capture_window, filename + ".txt")
                # print (file)
                # Execute the command on device and write output to file
                try:
                    output = remote_conn.send_command(command)
                    # Error executing command for cisco ios
                    if "Incomplete command" in output:
                        print(
                            Fore.RED
                            + " ===> Error is executing command `{}` on host `{}`".format(
                                command, a_device["host"]
                            )
                            + "\n"
                        )
                        error = "True"
                    else:
                        with open(file, "w") as f:
                            f.write(output)
                # If command execution is un-successful raise an exception on screen
                except:
                    print(
                        Fore.RED
                        + " ===> Error is executing command `{}` on host `{}`".format(
                            command, a_device["host"]
                        )
                        + "\n"
                    )
    # print (error)
    return error


def compute_diff(device_list):
    """
    Compare text string in 'pre-change' with 'post-change' and produce
    formatted HTML table to be written to a file.

    :param device_list: contains device IP addresses, type and commands
    """
    error = "False"
    # loops through list of devices
    for device in device_list:
        # defines a hostname paramater used later while computing the file name
        hostname = device["hostname"]
        print(Fore.CYAN + "***** Computing Diff for: {} *****".format(hostname))
        # loops through list of commands
        for command in device["command_list"]:
            print("Command: `{}`".format(command))
            filename = hostname + "_" + re.sub("\s", "_", command)
            # defines pre-change and post-change file name for each command to compute difference
            pre_change_file = "pre-change/" + filename + ".txt"
            post_change_file = "post-change/" + filename + ".txt"
            # ensure pre-change capture exists for host and command combination
            try:
                with open(pre_change_file, "r") as pre_change:
                    pre_change = pre_change.readlines()
            # raise exception if not
            except:
                print(
                    Fore.YELLOW
                    + "pre-change capture does not exist for command `{}` on host `{}`".format(
                        command, hostname
                    )
                )
                error = "True"
                break
            # ensure post-change capture exists for host and command combination
            try:
                with open(post_change_file, "r") as post_change:
                    post_change = post_change.readlines()
            # riase exception if not
            except:
                print(
                    Fore.YELLOW
                    + "post-change capture does not exist for command `{}` on host `{}`".format(
                        command, hostname
                    )
                )
                error = "True"
                break
            file = os.path.join("diff", filename + ".html")
            difffile = difflib.HtmlDiff().make_file(pre_change, post_change,"pre-change","post-change",context="-c", numlines=500)
            with open(file, 'w') as f:
                f.writelines(difffile)
    return error


def main():

    option = parse_args()
    # print (option.change)
    # print (option.device_list)
    # print (option.diff)
    capture_window = option.capture

    # reads the device list yaml file into device_list
    with open(option.device_list, "r") as device_list:
        device_list = yaml.safe_load(device_list)
    # print(device_list)

    # Checks if execution is to capture output
    if capture_window != None:

        # creates a folder for capture window if it does not exist
        # If it does, warns user and exits script
        try:
            os.makedirs(capture_window)
        except OSError as e:
            print(
                Fore.RED
                + "*" * 50
                + "\n"
                + "A {} capture already exists \n".format(option.capture)
                + "Delete the `{}` folder to re-capture \n".format(option.capture)
                + "*" * 50
                + "\n"
            )
            sys.exit(2)

        print(
            Fore.GREEN
            + "*" * 50
            + "\n Executing in Capture mode"
            + "\n Capture Window set to : {} \n".format(capture_window)
            + "*" * 50
            + "\n"
        )

        # get username and password input from user
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        print ("\n")
        # Execute command and write to file
        error = execute_command_write_to_file(capture_window, device_list, username, password)

    # check if execution is to get difference
    if option.diff:
        # creates a folder to capture difference if it does not exist
        # If it does, warns user and exits script
        try:
            os.makedirs("diff")
        except OSError as e:
            print(
                Fore.RED
                + "\n"
                + "*" * 50
                + "\n A configuration Diff already exists"
                + "\n Delete the `Diff` folder to re-capture\n"
                + "*" * 50
            )
            sys.exit(2)

        print(
            Fore.GREEN
            + "\n"
            + "*" * 50
            + "\n Executing in Diff mode\n"
            + "*" * 50
        )

        # compares differences between command output and generates HTML files 
        # highlighting the diferences
        error = compute_diff(device_list)

    # displays status of execution on screen
    if error == "True":
        print(
            Fore.YELLOW
            + "\n"
            + "*" * 50
            + "\n Execution completed with errors \n"
            + "*" * 50
        )
    elif error == "False":
        print(
            Fore.GREEN
            + "\n"
            + "*" * 50
            + "\n Execution completed with no errors \n"
            + "*" * 50
        )


if __name__ == "__main__":
    main()
