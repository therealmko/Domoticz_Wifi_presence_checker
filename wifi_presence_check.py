#!/usr/bin/python
#################################################################################################################
#														#
# Thanks and credits go out to the below from which I generously borrowed most of their work :			#
# * SweetPants (not at home : http://www.domoticz.com/forum/viewtopic.php?f=31&t=279)				#
# * Jan (Wifi presence check : http://www.domoticz.com/forum/viewtopic.php?f=11&t=1713				#
# * Chopper_Rob (check_device_online.py : http://www.domoticz.com/forum/viewtopic.php?f=23&t=2595 and		# 
#                https://www.chopperrob.nl/domoticz/5-report-devices-online-status-to-domoticz)			#
#														#
# Script : check_device_online.py										#
# Initial version : SweetPants & Jan N										#
# Version : 1.4													#
# Date : 19-11-2014												#
# Author : xKingx												#
#														#
# Version	Date		Major changes									#
# 1.0		31-10-2014	Added sleep loop | Added sleep time input option				#
# 1.1		04-11-2014	Added Domoticz host as an optional variable					#
# 1.2		05-11-2014	Added option to device json file to turn on optional switch			#
# 1.3		06-11-2014	Added option to search routers based on JSON input and removed ip option	#
# 1.4		19-11-2014	Added community string to JSON SNMP device list and use it to read out router	#
#														#
# To Do														#
# - Look into way results of SNMP walk are gathered as I put a dirty counter hack in				#
# - Look at way to prevent devices that reconnect from triggering presence reporting				#
# - Add way to check which router mobile device is connected to and do switching based of that if desired	#
# - Make SNMP key variable											#
# - Build in check for community string in SNMP version <3							#
#														#
# Notes :													#
# - This scripts assumes you have a SNMP capable dd-wrt router. It's tested with various dd-wrt versions	#
# - This script is scheduled through a crontab entry (if preferred through a wrapper script)			#
# - Script is running on Raspberry Pi, might need to be adapted for other OS'					#
# - To run on RPI with standard Domoticz image add this : sudo apt-get install python libsnmp-python		#
# - To switch on optional switch add that switch idx to json device file (Idx_opt value), default needs to be 0	# 
#														#
#################################################################################################################

import sys
import argparse
import netsnmp
import json
import httplib
import subprocess
import time
from datetime import datetime
from pprint import pprint
from collections import defaultdict

def cli_options():
   cli_args = {}
   #cli_args['community'] = 'public'
   cli_args['version'] = 2
   cli_args['secname'] = None
   cli_args['seclevel'] = 'AuthNoPriv'
   cli_args['authpassword'] = None
   cli_args['authprotocol'] = 'MD5'
   cli_args['privpassword'] = None
   cli_args['privprotocol'] = 'DES'
   cli_args['port'] = 161
   cli_args['jsonmacaddressfile'] = None
   cli_args['jsonsnmproutersfile'] = 'snmp_routers.json'
   cli_args['sleeptime'] = 20
   cli_args['domoticzhost'] = 'localhost:8080'
   cli_args['verbose'] = False

   # Parse the CLI
   parser = argparse.ArgumentParser()
   parser.add_argument('-v', '--version', help='SNMP version', type=int )
   parser.add_argument('-u', '--secname', help='SNMPv3 secname')
   parser.add_argument('-l', '--seclevel', help='SNMPv3 security level (NoAuthNoPriv, AuthNoPriv, AuthPriv)')
   parser.add_argument('-A', '--authpassword', help='SNMPv3 authpassword')
   parser.add_argument('-a', '--authprotocol', help='SNMPv3 authprotocol (MD5, SHA)')
   parser.add_argument('-X', '--privpassword', help='SNMPv3 privpassword')
   parser.add_argument('-x', '--privprotocol', help='SNMPv3 privprotocol (DES, 3DES, AES128)')
   parser.add_argument('-p', '--port', help='SNMP UDP port', type=int)
   parser.add_argument('-f', '--jsonmacaddressfile', help='JSON File with WiFi device MAC addresses', required=True)
   parser.add_argument('-r', '--jsonsnmproutersfile', help='JSON File with Router details', required=True)
   parser.add_argument('-s', '--sleeptime', help='Time between script executions', required=True)
   parser.add_argument('-d', '--domoticzhost', help='Domoticz host:port value if different than standard localhost:8080')
   parser.add_argument('--verbose', help='Verbose mode', action='store_true', default=False)

   # Parse arguments and die if error
   try:
      args = parser.parse_args()
   except Exception:
      sys.exit(2)

   # Assign and verify SNMP arguments
   if args.version:
      cli_args['version'] = args.version
   if (cli_args['version'] != 1) and (cli_args['version'] != 2) and (cli_args['version'] != 3):
      print 'ERROR: Only SNMPv2 and SNMPv3 are supported'
      sys.exit(2)
   if args.secname:
      cli_args['secname'] = args.secname
   if args.secname:
      cli_args['seclevel'] = args.seclevel
   if (not cli_args['secname']) and (cli_args['version'] == 3):
      print '{0} ERROR: SNMPv3 must specify a secname'.format(date_time())
      sys.exit(2)
   if args.authpassword:
      cli_args['authpassword'] = args.authpassword
   if args.authprotocol:
      cli_args['authprotocol'] = args.authprotocol.upper()
   if args.privpassword:
      cli_args['privpassword'] = args.privpassword
   if args.privprotocol:
      cli_args['privprotocol'] = args.privprotocol.upper()
   if args.port:
      cli_args['port'] = args.port
   if args.jsonmacaddressfile:
      cli_args['jsonmacaddressfile'] = args.jsonmacaddressfile
   if args.jsonmacaddressfile:
      cli_args['jsonsnmproutersfile'] = args.jsonsnmproutersfile
   #if (cli_args['version']!= 3) and (not cli_args['community']):
   #   print '{0} ERROR: SNMP community string not defined'.format(date_time())
   #   sys.exit(2)
   if args.sleeptime:
      cli_args['sleeptime'] = args.sleeptime
   if args.domoticzhost:
      cli_args['domoticzhost'] = args.domoticzhost
   if args.verbose:
      cli_args['verbose'] = args.verbose

   return (cli_args)


