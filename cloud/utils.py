class AWSUtils(CloudUtils):

    def __init__(self):
        profile_name = "dummy"
        self.session = boto3.Session(profile_name=profile_name)

    def get_all_regions(self):
        ec2 = self.session.client("ec2", region_name="us-east-1")
        regions_response = ec2.describe_regions(AllRegions=True)
        return [r["RegionName"] for r in regions_response["Regions"]]

    def enumerate_ec2_details(self, instance_id, region):
        ec2 = self.session.client("ec2", region_name=region)

        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response["Reservations"][0]["Instances"][0]

        print(f"\n[+] Instance ID: {instance['InstanceId']}")
        print(f"[+] State: {instance['State']['Name']}")
        print(f"[+] VPC: {instance['VpcId']}")
        print(f"[+] Subnet: {instance['SubnetId']}")
        print(f"[+] Security Groups: {[sg['GroupName'] for sg in instance['SecurityGroups']]}")

        iam_profile = instance.get("IamInstanceProfile")
        if iam_profile:
            print(f"[+] IAM Role: {iam_profile['Arn']}")

    def list_route53_records(self, domain_name):
        client = boto3.client("route53")

        response = client.list_hosted_zones_by_name(
            DNSName=domain_name,
            MaxItems="1"
        )

        hosted_zones = response["HostedZones"]

        if not hosted_zones:
            print(f"No hosted zone found for domain: {domain_name}")
            return

        hosted_zone_id = hosted_zones[0]["Id"]

        records_response = client.list_resource_record_sets(
            HostedZoneId=hosted_zone_id
        )

        resources = []

        for record in records_response["ResourceRecordSets"]:
            record_name = record["Name"]
            record_type = record["Type"]

            if record_type == "A":
                if "AliasTarget" in record:
                    ip_address = record["AliasTarget"]["DNSName"]
                else:
                    ip_address = record["ResourceRecords"][0]["Value"]

                resources.append(f"A Record: {record_name} -> {ip_address}")

            elif record_type == "CNAME":
                cname = record["ResourceRecords"][0]["Value"]
                resources.append(f"CNAME Record: {record_name} -> {cname}")

        for resource in resources:
            print(resource)

    def map_ip_to_aws_resource(self, ip, regions):

        for region in regions:
            ec2 = self.session.client("ec2", region_name=region)

            # 1. Check Elastic IPs
            try:
                addresses = ec2.describe_addresses(
                    Filters=[{"Name": "public-ip", "Values": [ip]}]
                ).get("Addresses", [])

                if addresses:
                    addr = addresses[0]
                    resource = {"Region": region}

                    if "InstanceId" in addr:
                        resource["Type"] = "EC2 Instance"
                        resource["InstanceId"] = addr["InstanceId"]

                    elif "NetworkInterfaceId" in addr:
                        resource["Type"] = "ENI"
                        resource["NetworkInterfaceId"] = addr["NetworkInterfaceId"]

                    elif "NatGatewayId" in addr:
                        resource["Type"] = "NAT Gateway"
                        resource["NatGatewayId"] = addr["NatGatewayId"]

                    return resource

            except Exception:
                pass

            # 2. Check ENIs
            try:
                enis = ec2.describe_network_interfaces(
                    Filters=[
                        {
                            "Name": "addresses.association.public-ip",
                            "Values": [ip],
                        }
                    ]
                ).get("NetworkInterfaces", [])

                if enis:
                    eni = enis[0]
                    eni_id = eni["NetworkInterfaceId"]

                    response = ec2.describe_network_interfaces(
                        NetworkInterfaceIds=[eni_id]
                    )

                    eni_details = response["NetworkInterfaces"][0]
                    attachment = eni_details.get("Attachment")

                    if attachment:
                        if "InstanceId" in attachment:
                            print(
                                f"ENI {eni_id} is attached to EC2 instance {attachment['InstanceId']}"
                            )

                        elif "InstanceOwnerId" in attachment:
                            print(
                                f"ENI {eni_id} is attached to a Lambda function."
                            )

                        else:
                            print(
                                f"ENI {eni_id} is attached to an unknown resource."
                            )
                    else:
                        print(
                            f"ENI {eni_id} is not attached to any resource."
                        )

                    return {
                        "Type": "ENI",
                        "NetworkInterfaceId": eni_id,
                        "Region": region,
                    }

            except Exception:
                pass

            # 3. Check NAT Gateways
            try:
                ngws = ec2.describe_nat_gateways(
                    Filters=[
                        {
                            "Name": "nat-gateway-addresses.public-ip",
                            "Values": [ip],
                        }
                    ]
                ).get("NatGateways", [])

                if ngws:
                    ngw = ngws[0]

                    return {
                        "Type": "NAT Gateway",
                        "NatGatewayId": ngw["NatGatewayId"],
                        "Region": region,
                    }

            except Exception:
                pass
