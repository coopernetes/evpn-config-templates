#!/usr/local/bin/python3.5
import argparse
import getpass
import ipaddress
import json
import os
import pprint
import re
import sys
import yaml
from jinja2 import Template, Environment, FileSystemLoader

# Get operating system type (windows or non-windows) via sys.platform
osType = sys.platform

# only import readline if OS is NOT Windows
if osType != "win32":
    import readline


# config directory
homedir = os.path.realpath(os.path.split(__file__)[0])
config_output = os.path.join(homedir, 'configs')

# Jinja global vars
LeafTemplateFilename = 'leaf-template.j2'
BLeafTemplateFilename = 'bleaf-template.j2'
SpineTemplateFilename = 'spine-template.j2'

# Fixed constants; used for constructing variables
MAX_GEN1_LEAFS = 30
MAX_GEN1_PAIRS = 15
MAX_GEN2_LEAFS = 62
MAX_GEN2_PAIRS = 31
START_SPINE_MGMTIP = 4
START_BLEAF_MGMTIP = 8
START_LEAF_MGMTIP = 10
START_GEN1_LO1IP = 100
START_GEN1_VLAN2IP = 199
START_GEN2_LO1IP = 70
START_GEN2_VLAN2IP = 189
START_VTEPIP = 150
MGMT_MASK = '24'
GEN1_PTP = 64
GEN2_PTP = 128
START_VPC = 100
START_IF_NUM = 49


def build_spine_vars(user_input, leaf_vars, bleaf_vars):
    spine_mgmt_ipaddresses = []
    spine_hostnames = []
    spine_loopback0_ipaddresses = []
    leaf_bgp_peers = []
    spine_interfaces = []

    mgmt_network = user_input['mgmt_subnet']
    loopback_network = user_input['loopback_subnet']
    ptp_network = user_input['ptp_subnet']

    mgmt_default_gateway = str(mgmt_network[1])
    pim_anycast_rp = str(loopback_network.broadcast_address)

    leaf_numbers = range(1, MAX_GEN1_LEAFS + 1)
    for bleaf in bleaf_vars:
        leaf_bgp_peers.append({'ip': bleaf['loopback0_ip'], 'description': bleaf['hostname']})

    for leaf in leaf_vars:
        leaf_bgp_peers.append({'ip': leaf['loopback0_ip'], 'description': leaf['hostname']})

    for spine in range(0, user_input['num_spines']):
        this_spine_interfaces = []
        spine_hostnames.append("{0}SP0{1}".format(user_input['name_prefix'], str(spine + 1)))
        spine_mgmt_ipaddresses.append(str(mgmt_network[spine + START_SPINE_MGMTIP + 1]))
        spine_loopback0_ipaddresses.append(str(loopback_network[spine + 33]))

        for leaf_number in leaf_numbers:
            int_portnum = 'Ethernet1/{0}'.format(leaf_number)
            int_description = "I,{0}_{1},{2}/31,POINT-TO-POINT,area {3}".format(
                leaf_vars[leaf_number - 1]['hostname'],
                'Ethernet1/' + str(START_IF_NUM + spine),
                leaf_vars[leaf_number - 1]['interfaces'][spine]['ipaddress'],
                user_input['ospf_area'])
            if leaf_number == 1:
                int_ipaddress = str(ptp_network[GEN1_PTP * spine])
            else:
                int_ipaddress = str(ptp_network[((leaf_number - 1) * 2) + (GEN1_PTP * spine)])

            this_spine_interfaces.append({'portnum': int_portnum,
                                        'ipaddress': int_ipaddress,
                                        'description': int_description})
        for bleaf in range(0, 2):
            this_bleaf_name = '{0}BL0{1}'.format(user_input['name_prefix'], str(bleaf + 1))
            int_portnum = 'Ethernet1/{0}'.format(str(31 + bleaf))
            int_ipaddress = str(ptp_network[(((bleaf + 31) * 2) - 2) + (GEN1_PTP * spine)])
            int_description = "I,{0}_{1},{2}/31,POINT-TO-POINT,area {3}".format(
                              this_bleaf_name,
                              'Ethernet1/' + str(START_IF_NUM + spine),
                              str(ptp_network[(((bleaf + 31) * 2) - 1) + (GEN1_PTP * spine)]),
                              user_input['ospf_area'])

            this_spine_interfaces.append({'portnum': int_portnum,
                                        'ipaddress': int_ipaddress,
                                        'description': int_description})
        spine_interfaces.append(this_spine_interfaces)

    spine_vars = {'spines': []}
    for i in range(0, user_input['num_spines']):
        spine_vars['spines'].append({'hostname': spine_hostnames[i],
                                     'loopback0_ip': spine_loopback0_ipaddresses[i],
                                     'pim_anycast_rp': pim_anycast_rp,
                                     'pim_rps': spine_loopback0_ipaddresses,
                                     'interfaces': spine_interfaces[i],
                                     'bgp_asn': user_input['bgp_asn'],
                                     'ospf_area': user_input['ospf_area'],
                                     'multicast_group_range': (user_input['multicast_group_range'] + '/24'),
                                     'leaf_bgp_peers': leaf_bgp_peers,
                                     'mgmt_ipaddress': spine_mgmt_ipaddresses[i],
                                     'mgmt_default_gateway': mgmt_default_gateway,
                                     'mgmt_ipmask': MGMT_MASK,
                                     })

    return spine_vars


