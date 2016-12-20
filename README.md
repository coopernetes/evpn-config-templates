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

## Preview ##
```
python config_generator.py
Mgmt Subnet [x.x.x.x]: 10.1.1.0
Loopback Subnet [x.x.x.x]: 10.1.2.0
PTP Subnet [x.x.x.x]: 10.1.3.0
Name Prefix [first seven characters in hostnames]: DC1SFRM
Number of Spines [2,4]: 4
BGP ASN [1-65535]: 65501
OSPF Area ID [x.x.x.x]: 0.0.0.1
VXLAN Multicast Group Subnet [x.x.x.x]: 239.0.0.0
VXLAN VRF Name [Max 32 characters. Leave blank for default 'prod']: vxlan

        Confirm? [y/n]

Successfully written template <Template 'leaf-template.j2'> to DC1SFRMLF01.txt
Successfully written template <Template 'leaf-template.j2'> to DC1SFRMLF02.txt
Successfully written template <Template 'leaf-template.j2'> to DC1SFRMLF03.txt
Successfully written template <Template 'leaf-template.j2'> to DC1SFRMLF04.txt
...
Successfully written template <Template 'bleaf-template.j2'> to DC1SFRMBL01.txt
Successfully written template <Template 'bleaf-template.j2'> to DC1SFRMBL02.txt
Successfully written template <Template 'spine-template.j2'> to DC1SFRMSP01.txt
Successfully written template <Template 'spine-template.j2'> to DC1SFRMSP02.txt
...
```

## Key Assumptions ##
Configurations generated have the following assumptions for creation:
  * N9K-9332PQ for spine layer (or equivalent) for 32x40G ports of leaf-to-spine uplinks
  * All underlay point-to-point interfaces use unique addressing; templates can be modified for using Loopback0 via ip unnumbered
  * Assymetric IRB is enabled via the L3VNI (Vlan 10) and is configured on all leaf switches (inc. border leaf)
  * OSPF as underlay IGP. An area ID is configured for this fabric but area 0.0.0.0 is perfectly valid as well.
  * PIM enabled for VXLAN EVPN BUM control plane (for broadcast/unknown unicasts and multicast for a VXLAN)
  * N9K-9372PX, N9K-9372TX, N9K-93180YC-EX or equivalents for the leaf layer. Uplinks assume Ethernet1/49 - 1/54 are present on the device for 4x40G uplinks and vPC peerlink
