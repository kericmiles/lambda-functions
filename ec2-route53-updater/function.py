import logging
import json
import boto3
import os
import time
import re
from datetime import datetime
zone_id_override = os.environ.get("zone_id_override")
zone_name_override = os.environ.get("zone_name_override")

logger = logging.getLogger()
logger.setLevel(logging.INFO)
route53 = boto3.client('route53')
ec2 = boto3.resource('ec2')
compute = boto3.client('ec2')

def lambda_handler(event, context):
    dns_zone_id = None
    instance_id = event['detail']['instance-id']
    region = event['region']
    state = event['detail']['state']


    instance = compute.describe_instances(InstanceIds=[instance_id])
    instance_dump = json.dumps(instance,default=json_serial)
    instance_attributes = json.loads(instance_dump)
    try:
        tags = instance['Reservations'][0]['Instances'][0]['Tags']
    except:
        tags = []
    
    try:
        public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
        public_dns_name = instance['Reservations'][0]['Instances'][0]['PublicDnsName']
        public_host_name = public_dns_name.split('.')[0]
    except BaseException as e:
        logger.error('Could not retrieve public net info: {}'.format(e))

    for tag in tags:
        if 'ZONE' in tag.get('Key',{}).lstrip().upper():
            if is_valid_hostname(tag.get('Value')):
                zone_name = tag.get('Value')
            else:
                logger.error('Could not retrieve valid zone value, recieved: {}'.format(tag.get('Value')))
        if 'CNAME' in tag.get('Key',{}).lstrip().upper():
            if is_valid_hostname(tag.get('Value')):
                cname = tag.get('Value')
            else:
                logger.error('Could not retrieve valid hostname value, recieved: {}'.format(tag.get('Value')))
        if 'ZONEID' in tag.get('Key',{}).lstrip().upper():
            if tag.get('Value') is not None:
                dns_zone_id = tag.get('Value')

    if zone_name is not None and cname is not None:
        if dns_zone_id is None:
            dns_zone_id = get_zone_id(zone_name)
        logger.info('Tag values are zone name: {0}|host name: {1}|zone id: {2}|public IP: {3}'.format(zone_name, cname, dns_zone_id, public_ip))
    
    if zone_id_override is not None:
        dns_zone_id = zone_id_override

    if zone_name_override is not None:
        zone_name = zone_name_override
        
    create_resource_record(dns_zone_id, cname, zone_name, 'A', public_ip)
    return 'Record created for IP {3} with hostname {1} in zone {0} with id {2}'.format(zone_name, cname, dns_zone_id, public_ip)

def json_serial(obj):
    #JSON serializer for objects not serializable by default json code
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")

def is_valid_hostname(hostname):
    #This function checks to see whether the hostname entered into the zone and cname tags is a valid hostname.
    if hostname is None or len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def create_resource_record(zone_id, host_name, hosted_zone_name, type, value):
    if host_name[-1] != '.':
        host_name = host_name + '.'
    route53.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    "Comment": "Updated by Lambda",
                    "Changes": [
                        {
                            "Action": "UPSERT",
                            "ResourceRecordSet": {
                                "Name": host_name + hosted_zone_name,
                                "Type": type,
                                "TTL": 60,
                                "ResourceRecords": [
                                    {
                                        "Value": value
                                    },
                                ]
                            }
                        },
                    ]
                }
            )

def get_zone_id(zone_name):
    #This function returns the zone id for the zone name that's passed into the function.
    if zone_name[-1] != '.':
        zone_name = zone_name + '.'
    hosted_zones = route53.list_hosted_zones()
    x = filter(lambda record: record['Name'] == zone_name, hosted_zones['HostedZones'])
    try:
        zone_id_long = x[0]['Id']
        zone_id = str.split(str(zone_id_long),'/')[2]
        return zone_id
    except:
        return None