def build_bleaf_vars(user_input, leaf_vars):
    bleaf_mgmt_ipaddresses = []
    bleaf_hostnames = []
    bleaf_loopback0_ipaddresses = []
    bleaf_loopback1_ipaddresses = []
    spine_bgp_peers = leaf_vars[0]['spine_bgp_peers']
    bleaf_interfaces = []

    mgmt_network = user_input['mgmt_subnet']
    loopback_network = user_input['loopback_subnet']
    ptp_network = user_input['ptp_subnet']

    mgmt_default_gateway = str(mgmt_network[1])
    pim_anycast_rp = leaf_vars[0]['pim_anycast_rp']
    vxlan_vni_prefix = leaf_vars[0]['vxlan_vni_prefix']

    for bleaf in range(0, 2):
        bleaf_mgmt_ipaddresses.append(str(mgmt_network[(bleaf + 1) + START_BLEAF_MGMTIP]))
        bleaf_hostnames.append('{0}BL0{1}'.format(user_input['name_prefix'], str(bleaf + 1)))
        bleaf_loopback0_ipaddresses.append(str(loopback_network[31 + bleaf]))
        bleaf_loopback1_ipaddresses.append(str(loopback_network[131 + bleaf]))
        this_bleaf_interfaces = []
        for spine in range(0, user_input['num_spines']):
            this_spine_name = '{0}SP0{1}'.format(user_input['name_prefix'], str(spine + 1))
            int_portnum = 'Ethernet1/{0}'.format(START_IF_NUM + spine)
            int_ipaddress = str(ptp_network[(((bleaf + 31) * 2) - 1) + (GEN1_PTP * spine)])
            int_description = "I,{0}_{1},{2}/31,POINT-TO-POINT,area {3}".format(
                              this_spine_name,
                              "Ethernet1/" + str(bleaf + 31),
                              str(ptp_network[(((bleaf + 31) * 2) - 2) + (GEN1_PTP * spine)]),
                              user_input['ospf_area'])

            this_bleaf_interfaces.append({'portnum': int_portnum,
                                        'ipaddress': int_ipaddress,
                                        'description': int_description})
        bleaf_interfaces.append(this_bleaf_interfaces)
    bleaf_vars = {'bleafs': []}
    for i in range(0, 2):
        bleaf_vars['bleafs'].append({'hostname': bleaf_hostnames[i],
                                     'loopback0_ip': bleaf_loopback0_ipaddresses[i],
                                     'loopback1_ip': bleaf_loopback1_ipaddresses[i],
                                     'mgmt_ipaddress': bleaf_mgmt_ipaddresses[i],
                                     'mgmt_default_gateway': mgmt_default_gateway,
                                     'mgmt_ipmask': MGMT_MASK,
                                     'multicast_group_range': (user_input['multicast_group_range'] + '/24'),
                                     'ospf_area': user_input['ospf_area'],
                                     'bgp_asn': user_input['bgp_asn'],
                                     'vxlan_vni_prefix': vxlan_vni_prefix,
                                     'vxlan_vrf': user_input['vxlan_vrf'],
                                     'pim_anycast_rp': pim_anycast_rp,
                                     'interfaces': bleaf_interfaces[i],
                                     'spine_bgp_peers': spine_bgp_peers})

    return bleaf_vars