def is_number(val):
   try:
      float(val)
      return True
   except ValueError:
      return False


def snmp_walk(cli_args, oid, router_list):
   return_results = {}
   session = False
   results_objs = False
   count = 0

   for router, keys in router_list.iteritems():
      location = keys[0]
      commstring = keys[1]
      try:
         session = netsnmp.Session(
         DestHost=router,Version=cli_args['version'], Community=commstring,
         SecLevel=cli_args['seclevel'], AuthProto=cli_args['authprotocol'], AuthPass=cli_args['authpassword'],
         PrivProto=cli_args['privprotocol'], PrivPass=cli_args['privpassword'], SecName=cli_args['secname'], UseNumeric=True)

         results_objs = netsnmp.VarList(netsnmp.Varbind(oid))
         session.walk(results_objs)
      except Exception as e:
         print "{0} ERROR: Occurred during SNMPget for OID {1} from {2}: ({3})".format(date_time(), oid, router, e)
         sys.exit(2)

      # Crash on error
      if (session.ErrorStr):
         print "{0} ERROR: Occurred during SNMPget for OID {1} from {2}: ({3}) ErrorNum: {4}, ErrorInd: {5}".format(date_time(), oid, router, session.ErrorStr, session.ErrorNum, session.ErrorInd)
         sys.exit(2)

      # Construct the results to return
      for result in results_objs:
         if is_number(result.val):
            return_results[('%s.%s') % (result.tag, result.iid)] = ( float(result.val))
         else:
            #return_results[('%s.%s') % (result.tag, result.iid)] = ( result.val)
            return_results[('%s.%s') % (count, result.iid)] = ( result.val)

         count +=1

      return_results.update(return_results)

   # Print each MAC address in verbose mode
   if cli_args['verbose']:
      print "{0} DEBUG: MAC address presence:".format(date_time())
      for oid, mac in return_results.iteritems():
         mac = bin_to_mac(mac).upper() # Convert binary MAC to HEX
         print "{0}".format(mac)

   return return_results


def date_time():
   return datetime.now().strftime('%Y/%m/%d %H:%M:%S')


def bin_to_mac(octet):
   return ":".join([x.encode("hex") for x in list(octet)])


def mac_table(cli_parms, oid, router_list):
   (mac_results) = snmp_walk(cli_parms, oid, router_list)

   return mac_results

       
def mac_in_table(searched_mac, mac_results, oid):
   mac = searched_mac
   # Loop through every MAC address found
   for oid, mac in mac_results.iteritems():
      mac = bin_to_mac(mac).upper() # Convert binary MAC to HEX
      if mac == searched_mac:
         return True

   return False

