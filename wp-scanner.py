#!/usr/bin/python
# WordPress Version Scanner
# v1.2
# Scan paths for outdated WordPress installations
# If MySQLdb available then wp-config.php credentials will be checked for valid installations
#
# URL: www.admingeekz.com
# Contact: sales@admingeekz.com
#
#
# Copyright (c) 2013, AdminGeekZ Ltd
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2, as
# published by the Free Software Foundation.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
import sys
#Check for version 2.3 or greater
if int(sys.version_info[1] <= 2):
  print "We need python v2.3 or above"
  sys.exit(1)

import urllib
import re
import os
import datetime

debug="no" #disable debugging
path=['/home', '/var/www', '/www'] #Paths to scan

#If MySQLdb exists enable fetching blog of url and verifying of DB credentials
try:
  import MySQLdb
  checksiteurl="yes"
except:
  checksiteurl="no"

#Override path if cPanel exists,  this reduces scan time to only valid accounts and skips virtfs
if os.path.exists('/usr/local/cpanel/version'):
  path=[]
  for base, dir, files in os.walk("/var/cpanel/users"):
    for f in files:
      #Only accept numbers, letters and under score for usernames
      if re.search("^(\w+)$", f):
        path.append("/home/"+f+"/public_html")


#Sort paths in alphabetical order
path.sort()

#original function based on wp-upgrade.py by stevenbrown.ca
def get_latest_wp_version(wp_latest_url="http://wordpress.org/latest.tar.gz"):
    """Returns a tuple containing the version string of the latest version of 
    wordpress and the full filename.
    'wp_latest_url' is a link to the latest tar.gz release."""

    # get version of latest available
    f = urllib.urlopen(wp_latest_url)
    filename = f.info()["content-disposition"]
    m = re.search(".*filename=(\S+).*", filename)
    filename = m.group(1)
    m = re.search(".*?([\.\d]+)\..*", filename)
    version = m.group(1)
    f.close()
    
    return version, filename

def get_wp_version(wp_directory="wordpress"):
    """Returns the version string of wordpress in wp_directory.
    'wp_directory' is the path to the wordpress folder to check."""
 
    vfilename = os.path.join(wp_directory, "wp-includes/version.php")
    try:
      vfile = open(vfilename)
      # extract version string from "$wp_version = 'the_string';" in version.php
      pattern = re.compile("\s*\$wp_version\s*=\s*.([\.\d]+).\s*;?")
      version = "unknown"
    
      for l in vfile:
        m = re.search(pattern, l)
        if m: 
          version = m.group(1)
          break
            
      return version
    except:
      return "unknown"

def wpconfig(path):
    """Extract the configuration variables from wp-config.php
    'path' is the path to the wp-config file"""
    db_params = {}
    db_params['table_prefix'] = 'wp_'
    mapping = {
         'DB_NAME'    :'db',
         'DB_USER'    :'user',
         'DB_PASSWORD':'passwd',
         'DB_HOST'    :'host',
      }
    vars = re.compile(
        r"^\s*define\s*\(\s*'(?P<key>DB_[A-Z]+)'\s*,\s*'(?P<val>.*)'\s*\)\s*;")
    TablePrefix = re.compile(
        r"^\s*\$table_prefix\s*=\s*'(\w+)'\s*;")
    checkpath=os.path.join(path, "wp-config.php")
    if not os.path.exists(checkpath):
      checkpath=os.path.join(path, "../wp-config.php")
      checksettings=os.path.join(path, "../wp-settings.php")
      if os.path.exists(checksettings):
        return "invalid"
      if not os.path.exists(checkpath):
        return "invalid"

    f = file(checkpath)
    while(True):
     line = f.readline()
     if not line:
       break
     match = vars.match(line)
     if match:
       key = match.group('key')
       if key in mapping:
         db_params[ mapping[key] ] = match.group('val')
     match = TablePrefix.match(line)
     if match:
       db_params['table_prefix'] = match.group(1)

    return db_params

def getsiteurl(dbinfo):
    """Obtain the siteurl value from the wp_options table
    'dbinfo' the database information and table prefix"""
    try:
      db = MySQLdb.connect(dbinfo['host'],dbinfo['user'],dbinfo['passwd'],dbinfo['db'])
      cursor = db.cursor()
      query = "SELECT option_value from " + dbinfo['table_prefix'] + "options WHERE option_name='siteurl' LIMIT 1"
      cursor.execute(query)
      out=cursor.fetchone()
      db.close()
      return out[0] 
    except:
      return "invalid"

def find_wp_installs(path="/",wpname="wp-cron.php"):
   """Scans directory for wordpress installations.
   'paths' is the path to scan.
   'wpname' is the name of the file to scan for.""" 

   results = []
   for num, p in enumerate(path):
     if debug == "yes": print "%s DEBUG: processing %s (%s/%s)" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), p, num, len(path))
     for base, dir, files in os.walk(p):
       files = [f for f in files if f == wpname]
       if files:
         results.append(base)
   return results 

if __name__ == "__main__":
 try:
   url=""
   wplatest, newest_filename = get_latest_wp_version()
   for wpinstall in find_wp_installs(path):
     configvars = wpconfig(wpinstall)
     #If the directory doesn't have a valid wp-config.php, common for test installs/fresh installs then ignore
     if configvars == "invalid":
       continue
     if checksiteurl == "yes": 
       #Check the credentials in wp-config.php are valid otherwise ignore
       url=getsiteurl(configvars)
       if url == "invalid":
         continue

     outdated=""
     curver = get_wp_version(wpinstall)
     if curver < wplatest:
       outdated="- OUTDATED "

     print "%s - %s %s- %s - %s" % (url, wpinstall, outdated, curver, wplatest)

 except Exception,e:
  print "An Exception occurred.  Scan not performed."
  if debug == "yes": print e
  sys.exit(1)