def build_leaf_vars(user_input):
    vpc_domains = []
    is_first_leaf = []
    leaf_mgmt_ipaddresses = []
    leaf_hostnames = []
    leaf_loopback0_ipaddresses = []
    leaf_loopback1_ipaddresses = []
    leaf_loopback1_vtep_ipaddresses = []
    peer_leafs = []
    peer_leaf_mgmt_ipaddresses = []
    leaf_vlan2_ipaddresses = []
    leaf_vlan2_descriptions = []
    spine_bgp_peers = []
    leaf_interfaces = []

    mgmt_network = user_input['mgmt_subnet']
    loopback_network = user_input['loopback_subnet']
    ptp_network = user_input['ptp_subnet']
    mgmt_default_gateway = str(mgmt_network[1])
    vxlan_vni_prefix = str(user_input['bgp_asn'])[2:]
    pim_anycast_rp = str(user_input['loopback_subnet'].broadcast_address)

    leaf_numbers = range(1, MAX_GEN1_LEAFS + 1) # list of int's 1-30
    pair_numbers = range(1, MAX_GEN1_PAIRS + 1) # list of int's 1-15
    for leaf_number in leaf_numbers:
        this_leaf_interfaces = []
        this_spine_bgp_peers = []
        for spine in range(0, user_input['num_spines']):
            this_spine_name = "{0}SP0{1}".format(user_input['name_prefix'], str(spine + 1))
            int_portnum = "Ethernet1/{0}".format(START_IF_NUM + spine)
            if leaf_number == 1:
                int_ipaddress = str(ptp_network[leaf_number + (GEN1_PTP * spine)])
                int_description = "I,{0}_{1},{2}/31,POINT-TO-POINT,area {3}".format(
                                 this_spine_name,
                                 "Ethernet1/" + str(leaf_number),
                                 str(ptp_network[GEN1_PTP * spine]),
                                 user_input['ospf_area'])
            else:
                int_ipaddress = str(ptp_network[(((leaf_number - 1) * 2) + 1) + (GEN1_PTP * spine)])
                int_description = "I,{0}_{1},{2}/31,POINT-TO-POINT,area {3}".format(
                                  this_spine_name,
                                  "Ethernet1/" + str(leaf_number),
                                  str(ptp_network[((leaf_number - 1) * 2) + (GEN1_PTP * spine)]),
                                  user_input['ospf_area'])

            this_leaf_interfaces.append({'portnum': int_portnum,
                                         'ipaddress': int_ipaddress,
                                         'description': int_description})
            this_spine_bgp_peers.append({'description': this_spine_name,
                                         'ip': '{}'.format(str(loopback_network[33 + spine]))})
        leaf_interfaces.append(this_leaf_interfaces)
        spine_bgp_peers.append(this_spine_bgp_peers)
        leaf_mgmt_ipaddresses.append(str(mgmt_network[leaf_number + START_LEAF_MGMTIP]))
        leaf_loopback0_ipaddresses.append(str(loopback_network[leaf_number]))
        leaf_loopback1_ipaddresses.append(str(loopback_network[START_GEN1_LO1IP + leaf_number]))
        leaf_vlan2_ipaddresses.append(str(loopback_network[START_GEN1_VLAN2IP + leaf_number]))
        if (leaf_number % 2) > 0:
            peer_leaf_mgmt_ipaddresses.append(str(mgmt_network[leaf_number + START_LEAF_MGMTIP + 1]))
            is_first_leaf.append(True)
            if leaf_number < 10:
                leaf_hostnames.append(user_input['name_prefix'] + 'LF0' + str(leaf_number))
                this_leaf_peer = user_input['name_prefix'] + 'LF0' + str(leaf_number + 1)
                peer_leafs.append(this_leaf_peer)
            else:
                leaf_hostnames.append(user_input['name_prefix'] + 'LF' + str(leaf_number))
                peer_leafs.append(user_input['name_prefix'] + 'LF' + str(leaf_number + 1))

            leaf_vlan2_descriptions.append("I,{0}_Vlan2,{1}/31,POINT-TO-POINT,area {2}".format(
                                           this_leaf_peer,
                                           str(loopback_network[START_GEN1_VLAN2IP + leaf_number + 1]),
                                           user_input['ospf_area']))

        else:
            peer_leaf_mgmt_ipaddresses.append(str(mgmt_network[leaf_number + START_LEAF_MGMTIP - 1]))
            is_first_leaf.append(False)
            if leaf_number < 10:
                leaf_hostnames.append(user_input['name_prefix'] + 'LF0' + str(leaf_number))
                this_leaf_peer = user_input['name_prefix'] + 'LF0' + str(leaf_number - 1)
                peer_leafs.append(this_leaf_peer)
            else:
                leaf_hostnames.append(user_input['name_prefix'] + 'LF' + str(leaf_number))
                peer_leafs.append(user_input['name_prefix'] + 'LF' + str(leaf_number - 1))

            leaf_vlan2_descriptions.append("I,{0}_Vlan2,{1}/31,POINT-TO-POINT,area {2}".format(
                                           this_leaf_peer,
                                           str(loopback_network[START_GEN1_VLAN2IP + leaf_number - 1]),
                                           user_input['ospf_area']))

    for pair_number in pair_numbers:
        vpc_domains.extend([str(START_VPC + pair_number), str(START_VPC + pair_number)])
        leaf_loopback1_vtep_ipaddresses.extend([str(loopback_network[START_VTEPIP + pair_number]), str(loopback_network[START_VTEPIP + pair_number])])

    leaf_vars = {'leafs': []}
    for i in range(0, MAX_GEN1_LEAFS):
        leaf_vars['leafs'].append({'hostname': leaf_hostnames[i],
                                   'first_leaf': is_first_leaf[i],
                                   'loopback0_ip': leaf_loopback0_ipaddresses[i],
                                   'loopback1_ip': leaf_loopback1_ipaddresses[i],
                                   'loopback1_vtepip': leaf_loopback1_vtep_ipaddresses[i],
                                   'vpc_domain': vpc_domains[i],
                                   'mgmt_ipaddress': leaf_mgmt_ipaddresses[i],
                                   'mgmt_default_gateway': mgmt_default_gateway,
                                   'mgmt_ipmask': MGMT_MASK,
                                   'peer_leaf_mgmt_ip': peer_leaf_mgmt_ipaddresses[i],
                                   'peer_leaf': peer_leafs[i],
                                   'multicast_group_range': (user_input['multicast_group_range'] + '/24'),
                                   'ospf_area': user_input['ospf_area'],
                                   'bgp_asn': user_input['bgp_asn'],
                                   'vxlan_vni_prefix': vxlan_vni_prefix,
                                   'vxlan_vrf': user_input['vxlan_vrf'],
                                   'pim_anycast_rp': pim_anycast_rp,
                                   'vlan2_ip': leaf_vlan2_ipaddresses[i],
                                   'vlan2_description': leaf_vlan2_descriptions[i],
                                   'interfaces': leaf_interfaces[i],
                                   'spine_bgp_peers': spine_bgp_peers[i]})

    return leaf_vars


