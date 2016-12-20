# nxos-config-generator #
## Requirements ##

1. <a href="https://www.python.org/downloads/">**Python 3**</a>
2. <a href="https://pip.pypa.io/en/stable/installing/">Download and install pip (package manager)</a>
3. <a href="http://jinja.pocoo.org/docs/dev/intro/#as-a-python-egg-via-easy-install">Download and install Jinja2 via pip</a>

## Install ##
Clone the repo
    `git clone https://github.com/tomcooperca/nxos-config-generator`
Create the required output directory in the same location as the script (named "configs")
    `cd nxos-config-generator`
    `mkdir configs`

## Usage ##
Run the script via `python buildFabric.py`
No arguments are required for this script.  
All configuration files are saved on in the `configs` directory. The name prefix is used for the specific directory for the configurations.
