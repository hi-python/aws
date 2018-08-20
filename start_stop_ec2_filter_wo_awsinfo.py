import boto3
import sys
from time import sleep
from operator import itemgetter

# get instance list with filter
def get_aws_instance_filter(ec2, filter_name):
    instances.clear()
    for i in ec2.instances.all():
        tags = dict([(tag['Key'], tag['Value']) for tag in i.tags])
        if (filter_name in tags['Name']):
            instance = {}
            instance['Name'] = tags['Name']
            instance['StopApp'] = tags['StopApp'] if ('StopApp' in tags.keys()) else ''
            instance['StartApp'] = tags['StartApp'] if ('StartApp' in tags.keys()) else ''
            instance['Id'] = i.instance_id
            instance['Status'] = i.state['Name']
            instance['Platform'] = i.platform
            instances.append(instance)
    instances.sort(key=itemgetter('Name'))
    return instances

# print instance list
def print_aws_instance(instances):
    print('No | '+'Name'.ljust(40, ' ') + ' | Status')
    print(''.ljust(60, '-'))
    for index, instance in enumerate(instances):
        print(str(index + 1).ljust(2,' ') + ' | ' + instance['Name'].ljust(40, ' ') + ' | ' + instance['Status'])

# yes/no input
def yes_no_input(question):
    choice = input(question).lower()
    while True:
        if choice in ['y', 'ye', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        choice = input("Please respond with 'yes' or 'no' [y/n]: ").lower()

# start/stop the specified instances
def start_stop_instance(event, ec2):
    region = event['Region']
    instances = event['Instances']
    if event['Action'] == 'start':
        ec2.start_instances(InstanceIds=instances)
        print('starting your instance...')
    elif event['Action'] == 'stop':
        ec2.stop_instances(InstanceIds=instances)
        print('stopping your instance...')

# execute the specified command
def command(ssm, instance_id, commands, platform):
    result = ssm.send_command(
    InstanceIds = [instance_id],
    DocumentName = 'AWS-RunPowerShellScript' if(platform=='windows') else 'AWS-RunShellScript',
    Parameters = {
        "commands": commands
    }
    )
    command_id = result['Command']['CommandId']

    while True:
        sleep(10)
        res = ssm.list_command_invocations(CommandId=command_id)

        invocations = res['CommandInvocations']
        if len(invocations) <= 0: continue

        status = invocations[0]['Status']
        if status == 'Success': return True
        if status == 'Failed': return False

    
# access info
access_key = 'yourAccessKey'
secret_key = 'YourSecretKey'
region = 'ap-northeast-1'

############
# Main
############
session = boto3.session.Session(region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
ec2 = session.resource('ec2')
ec2_cli = session.client('ec2')
ssm = session.client('ssm')

print('connected')
instances = []

# print the list of AWS instances
instances = get_aws_instance_filter(ec2, 'R4S')
print_aws_instance(instances)

# get input num
instance_no = int(input('Enter the number of instance to start or stop : ')) - 1
instance = instances[instance_no]

# get accepted or not and set it to target
if instance['Status'] == 'running':
    print(instance['Name'] + ' is running.')
    accepted = yes_no_input('do you want to stop it? [y/n] : ')
    target = {'Action' : 'stop', 'Status' : 'stopped'} if (accepted) else sys.exit(1)
elif instance['Status'] == 'stopped':
    print(instance['Name'] + ' is stopped.')
    accepted = yes_no_input('do you want to start it? [y/n] : ')
    target = {'Action' : 'start', 'Status' : 'running'} if (accepted) else sys.exit(1)
else :
    print('status is unknwon')
    sys.exit(1)

# Stop application if exists
if(target['Action'] == 'stop' and instance['StopApp'] != ''):
    print('stopping the application...')
    command_result = command(ssm, instance['Id'], [instance['StopApp']], instance['Platform']) 
    print('successfully stopped') if(command_result) else print('failed to stop')
else : pass
    
# start/stop EC2 instance
event = {'Action': target['Action'], "Region": "ap-northeast-1", "Instances":[instance['Id']]}
start_stop_instance(event, ec2_cli)

# check the EC2 status
for i in range(6):
    sleep(10)
    instances = get_aws_instance_filter(ec2, 'R4S')
    instance = instances[instance_no]
    if(instance['Status'] == target['Status']) : 
        print('finished successfully')
        break
    elif(i==5):
        print('timeout')    
    else:
        continue
        
# Start application if exists
if(target['Action'] == 'start' and instance['StartApp'] != ''):
    print('starting the application...')
    sleep(300) # wait to start OS completely
    command_result = command(ssm, instance['Id'], [instance['StartApp']], instance['Platform']) 
    print('successfully started') if(command_result) else print('failed to start')
else : pass
        

# print the list of AWS instances again
print_aws_instance(instances)
