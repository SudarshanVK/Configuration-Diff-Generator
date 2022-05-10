import click
import os
import yaml
import re
import difflib
import sys
import getpass
import json

from colorama import Fore, init
from netmiko import ConnectHandler
from netmiko.ssh_exception import (
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
    SSHException,
)

# reset Colorama Colors after each print statement
init(autoreset=True)

# Click command group to run in Capture Mode
@click.group()
def execute_capture():
    pass


# Click command group to run in Diff Mode
@click.group()
def execute_diff():
    pass


# Specify the two options that are needed to run the Capture Mode
# option w: Defines the capture window
# option dl: inventory file that contails the list of hosts and commands
@execute_capture.command()
@click.option("-w", type=str, help="Enter Capture Window.", required=True)
@click.option("-i", type=str, help="Enter inventory file.", required=True)
def capture(w, i):
    """
    Use this mode to capture command output and save to files.
    """
    print(Fore.CYAN + "\n=====> EXECUTING IN CAPTURE MODE <=====")
    with open(i, "r") as device_list:
        device_list = yaml.safe_load(device_list)
        # print(device_list)
    try:
        os.makedirs(w)
    except OSError as e:
        print(
            Fore.RED
            + f"  ===>A '{w}' capture already exists. "
            + f"Delete '{w}' folder to re-capture\n"
        )
        sys.exit(2)

    print(Fore.GREEN + f" ====>Capture Window Set to: {w}")

    # print(Fore.YELLOW + "   ==> Enter device Credentials:")
    # username = input(Fore.YELLOW + "    => Username: ")
    # password = getpass.getpass(Fore.YELLOW + "    => Password: ")
    execute_command_write_to_file(w, device_list)


# Specify the two options that are needed to run in Diff mode
# option w1: Capture Window 1
# option w2: Capture Window 2
@execute_diff.command()
@click.option("-w1", type=str, help="Enter Capture Window(pre-change)", required=True)
@click.option(
    "-w2",
    type=str,
    help="Enter Capture Window to diff against(post-change)",
    required=True,
)
def diff(w1, w2):
    """
    Use this mode to compute diff in command output between two captures.
    """
    print(Fore.CYAN + "\n=====> EXECUTING IN DIFF MODE <=====")
    # Check if Capture Window 1 exists, if it does not exit program
    if os.path.isdir(w1) == False:
        print(f"{Fore.RED}  ===>A '{w1}' capture does not exist.\n")
        sys.exit(2)
    # Check if Capture Window 2 exists, if it does not exit program
    if os.path.isdir(w2) == False:
        print(f"{Fore.RED}  ===>A '{w2}' capture does not exist.\n")
        sys.exit(2)
    # Check if a diff already exists between the two Capture Windows.
    # If it does exit the program
    try:
        diff_dir = f"{w1}_{w2}_diff"
        os.makedirs(diff_dir)
    except OSError as e:
        print(
            Fore.RED
            + f" ===> A diff between '{w1}' and '{w2}' already exists. "
            + f"Delete folder '{diff_dir}' and try again"
        )
        sys.exit(2)
    # Call function that will compute the Diff
    compute_diff(w1, w2, diff_dir)


