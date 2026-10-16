# AWS infrastructure — not deployed

This configuration defines a VPC, two public and two private subnets across two availability zones, EKS, two managed workers (maximum four), encrypted gp3 worker disks, EBS CSI and Pod Identity, Kubernetes secret encryption, API/audit logs, VPC flow logs and a restricted operator /32 API endpoint.

No AWS account credentials are available for this project session. A successful static check is not an AWS plan or deployment. Regional versions, quotas, access and prices must be checked before creating infrastructure.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Set operator_cidr to your current public IPv4 /32.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=stockpilot.tfplan
# Review the concrete plan and obtain authorization before spending.
terraform apply stockpilot.tfplan
aws eks update-kubeconfig --region us-east-1 --name vimal-stockpilot-capstone
kubectl apply -f ../k8s/namespace.yaml
kubectl apply -f ../k8s/storageclass-eks.yaml
# Create application secrets, then install Helm with postgres.storageClass=stockpilot-gp3.
```

The default sets `enable_nat_gateway=false` to avoid a NAT gateway charge: workers use public subnets with public IPs so image pulls work. The private subnets remain defined. Node security groups restrict inbound access; a public address does not grant SSH access. This is a short demo cost mode, not the production recommendation. Opt in with `enable_nat_gateway=true` to place workers in private subnets through one billed NAT gateway. The single NAT is an availability dependency; production would use one per availability zone.

EKS, EC2 workers, NAT, public IPv4, EBS, logs and data transfer can incur charges. There is no automatic spending cap. Use a short session and capture evidence before teardown. Delete Ingress/load balancers, uninstall app and monitoring releases, and deliberately handle retained database PVCs/volumes. Then run `terraform destroy` and check AWS for remaining EBS volumes, load balancers and logs. The StorageClass uses Retain to protect data; those volumes require a separate explicit deletion decision.

The default managed group has two `t3.medium` workers. Capacity for the full application plus Prometheus/Grafana has not been measured. Start with the application only, inspect allocatable memory and actual usage, and add monitoring only after confirming headroom or adjusting instance type/count. Resource requests and replica defaults are configuration, not proof that a workload fits.

EKS node group scaling is not automatically connected to pod HPA. HPA scales API pods within available capacity; install Cluster Autoscaler/Karpenter before expecting nodes to scale automatically. PostgreSQL and Redis are single-instance persistent demo services, not a high-availability database cluster.
