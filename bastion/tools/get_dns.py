#!/usr/bin/python

import json
import pycurl
import StringIO
import optparse

def get_options():
    usage = "%prog [--verbose]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("--debug", "-d", dest="debug", action="store_true",
                      default=False, help="Debug Mode")
    parser.add_option("--cert", action="store" , type="string",
                  dest="cert", default="/etc/pki/tls/certs/system.crt",
                  help="machine certificate", metavar="FILE")
    parser.add_option("--ca", action="store" , type="string",
                  dest="ca", default="/etc/pki/tls/certs/ca-bundle.crt",
                  help="certificate authority", metavar="FILE")
    parser.add_option("--key", action="store" , type="string",
                  dest="key", default="/etc/pki/tls/private/system.key",
                  help="machine key", metavar="FILE")
    parser.add_option("--url", action="store" , type="string",
                  dest="url", default="http://localhost:8080/export_dns",
                  help="url", metavar="URL")
    (options, args) = parser.parse_args()
    return options, args

def main():
    options, args = get_options()
    bastion_url=options.url
    bastion_file = StringIO.StringIO()
    curl = pycurl.Curl()
    curl.setopt(pycurl.CAINFO, options.ca)
    curl.setopt(pycurl.SSLCERT, options.cert)
    curl.setopt(pycurl.SSLKEY, options.key)
    curl.setopt(pycurl.SSL_VERIFYPEER, False)
    curl.setopt(pycurl.SSL_VERIFYHOST, 2)
    curl.setopt(pycurl.URL, bastion_url)
    curl.setopt(pycurl.WRITEFUNCTION, bastion_file.write)
    curl.perform()
    bastion_file.seek(0)
    bastion_data=json.loads(bastion_file.read())['data']
    for line in bastion_data:
        print line

if __name__ == "__main__":
    main()