# Function to execute command on device and wite to file.
def execute_command_write_to_file(capture_window, device_list):
    # sourcery skip: do-not-use-bare-except, use-fstring-for-concatenation
    """
    Executes IOS commands using Netmiko.
    Writes raw output to a report file.

    :param capture_window: pre-change or post-change capture
    :param device_list: contains device IP addresses, type and commands
    :param uname: Username used to authenticate to device
    :param pword: Password used to authenticate to device
    """
    # loops through list of devices
    for device in device_list:
        # defines a hostname paramater used later while computing the file name
        hostname = device["hostname"]
        print(f"{Fore.GREEN}  ===> Processing Host: {hostname} ")
        # Defines Netmiko connection parameters
        a_device = {
            "device_type": device["device_type"],
            "host": device["ip"],
            "username": device["username"],
            "password": device["password"],
            'global_delay_factor': 2
        }
        # Try to connect to device and raise exception if unsuccessful
        # and exit program
        try:
            remote_conn = ConnectHandler(**a_device)
        # Raise exception if Username or Password is wrong
        except NetMikoAuthenticationException as error:
            print(
                Fore.RED
                + "   ==> Authentication Exception on host `"
                + f"{a_device['host']}"
            )
        # Raise exception if connection times out
        except NetMikoTimeoutException as error:
            print(
                Fore.RED
                + "  ===> WARNING : Timeout while connecting"
                + f"to: {a_device['host']}, error: {str(error)} Skipping."
            )
        # Raise SSH exception
        except SSHException as error:
            print(
                Fore.RED
                + "   ==> WARNING : SSH2 protocol negotiation or logic errors "
                + f" while connecting to: '{a_device['host']}',"
                + f" error: '{str(error)}'  Skipping."
            )
        # Raise Un handled Exception during execution
        except Exception as error:
            print(
                Fore.RED
                + "   ==> WARNING : Unhandled exception while connecting"
                + f"to: {a_device['host']}, error: {str(error)}  Skipping."
            )

        # if SSH to device was successful
        else:
            # loop through the list of commands
            for command in device["command_list"]:
                # defines the file name - a combination of host name and command
                command_name = re.sub("\s", "_", command)
                command_name = re.sub(":", "_", command_name)
                filename = hostname + "_" + command_name
                # set path of the file that will be created.
                # depends on the capture_window paramater
                file = os.path.join(capture_window, filename)
                # print (file)
                # Execute the command on device and parse the output through
                # Genie if there is a parser for it.
                try:
                    output = remote_conn.send_command(
                        command, cmd_verify=True
                    )
                    # print (output)
                    # Error executing command for cisco ios
                    if "Incomplete command" in output or "Ambigious" in output:
                        print(
                            Fore.RED
                            + f"    => Error is executing command `{command}` "
                            + f"msg: {output}"
                        )
                    else:
                        print(f"    => Command: '{command}'")
                        # try writing the contents to a text file. If the command is
                        # not parsed this will be successful
                        with open(file + ".txt", "w") as f:
                            f.write(output)
                except:
                    print(Fore.RED + f"    => Command: '{command} execution failed'")


def compute_diff(dir1, dir2, diff_dir):
    # sourcery skip: simplify-len-comparison, use-named-expression
    """
    Compare text string in 'pre-change' with 'post-change' and produce
    formatted HTML table to be written to a file.

    :param dir1: Directory name containing captured command output
    :param dir2: Directory name containing captured command output
    :param diff_dir: Directory name where the diff files will be stored.
    """

    # List the files of both directories.
    dir1_entries = os.listdir(dir1)
    dir2_entries = os.listdir(dir2)
    # Find captures that were missed in the second window and display on screen
    cd1 = list(set(dir1_entries) - set(dir2_entries))
    if len(cd1) != 0:
        for item in cd1:
            print(
                Fore.YELLOW
                + f"    => Missing {item} capture in Window: '{dir2}'. "
                + "Diff computation will be skipped"
            )
    # Find captures that were missed in the first window and display on screen
    cd2 = list(set(dir2_entries) - set(dir1_entries))
    if len(cd2) != 0:
        for item in cd2:
            print(
                Fore.YELLOW
                + f"    => Missing {item} capture in Window: '{dir1}'. "
                + "Diff computation will be skipped"
            )
    # Find list of file names that are common between the two capture windows.
    common_files = list(set(dir1_entries) & set(dir2_entries))
    # Loop through the file names and compute diff between the two
    # capture windows.
    for file in common_files:
        print(f"    => Computing Diff for: '{file}'")
        # Open file and read contents from Capture Window 1
        try:
            # Handles reading of txt files
            with open(f"{dir1}/{file}", "r") as f1:
                f1 = f1.readlines()
        except Exception:
            # Handles reading of JSON files
            with open(f"{dir1}/{file}", "r") as f1:
                f1 = json.load(f1)
        # Open file and read contents from Capture Window 1
        try:
            # Handles reading of txt files
            with open(f"{dir2}/{file}", "r") as f2:
                f2 = f2.readlines()
        except Exception:
            # Handles reading of JSON files
            with open(f"{dir2}/{file}", "r") as f2:
                f2 = json.load(f2)
        # Defind Diff File name
        diff_file = f"{diff_dir}/{file}.html"
        # Compute Diff and Write to file
        diff = difflib.HtmlDiff().make_file(f1, f2, f"{dir1}", f"{dir2}", context=False)
        with open(diff_file, "w") as f:
            f.writelines(diff)
        # master_diff = difflib.ndiff(f1, f2)
        # print(''.join(master_diff),)
        


cli = click.CommandCollection(sources=[execute_capture, execute_diff])
if __name__ == "__main__":
    cli()