def read_json(json_file):
    file = json_file

    # Read JSON file
    try:
       json_data = open(file)
       data = json.load(json_data)
       json_data.close()
    except Exception as e:
       print "{0} ERROR: Occurred during reading file {1}: ({2})".format(date_time(), file, e)
       sys.exit(2)

    return data


# This class is derived from Pymoticz, modified to use httplib
class Domoticz:
   def __init__(self, domoticz_host, switch_idx_optional):
      self.host = domoticz_host
      self.idx_opt = switch_idx_optional


   def _request(self, url):
      (ip, port) = self.host.split(":")
      http = httplib.HTTPConnection(ip, port, timeout=2)
      http.request("GET", url)
      result = http.getresponse()

      if (result.status != 200):
         raise Exception

      http.close()
      return json.loads(result.read())


   def list(self):
      url='/json.htm?type=devices&used=true'
      return self._request(url)

   def turn_on(self, _id):
      url='/json.htm?type=command&param=switchlight&idx=%s&switchcmd=On' % (_id)
      return self._request(url)

   def turn_off(self, _id):
      url='/json.htm?type=command&param=switchlight&idx=%s&switchcmd=Off' % (_id)
      return self._request(url)

   def turn_on_if_off(self, _id):
      status=False
      if (self.get_switch_status(_id) == "Off"):
         self.turn_on(_id)
         if (self.idx_opt != 0):
             self.turn_on(self.idx_opt)
         status=True
      return status

   def turn_off_if_on(self, _id):
      status=False
      if (self.get_switch_status(_id) == "On"):
         self.turn_off(_id)
         status=True
      return status

   def turn_on_off(self, _id, _state):
      url='/json.htm?type=command&param=switchlight&idx=%s&switchcmd=%s' % (_id, _state)
      return self._request(url)

   def get_switch_status(self, _id):
      try:
         device = self.get_device(_id)
      except:
         return None

      return device['Status']

   def get_device(self, _id):
      url='/json.htm?type=devices&rid=%s' % (_id)
      try:
         device = self._request(url)
      except:
         return None

      return device['result'][0]


def main():

   # Parse the CLI options
   (cli_parms) = cli_options()

   # Check if I am already running and exit
   if int(subprocess.check_output('ps x | grep \'' + sys.argv[0] + '\' | grep \'' + cli_parms['domoticzhost'] + '\' | grep -cv grep', shell=True)) > 1:
      #print datetime.now().strftime("%H:%M:%S") + "- script already running. exiting."
      sys.exit(0)
 
 
   # Enter recurring loop to act like daemon
   while 1==1:

      # Fill dictionaries with JSON file values
      (data) = read_json(cli_parms['jsonmacaddressfile'])
      (routers) = read_json(cli_parms['jsonsnmproutersfile'])
     
      # Create 1 dictionary with all routers to check
      router_list = defaultdict(list)
      for key, value in routers.items():
          router_list[key].append(value["Location"])
          router_list[key].append(value["CommunityString"])
      router_list = dict(router_list)

      (found_macs) = mac_table(cli_parms, '.1.3.6.1.4.1.2021.255.3.54.1.3.32.1.4', router_list)

      for key, value in data.items():

         # Switch by Index (idx)
         switch_idx = value["Idx"]
	 switch_idx_optional = value["Idx_opt"]

         # Get instance of Domoticz class optional ip:port, default = localhost:8080
         d = Domoticz(cli_parms['domoticzhost'], switch_idx_optional)

         # Get Name of switch from Domoticz
         switch_name = d.get_device(switch_idx)['Name']

         if mac_in_table(key, found_macs, '.1.3.6.1.4.1.2021.255.3.54.1.3.32.1.4'):
            if d.turn_on_if_off(switch_idx) and cli_parms['verbose']: # Turn switch On only if Off
               print "{0} DEBUG: Switching {1}: {2}".format(date_time(), "On", switch_name)
         else:
            if d.turn_off_if_on(switch_idx) and cli_parms['verbose']:# Turn switch Off only if On
               print "{0} DEBUG: Switching {1}: {2}".format(date_time(), "Off", switch_name)

      
      # Sleep for the amount of seconds give to this script before re-checking again
      time.sleep (float(cli_parms['sleeptime']))


if __name__ == "__main__":
   main()
