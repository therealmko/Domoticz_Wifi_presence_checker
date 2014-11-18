###THANKS AND ACKNOWLEDGEMENT
######Thanks and credits go out to the below people on the [Domoticz Forum](http://www.domoticz.com/forum/index.php), from which I generously borrowed most of their work:
* SweetPants ([not at home](http://www.domoticz.com/forum/viewtopic.php?f=31&t=279))
* Jan ([Wifi presence check]( http://www.domoticz.com/forum/viewtopic.php?f=11&t=1713))
* Chopper_Rob ([check_device_online.py](http://www.domoticz.com/forum/viewtopic.php?f=23&t=2595))

###VERSIONING
Script : check_device_online.py                                                                               
Initial version : SweetPants & Jan N                                                                          
Version : 1.3                                                                                                
Date : 18-11-2014                                                                                             
Author : xKingx

```
Version       Date            Major changes
1.0           31-10-2014      Added sleep loop | Added sleep time input option
1.1           04-11-2014      Added Domoticz host as an optional variable
1.2           05-11-2014      Added option to device json file to turn on optional switch
1.3           06-11-2014      Added option to search routers based on JSON input and removed ip option from command line input
```

###TODO
* Add community string to JSON SNMP device list and use it to read out router
* Look into way results of SNMP walk are gathered as I put a dirty counter hack in
* Look at way to prevent devices that reconnect from triggering presence reporting
* Make SNMP key variable

###SETUP
* Disclaimer
  - I have this script running for a couple of weeks already without issues. That being said I cannot guarentee that it will work in other situations and setups. Please take that into account when attempting to use this.

* Pre-requisits
  - This scripts assumes you have a SNMP capable [dd-wrt router](http://dd-wrt.com/). It's tested with various dd-wrt versions on various routers.
    To turn it on in the dd-wrt GUI go to *"services" tab, enable SNMP, set it up like you want and hit "Save" and "Apply Settings"*
  - To run on RPI with standard Domoticz image add these packages from a shell prompt : *sudo apt-get install python libsnmp-python*

* Configuration
  - check_device_online.py takes the following parameters:
  ```
   [-h]                         -> Display help
   [-v VERSION]                 -> SNMP version, default 2 
   [-c COMMUNITY]               -> SNMP v1/2 community string, default public 
   [-u SECNAME]                 -> SNMP v3 security name, default none 
   [-l SECLEVEL]                -> SNMP v3 security level, default AuthNoPriv, options NoAuthNoPriv, AuthNoPriv, AuthPriv
   [-A AUTHPASSWORD]            -> SNMP v3 authentication password, default None
   [-a AUTHPROTOCOL]            -> SNMP v3 authentication protocol, default MD5, options MD5, SHA  
   [-X PRIVPASSWORD]            -> SNMP v3 private password, default None 
   [-x PRIVPROTOCOL]            -> SNMP v3 private protocol, default DES, options DES, 3DES, AES128 
   [-p PORT]                    -> SNMP UDP port, default 161 
   [-d DOMOTICZHOST]            -> ip and port of your Domoticz instalation
   -f JSONMACADDRESSFILE        -> Full path to file with mobile device information
   -r JSONSNMPROUTERSFILE       -> Full path to file with router information
   -s SLEEPTIME                 -> Amount of time in seconds between SNMP checks
   [--verbose]                  -> Output verbose information
  ```

  - snmp_routers.json follows this setup
  ```
   ipaddress                    -> IP address of your router (mandatory)
   "Vendor"                     -> Router vendor - not used a.t.m.
   "Model"                      -> Router model - not used a.t.m.
   "Purpose"                    -> Router purpose - not used a.t.m.
   "Location"                   -> Router location - not used a.t.m.
   "CommunityString"            -> Router SNMP communitystring - not used a.t.m.
  ```

  - wifi_devices.json follows this setup
  ```
    mobile mac address          -> MAC address of your mobile device (mandatory)
    "Vendor"                    -> Mobile device vendor - not used a.t.m.
    "Type"                      -> Mobile device type - not used a.t.m.
    "Model"                     -> Mobile device model - not used a.t.m.
    "Owner"                     -> Mobile device owner - not used a.t.m.
    "Idx"                       -> Domoticz switch to turn on and off (mandatory)
    "Idx_opt"                   -> Additional Domoticz switch to turn on and off (mandatory, 0 if not used)
  ```

###EXECUTION
* This script is scheduled through a crontab entry (if preferred through a wrapper script). My crontab entry for a script looks like this:

`* * * * * /home/pi/domoticz/scripts/wifi_presence_check.sh`