def write_template_to_file(vars,template,output_filename,output_dir):
    env = Environment(loader=FileSystemLoader(homedir)) # Location of templates
    output_file = open(os.path.join(output_dir,output_filename),'w')
    template = env.get_template(template)
    result = template.render(vars)
    output_file.write(result)
    return "Successfully written template {0} to {1}".format(template,output_filename)


def create_fabric_directory(fabric_name, root_dir):
    resultant_dir = os.path.join(root_dir, fabric_name)
    # check if dir exists and is dir; if not, create it
    if not os.path.exists(resultant_dir):
        os.makedirs(resultant_dir)
    else:
        if not os.path.isdir(resultant_dir):
            os.remove(resultant_dir)
            os.makedirs(resultant_dir)
    return resultant_dir


def get_user_input():
    user_input = {}
    while True:
        while True:
            try:
                mgmt_subnet = ipaddress.IPv4Network(str(input("Mgmt Subnet [x.x.x.x]: ")+'/24'))
                loopback_subnet = ipaddress.IPv4Network(str(input("Loopback Subnet [x.x.x.x]: ")+'/24'))
                ptp_subnet = ipaddress.IPv4Network(str(input("PTP Subnet [x.x.x.x]: ")+'/24'))
            except (ipaddress.AddressValueError, ValueError):
                print("Invalid Input - must be valid subnet for Mgmt/Loopback/PTP")
                continue
            else:
                break

        while True:
            try:
                name_prefix = str(input("Name Prefix [first seven characters in hostnames]: "))
                if len(name_prefix) != 7:
                    print("Invalid Input - prefix must be exactly seven characters (alphanumeric)")
                    continue
                else:
                    break
            except ValueError:
                print("Invalid Input - prefix must be exactly seven characters (alphanumeric)")

        while True:
            try:
                num_spines = int(input("Number of Spines [2,4]: "))
            except ValueError:
                print("Invalid Input - only the number 2 or 4 is accepted")
                continue
            if num_spines == 2 or num_spines == 4:
                break
            else:
                print("Input Invalid - number of spines must be either 2 or 4")
                continue
        while True:
            try:
                bgp_asn = int(input("BGP ASN [1-65535]: "))
                if bgp_asn < 1 or bgp_asn > 65535:
                    print("Invalid Input - BGP ASN must be between 1 and 65535")
                    continue
                else:
                    break
            except ValueError:
                print("Invalid Input - BGP ASN must be a number between 1 and 65535")
                continue
        while True:
            ospf_area = str(input("OSPF Area ID [x.x.x.x]: "))
            match_id = re.search(r'^\d+\.\d+\.\d+\.\d+$', ospf_area)
            if not match_id:
                print("Invalid Input - area ID must be dotted decimal")
                continue
            else:
                break
        while True:
            try:
                multicast_group_range = str(input("VXLAN Multicast Group Subnet [x.x.x.x]: "))
                if not ipaddress.IPv4Address(multicast_group_range).is_multicast:
                    print("Invalid Input - must be a valid multicast group range (Class D address)")
                    continue
                else:
                    break
            except ipaddress.AddressValueError:
                print("Invalid Input - not a valid multicast address.")

        while True:
            vxlan_vrf = str(input("VXLAN VRF Name [Max 32 characters. Leave blank for default 'prod']: "))
            if vxlan_vrf != '' and len(vxlan_vrf) > 32:
                print("Input Invalid - name must be no more than 32 characters long")
                continue
            elif vxlan_vrf == '':
                vxlan_vrf = 'prod'
                break
            else:
                break
        option = str(input("\n\tConfirm? [y/n] "))
        if option == 'y' or option == 'Y':
            user_input.update({'mgmt_subnet': mgmt_subnet,
                              'loopback_subnet': loopback_subnet,
                              'ptp_subnet': ptp_subnet,
                              'name_prefix': name_prefix,
                              'bgp_asn': str(bgp_asn),
                              'ospf_area': ospf_area,
                              'multicast_group_range': multicast_group_range,
                              'vxlan_vrf': vxlan_vrf,
                              'num_spines': num_spines})
            break
        else:
            continue

    return user_input


def generate_device_configs(user_input):
    fabric_dir = create_fabric_directory(user_input['name_prefix'],config_output)
    leaf_vars = build_leaf_vars(user_input)
    for leaf in leaf_vars['leafs']:
        print(write_template_to_file(leaf,LeafTemplateFilename,leaf['hostname']+".txt",fabric_dir))

    bleaf_vars = build_bleaf_vars(user_input, leaf_vars['leafs'])
    for bleaf in bleaf_vars['bleafs']:
        print(write_template_to_file(bleaf,BLeafTemplateFilename,bleaf['hostname']+".txt",fabric_dir))

    spine_vars = build_spine_vars(user_input, leaf_vars['leafs'], bleaf_vars['bleafs'])
    for spine in spine_vars['spines']:
        print(write_template_to_file(spine,SpineTemplateFilename,spine['hostname']+".txt",fabric_dir))


def main(argv):
    user_input = get_user_input()
    generate_device_configs(user_input)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
