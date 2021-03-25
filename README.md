[![Python 3](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue)](https://www.python.org/downloads/)
[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/SudarshanVK/Configuration_Diff_Generator)

# Configuration Diff Generator

This tool helps to collect the output of specified commands during defined capture windows and produces HTML diff files highlighting the differences in the command output.

# Installation

Execute the following command to install the tool. It is highly recommended that this is done in a dedicated virtual environment.

```
pip install -r requirements.txt
```

# Usage

The application has two execution modes:

* __capture__: Used to capture command output and save files.
* __diff__: Used to compute diff between command output that was captured earlier.
  Example:

```
run --help
Usage: run [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  capture  Use this mode to capture command output and save to files.
  diff     Use this mode to compute diff in command output between two...
```

### Capture Mode

The capture mode accepts two arguments:

* **-w**: A string value that defines the capture window (eg: Pre-change)
* **-i**: Inventory file that contains the list of devices and commands to execute. rever to [sample_device.yaml](device.yaml) for example.
  Example

```
run capture [OPTIONS]

  Use this mode to capture command output and save to files.

Options:
  -w TEXT  Enter Capture Window.  [required]
  -i TEXT  Enter inventory file.  [required]
  --help   Show this message and exit.
```

### Diff mode

The diff mode accepts two arguments:

* **-w1**: The first capture window against which the diff is to be generated.
* **-w2**: The second capture window against which the diff is to be generated.
  Example

```
run diff --help
Usage: run diff [OPTIONS]

  Use this mode to compute diff in command output between two captures.

Options:
  -w1 TEXT  Enter Capture Window(pre-change)  [required]
  -w2 TEXT  Enter Capture Window to diff against(post-change)  [required]
  --help    Show this message and exit.
```

# How it works

In **Capture mode**, the application will prompt for the `username` and `password` used to login to the deivces. The command output is stored in a dedicated folder that is created with the capture window parameter that was passed. If a capture already exists for the window, the application will warn and terminate. In the event that the application was not able to execute a particular command on a device, a warning is displayed on screen but the application does not terminate.

In **Diff mode**, the application generates HTML diff for command output in the provided capture window.It looks for any captures that are present in one window and not the other and a warning is displayed on screen for those. The results are saved in a dedicated folder that is created.

# Sample Output

### Capture mode

![alt text](images/capture_mode.png)

### Sample diff output![alt text](images/diff_mode.png)

![alt text](images/diff.png)

## Supported Vendors

The script uses netmiko to connect to devices and execute commands.
Supported `device_types` can be found [here.](https://github.com/ktbyers/netmiko/blob/master/netmiko/ssh_dispatcher.py) see CLASS_MAPPER keys.

Some of the commonly used device types and os to be used are as below:


| Vendor | device_type |
| :- | :-: |
| Cisco IOS | cisco_ios |
| Cisco Nexus | cisco_nxos |
| Cisco IOS-XE | cisco_xe |
| Juniper | juniper_junos |
| Arista | arista_eos |
| Palo Alto FW | paloalto_panos |

Sudarshan Vijaya Kumar
