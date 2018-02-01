# EC2/Route 53 DNS Updater
## Introduction
I ran into an issue when setting up some machines for my lab with public IP addresses. I keep my AWS machines turned off most of the time to reduce costs since they do not need to be on 24/7. In general, after an EC2 instance has been off for some time the public IP address that it gets when it comes back up will probably be different from the one it started with as was true in my case. This in turn caused my public DNS entries for my machines to be wrong and meant I had to manually change them once they came back up. This got me looking for an automated solution.

This Lambda function is designed to be used with CloudWatch events to automatically update public DNS entries based on tags of EC2 instances when their state is changed to running. While you can get a similar effect by using elastic IPs, they incur charges while not in use and in some cases may cost more than the instance itself!

## Setting Up
##### 1. Create the policy and Lambda role in IAM.
Download the either **lambda-role-policy.json** or **lambda-role-policy-permissive.json**. The difference is that **lambda-role-policy.json** is easy to modify to restrict the access lambda has to only specific zones where as **lambda-role-policy-permissive.json** allows access to all zones in Route 53. After you create the policy you can then create the IAM role that will be used by Lambda and attach the policy to it.

##### 2. Create the Lambda function.
Navigate to the Lambda landing page and select create new function from scratch. When you create the Lambda function be sure to select the Python 2.7 runtime, the code will not work on version 3.6. Once it is created you can copy and paste the code from **lambda-function.py** into the editor and save the function. Since all of the dependencies are built into Lambda already there is no need to upload a deployment bundle.

##### 3. Create the CloudWatch rule.
Once you are on the CloudWatch page go to the Rules section under Events and hit create rule. Near the Event Patter Preview click edit and paste in contents of **event-pattern.json**. Under targets select the Lambda function that was created earlier and leave everything on default. Configuring the event this way will mean that every time a instance goes into the __running__ state the Lambda function will run.

##### 4. Add tags to your instances
The final step is to add tags to your instances. For any instances you want to set a public DNS entry for when they turn on just add tags **cname**, for the hostname and **zone**, for the hosted zone in Route 53. When you input the zone name make sure to add a trailing dot as it appears in Route 53. Now when you turn on a machine with these tags, an entry int Route 53 under the specified zone will be created or updated with the current IP address automatically.